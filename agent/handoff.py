import re
from pathlib import Path


def participants(path):
    raw = Path(path).read_text(encoding='utf-8')

    def name(role):
        found = re.findall(r'^\[\d{2}:\d{2}\] ' + role + r' \(([^\n]+?)\):', raw, re.M)
        headers = re.findall(r'^' + role + r':\s*([^\n]+)', raw, re.M)
        for value in found + headers:
            value = value.split(',', 1)[0].strip()
            if value and value.strip('()').lower() != 'automated':
                return value
        return None

    return {'customer': name('Customer') or 'Customer', 'human_agent': name('Agent')}


def _short(value, size):
    value = ' '.join(str(value).split())
    return value if len(value) <= size else value[:size - 3].rstrip() + '...'


CHARGE_NOUNS = ('taxes', 'regulatory surcharges', 'surcharges', 'late fee', 'late fees', 'device charge',
                'activation fee', 'one-time charges', 'add-ons', 'fees')


def _money(value):
    return '${:.2f}'.format(value)


def _question(text):
    parts = [p for p in re.split(r'(?<=[.!?])\s+', text or '') if '?' in p]
    cleaned = []
    for part in parts:
        for dash in (' — ', ' -- ', ' - '):
            if dash in part:
                part = part.split(dash)[-1]
        cleaned.append(part.strip())
    return ' '.join(cleaned) or ' '.join((text or '').split())


def _nouns(text):
    low = (text or '').lower()
    found = [n for n in CHARGE_NOUNS if re.search(r'\b' + re.escape(n) + r'\b', low)]
    found = [n for n in found if not any(n != other and n in other for other in found)]
    found.sort(key=low.find)
    if not found:
        return ''
    return found[0] if len(found) == 1 else ', '.join(found[:-1]) + ' and ' + found[-1]


def _first_sentence(text):
    return re.split(r'(?<=[.!?])\s+', ' '.join((text or '').split()))[0].rstrip('.')


def _customer_part(turn, first):
    kinds = str(turn.get('intent') or '').split('+')
    issue = turn.get('issue')
    values = turn.get('computed') or {}
    out = []
    for kind in kinds:
        if kind == 'identity':
            out.append('reported a service outage and disputed the charge' if issue == 'outage'
                       else 'opened a billing dispute')
        elif kind in ('credit', 'question'):
            if turn.get('decision') == 'clarify':
                out.append('gave account details')
            elif issue == 'outage':
                charge = values.get('monthly_recurring_charge')
                out.append('gave the outage details' + (' and the disputed {} charge'.format(_money(charge)) if charge is not None else ''))
            elif 'requested_credit' in values:
                out.append('reported a billing error of {}'.format(_money(values['requested_credit'])))
            else:
                out.append('gave details of the disputed charge')
        elif kind == 'limit':
            out.append('asked whether the $75 limit applies')
        elif kind == 'deadline':
            out.append('asked about the deadline to request the credit')
        elif kind in ('scope', 'tax') and issue == 'outage':
            out.append('asked whether {} are also reduced'.format(_nouns(turn.get('customer')) or 'other charges'))
        elif kind in ('tax', 'bill'):
            out.append('asked how the bill is made up')
        elif kind == 'proration':
            out.append('asked about plan-change proration')
        elif kind == 'outside':
            out.append('asked for a lookup outside Nimbus documents')
        elif kind == 'retention':
            out.append('asked for a retention credit')
        elif kind == 'device':
            out.append('asked for a device replacement credit')
        elif kind == 'human':
            out.append('asked to speak with a person')
        elif kind == 'acknowledge':
            out.append('acknowledged')
        elif kind == 'gap':
            out.append('asked something the documents do not cover')
        else:
            out.append('said: "' + _first_sentence(turn.get('customer')) + '"')
    return ' and '.join(dict.fromkeys(out))


def _agent_part(turn, verified_before):
    kinds = str(turn.get('intent') or '').split('+')
    decision = turn.get('decision')
    values = turn.get('computed') or {}
    rules = turn.get('governing_policy') or []
    to = turn.get('escalate_to') or 'a human'
    if decision == 'clarify':
        if 'identity' in kinds:
            return 'asked for identity details'
        what = 'the outage dates' if turn.get('issue') == 'outage' else 'the missing details'
        return ('asked for ' if verified_before else 'verified identity and asked for ') + what
    if decision == 'decline':
        return 'prepared a handoff note for ' + to
    if decision == 'escalate':
        if turn.get('escalation_basis') in ('customer_request', 'stalled_clarification'):
            return 'prepared a handoff note for ' + to
        if turn.get('escalation_basis') == 'evidence_gap':
            if any('recurring plan charge only' in e for e in turn.get('evidence') or []):
                return 'confirmed the credit covers the plan charge only and prepared a handoff note for ' + to
            if 'outside' in kinds:
                return 'said it answers only from Nimbus policy and help articles and prepared a handoff note for ' + to
            return 'said the documents do not cover it and prepared a handoff note for ' + to
        amount = values.get('credit', values.get('requested_credit'))
        return ('calculated {} but offered no credit; '.format(_money(amount)) if amount is not None and 'credit' in values
                else 'offered no credit; ') + 'prepared a handoff note for ' + to
    out = []
    for kind in kinds:
        if kind == 'limit' and 'Rule 3' in rules:
            out.append('said no, the $75.00 limit does not cap an outage credit')
        elif kind == 'limit':
            out.append('confirmed the $75.00 limit for general billing-error credits')
        elif kind == 'deadline' and values.get('request_deadline'):
            days = values.get('days_since_resolution')
            out.append('gave the deadline ' + str(values['request_deadline'])
                       + ('' if days is None else ' and said the request is ' + ('in time' if 0 <= days <= 30 else 'late')))
        elif kind == 'credit' and 'credit' in values and 'Rule 3' in rules:
            out.append('found ticket {} and quoted a credit of {} for {} full days'.format(
                values.get('ticket_id'), _money(values['credit']), values.get('full_days')))
        elif kind == 'credit' and 'rolling_total' in values:
            out.append('said the {} credit is within the $75.00 limit (12-month total {})'.format(
                _money(values.get('requested_credit', 0)), _money(values['rolling_total'])))
        elif kind == 'acknowledge':
            out.append('closed politely')
        elif kind in ('bill', 'tax', 'proration'):
            out.append('explained it from the help article')
        else:
            out.append('replied: "' + _first_sentence(turn.get('reply')) + '"')
    return ' and '.join(dict.fromkeys(out))


def build_notes(result, headers, state, participants):
    turns = result.get('turns') or []
    name = participants['customer']
    short_name = name.split()[0]
    account = headers.get('Account Number') or state.account_id or 'unknown account'
    plan = headers.get('Plan') or 'plan not recorded'
    customer = '{}; account {}; {}'.format(name, account, plan)
    if '$' not in plan and state.monthly is not None:
        customer += '; {}/month'.format(_money(state.monthly))

    if not state.verified:
        customer = name + '; identity not verified; account details withheld'

    history = []
    verified_before = False
    for index, turn in enumerate(turns):
        summary = (_customer_part(turn, index == 0) if state.verified else
                   'asked for assistance; account details withheld')
        history.append('{}  {} {}. Agent {}.'.format(
            turn.get('time') or '--:--', name if index == 0 else short_name,
            summary, _agent_part(turn, verified_before)))
        if 'identity' not in str(turn.get('intent')):
            verified_before = True

    policy_stops = [t for t in turns if t.get('escalation_basis') == 'policy']
    settled = ['- Identity {} (account {}).'.format('verified' if state.verified else 'NOT verified', account)]
    if not state.verified:
        settled = ['- Identity NOT verified; account details withheld.']
    credits = [t for t in turns if 'credit' in (t.get('computed') or {})]
    if state.ticket:
        line = '- Outage confirmed by NOC ticket {}'.format(state.ticket.get('id'))
        if credits and credits[-1]['computed'].get('full_days') is not None:
            line += ': {} full days'.format(credits[-1]['computed']['full_days'])
        settled.append(line + '.')
    if credits:
        amount = credits[-1]['computed']['credit']
        settled.append('- Outage credit of {} under Rule 3; '.format(_money(amount))
                       + ('Tier 2 must approve it before it is applied.' if policy_stops
                          else 'a front-line agent may apply it (under $300.00 and 30 days).'))
    general = [t for t in turns if 'rolling_total' in (t.get('computed') or {}) and 'Rule 2' in (t.get('governing_policy') or [])]
    if general and not credits:
        values = general[-1]['computed']
        settled.append('- General credit of {} asked for; the 12-month total would be {} against the $75.00 limit.'.format(
            _money(values.get('requested_credit', 0)), _money(values['rolling_total'])))
    deadlines = [t['computed'] for t in turns if (t.get('computed') or {}).get('request_deadline') and 'days_since_resolution' in t['computed']]
    if deadlines and state.ticket:
        days = deadlines[-1]['days_since_resolution']
        settled.append('- Request deadline {}; this request is {}.'.format(
            deadlines[-1]['request_deadline'], 'in time' if days is not None and 0 <= days <= 30 else 'outside the window'))

    notes, seen = {}, {}
    for turn in turns:
        decision, destination = turn.get('decision'), turn.get('escalate_to')
        if decision not in ('escalate', 'decline') or not destination:
            continue
        if destination not in notes:
            notes[destination] = {'for': destination, 'status': 'prepared, not sent (prototype)', 'customer': customer, 'decision_needed': [], 'why_a_human': [],
                                  'what_happened': list(history), 'already_settled': list(settled), 'not_promised': []}
            seen[destination] = set()
        reason = turn.get('reason') or ''
        if reason in seen[destination]:
            continue
        seen[destination].add(reason)
        note = notes[destination]
        time = '[' + str(turn.get('time') or '--:--') + '] '
        values = turn.get('computed') or {}
        if decision == 'decline':
            note['decision_needed'].append(time + name + ' asked: "' + _question(turn.get('customer')) + '"')
            note['decision_needed'].append('Decide: whether and how the ' + destination + ' handles this request.')
            why = 'Out of scope for Billing: this request is handled by the ' + destination + '.'
            lines = ['- No credit was applied or promised by Billing for this request.']
        elif turn.get('escalation_basis') in ('customer_request', 'stalled_clarification'):
            cause = ('the customer asked for a human.'
                     if turn['escalation_basis'] == 'customer_request' else
                     'two clarifying questions brought no progress.')
            note['decision_needed'].append('Take over the conversation: ' + cause)
            why = turn['escalation_basis'].replace('_', ' ') + ': ' + cause
            lines = ['- No account decision or credit was promised.']
        elif turn.get('escalation_basis') == 'evidence_gap':
            scope = any(k in str(turn.get('intent')) for k in ('scope', 'tax')) and turn.get('issue') == 'outage'
            nouns = _nouns(turn.get('customer')) or 'the other charges asked about'
            note['decision_needed'].append(time + name + ' asked: "' + _question(turn.get('customer')) + '"')
            note['decision_needed'].append('Decide: ' + ('whether those charges are adjusted or refunded as well.' if scope
                                           else 'how to answer this question.') + ' The policy and knowledge base do not say.')
            pairs = list(zip(turn.get('evidence') or [], turn.get('evidence_sources') or []))
            known = next((src for text, src in pairs if 'recurring plan charge only' in text), None)
            if known:
                note['decision_needed'].append('Known: the outage credit applies to the recurring plan charge only (' + known + ').')
            elif 'credit' in values:
                note['decision_needed'].append('Known: the credit of {} is calculated from the monthly recurring charge (Rule 3).'.format(_money(values['credit'])))
            why = 'Evidence gap: the documents do not answer this question.'
            lines = ['- Nothing was said about whether {} are adjusted.'.format(nouns) if scope
                     else '- No answer was given to the question asked at {}.'.format(turn.get('time'))]
        else:
            amount = values.get('credit', values.get('requested_credit'))
            note['decision_needed'].append(time + ('Approve or refuse the credit of {}?'.format(_money(amount)) if amount is not None
                                                   else 'Approve or refuse a credit for this request?'))
            rule, _, rest = reason.partition(': ')
            why = 'Policy threshold ({}): {}; a front-line agent may not decide this.'.format(rule, rest.rstrip('.')) if rest else 'Policy threshold: ' + reason
            lines = ['- No credit was applied or promised; the ' + destination + ' decides.']
        if why not in note['why_a_human']:
            note['why_a_human'].append(why)
        for line in lines:
            if line not in note['not_promised']:
                note['not_promised'].append(line)
    for note in notes.values():
        note['not_promised'].append('- The automated agent applies nothing; it states what the policy allows.')
    return list(notes.values())
