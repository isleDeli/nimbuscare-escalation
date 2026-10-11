import re
from datetime import datetime, timedelta
from .loaders import sentences
from .policy import evaluate, qualifies
from .state import dates


DEADLINE = (r'\b(?:deadline|cutoff|cut-off|too late|by when|until when|how long|window|time limit|last day|last date|latest day|latest date)\b'
            r'|\b(?:when|until|till)\b[^.?!]{0,40}\b(?:file|filing|claim|submit|apply|put in)\b|\bsubmit[^.?!]*\brequest\b')
LIMIT = r'\$75\b|\b(?:limit|cap|maximum|max|ceiling|the most|upper limit|how much can you|up to how much|without (?:a |any )?(?:supervisor|manager|approval)|seventy[ -]five|never[^.?!]*more than)\b'


def identity_only(text):
    remainder = re.sub(r'\bNMB-[\w-]+\b', '', text, flags=re.I)
    remainder = re.sub(r'(?:card(?:\s+\w+){0,3}|last\s*4(?:\s+digits)?|ending(?:\s+is)?|pin(?:\s+is)?)\D{0,15}\d{4}\b', '', remainder, flags=re.I)
    remainder = re.sub(r'\b(?:hi|hello|hey|good|morning|afternoon|evening|acct|account|number|my|is)\b', '', remainder, flags=re.I)
    return len(re.findall(r"[a-z]+(?:'[a-z]+)?", remainder, re.I)) < 4


def intent(text, state):
    t = text.lower().replace('’', "'")
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", t)
    human = re.search(
        r'\b(?:speak|talk|transfer|connect|escalate)\b[^.?!]{0,60}'
        r'\b(?:human|person|agent|supervisor|manager|representative|rep|specialist)\b'
        r'|\bescalate this\b|\bget me someone\b'
        r'|\b(?:want|need|get me)\s+(?:to speak with\s+)?'
        r'(?:a\s+)?(?:real\s+|live\s+)?(?:human|person|agent|representative)\b', t)
    if human:
        return 'human'
    if not state.verified:
        return 'identity'
    closers = set("thanks thank you thx ok okay great perfect good got it sounds "
                  "cheers bye goodbye that's that is all everything no nothing "
                  "else i'm done appreciate fine cool alright understood yes "
                  "sure much very so for your help the".split())
    if words and '?' not in t and not re.search(r'\d', t) and set(words) <= closers:
        return 'acknowledge'
    if re.search(r'\b(?:google|search.*\b(?:web|online|internet)|look up online|competitor|regulator|fcc|what.*\blaw|legally owed)\b', t):
        return 'outside'
    if state.other_team:
        return state.other_team
    if not state.verified:
        return 'identity'
    for label, pattern in [
        ('tax', r'\b(?:tax|taxes|taxed|surcharges?)\b'),
        ('deadline', DEADLINE),
        ('limit', LIMIT),
        ('proration', r'\b(?:plan\b.*\bchang\w*|chang\w*.*\bplan|upgrad\w*|downgrad\w*|switch\w*.*\bplan)\b'),
        ('bill', r'\b(?:explain\w*.*\bbill|understand\w*.*\bbill|what.*\bbill\b.*\binclude\w*|how.*\bbill\b.*\bwork\w*)\b'),
        ('gap', r'\b(?:waiv\w*|late fee|price match|match\w*.*\bprice)\b'),
    ]:
        if re.search(pattern, t if label != 'limit' else t.replace('time limit', ' ')):
            return label
    if getattr(state, 'credit_answered', False) and state.issue in ('outage', 'billing_error'):
        new_details = bool(re.search(r'\$\d', t)) or bool(dates(text, state.date.year if state.date else None))
        amount_again = re.search(r"\bhow much\b|\bwhat(?:'s| is| was)\b[^.?!]{0,30}\b(?:credit|amount|refund)\b|\b(?:again|repeat|remind)\b", t)
        asks = '?' in t or re.search(r'\b(?:can|could|will|would|please|want|need|add|give|pay|compensat\w*|reimburs\w*)\b', t)
        if not new_details and not amount_again and asks:
            return 'gap'
    if state.issue in ('outage', 'billing_error') or state.dispute:
        if re.search(r'credit|refund|disput|charg|money back|owed|how much|amount|outage|compensation|invoice|line item|\$\d', t) or dates(text, state.date.year if state.date else None):
            return 'credit'
        if re.search(r'\b(?:pin|card|last\s*4|ending)\b', t) and ((state.outage and not state.start) or not state.line or state.amount is None):
            return 'credit'
    facts_missing = (state.outage and not state.start) or not state.line or state.amount is None
    if state.issue in ('outage', 'billing_error') and not facts_missing and '?' in t:
        return 'gap'
    if re.search(r'\b(?:still broken|happened again|down again)\b', t):
        return 'unresolved'
    if state.problem:
        return 'unresolved'
    if identity_only(text):
        return 'question'

    return 'credit'



def _respond(turn, number, state, rules, articles, retriever, label):
    text = turn['customer']
    topic = ''
    if not state.verified:
        topic += ' confirm account holder identity billing dispute payment method PIN'
    elif state.outage and state.other_team == 'device':
        topic += ' device protection claim damaged device'
    elif state.outage:
        topic += ' service outage credit NOC ticket outage recurring plan charge full days resolution'
        if not state.ticket:
            topic += ' ticket verified'
    elif state.issue == 'billing_error':
        topic += ' billing error goodwill credit limit refund eligibility'
    elif state.dispute:
        topic += ' billing dispute line item'
    else:
        topic += ' account identity billing question'
    if state.verified and (state.issue in ('outage', 'billing_error') or state.dispute) and ((state.outage and not state.start) or not state.line or state.amount is None):
        topic += ' identify specific disputed line item date amount description confirm account identity billing dispute'
    if state.statement:
        topic += ' dispute invoice statement date line item'
    if state.review_days is not None:
        topic += ' second dispute prior resolved dispute'
    if state.fraud_reported:
        topic += ' fraud not registered'
    if state.account.get('fraud_flags'):
        topic += ' fraud'
    retrieved = retriever.search(text + topic)
    r = dict(turn=number, time=turn['time'], customer=text, intent=label, issue=state.issue,
             decision='answer', governing_policy=[], rejected_policy=[], retrieved=retrieved,
             driving_article=None, evidence=[], evidence_sources=[], computed={}, computed_working=[],
             escalate_to=None, escalation_basis=None, escalation_check='', guards=[], reason='', reply='')
    if 'original_agent_reply' in turn:
        r['original_agent_reply'] = turn['original_agent_reply']
    patterns = []
    categories = []
    rule_patterns = {}
    def support(cats, pats, rule_pats=None):
        nonlocal categories, patterns, rule_patterns
        categories, patterns, rule_patterns = cats, pats, rule_pats or {}
    def handoff(message, basis='policy', confirmed=''):
        r.update(decision='escalate', escalation_basis=basis, escalate_to='Tier 2 Billing Specialist', reason=message)
        prefix = f'Confirmed: {confirmed} ' if confirmed else ''
        r['reply'] = prefix + ('Needs approval: ' if basis == 'policy' else 'Not covered: ') + message + '. Next: a Tier 2 Billing Specialist needs to review this and decide; nothing is applied until then. A handoff note has been prepared for them.'
    if label == 'human':
        return takeover(r, state, 'customer_request')
    if label == 'fraud':
        support(['Escalation Rules'], [r'fraud'],
                {'Rule 4': [r'Suspected fraud'], 'Rule 5': [r'Regardless']})
        r.update(governing_policy=['Rule 4', 'Rule 5'])
        report = 'the report is recorded as an allegation for investigation'
        if state.amount is not None:
            report += f'; disputed amount ${state.amount:.2f}'
        if state.statement:
            report += f'; invoice date {state.statement}'
        handoff('possible fraud means a Tier 2 Billing Specialist must make '
                'the credit decision', confirmed=report + '.')
        r['reason'] = ('Rule 4d / Rule 5: customer reports possible fraud; '
                       'Tier 2 must make the credit decision')
        r['escalation_check'] = r['reason']
        r['guards'].append(
            'front-line credit on a suspected-fraud dispute: made no '
            'eligibility statement on a charge the customer reports as '
            'unauthorized; Rule 4d / Rule 5 send the decision to Tier 2')
    elif label == 'acknowledge':
        r.update(reply="You're welcome. Is there anything else on this bill I can check against our billing policy?", reason='Acknowledgement only; no policy question asked.')
        return r
    elif label == 'outside':
        handoff('These documents do not address this question', 'evidence_gap', 'I can only answer from Nimbus billing policy and help articles and cannot search the web or use outside sources.')
        r['guards'].append('outside source: blocked outside lookup; only the two billing documents are available')
    elif label in ('retention', 'device'):
        support(['not a billing-dispute credit'], [r'Customer Retention queue' if label == 'retention' else r'handled by the Device Protection team'])
        r['decision'] = 'decline'
        r['reason'] = 'A separate team handles this request.'
    elif label == 'identity':
        support(['Billing Dispute Process'], [r'Confirm the account holder'])
        r.update(decision='clarify', governing_policy=['Rule 1'], reason=('The identity details given did not match the account record.' if state.mismatch else 'Identity is not yet verified against the account record.'), reply=('The details could not be verified. ' if state.mismatch else '') + 'Please confirm your account number and card last 4 digits or account PIN.')
    elif label in ('tax', 'scope') and state.outage:
        support(['Service-Outage Credit Policy'], [r'This credit applies to the recurring plan charge only'])
        governing, rejected, computed, escalation = evaluate(state)
        r.update(governing_policy=governing, rejected_policy=rejected, computed=computed)
        rule_patterns = {'Rule 3': [r'Service-Outage Credit =|not capped|30 calendar days'],
                         'Rule 2': [r'up to \$75.00'], 'Rule 5': [r'Regardless']}
        c = computed.get('credit')
        r['escalation_check'] = escalation or ('Rule 4b: no approval threshold exceeded; ticket verified'
                                                  if 'Rule 3' in governing else 'Rule 3 does not qualify; Rule 2 applies')
        if c is not None:
            r['computed_working'] = [f'credit ${c:.2f} = ${computed["monthly_recurring_charge"]:.2f} / 30 x {computed["full_days"]} full days', f'ticket {computed["ticket_id"]}']
        handoff('The documents do not say whether these other charges are adjusted or refunded', 'evidence_gap')
        r['guards'].append('credit scope: did not infer adjustment of other charges from plan-only eligibility')
    elif label in ('bill', 'proration', 'tax'):
        support(['Account & Billing Basics'], [r'Taxes and surcharges are calculated' if label == 'tax' else r'system prorates' if label == 'proration' else r'Your monthly invoice includes'])
        r['reason'] = 'The billing basics article directly supports this explanation.'
    elif label == 'gap' and state.issue in ('outage', 'billing_error') and ((state.outage and not state.start) or not state.line or state.amount is None) and not re.search(r'waiv|payment|price match|late fee', text, re.I):
        support(['Billing Dispute Process'], [r'Identify the exact'])
        r.update(decision='clarify', reply='Please confirm which charge on which bill, what is wrong with it, and the dates involved.', reason='Required facts are missing for the billing request.')
    elif label == 'gap' and getattr(state, 'credit_answered', False) and qualifies(state) and 'credit' in evaluate(state)[2]:
        governing, rejected, computed, escalation = evaluate(state)
        r.update(governing_policy=[g for g in governing if g == 'Rule 3'], rejected_policy=rejected, computed=computed)
        rule_patterns = {'Rule 3': [r'Service-Outage Credit =']}
        c, days = computed['credit'], computed['full_days']
        r['computed_working'] = [f'credit ${c:.2f} = ${computed["monthly_recurring_charge"]:.2f} / 30 x {days} full days', f'ticket {computed["ticket_id"]}']
        handoff('The policy and help articles provide for the outage credit only and do not address this additional request', 'evidence_gap',
                f'your outage credit is ${c:.2f} (${computed["monthly_recurring_charge"]:.2f} / 30 x {days} full days).')
        r['guards'].append('request beyond the outage credit: did not grant, refuse or restate the credit as an answer to an additional request the documents do not cover')
    elif label == 'gap':
        handoff('These documents do not address this question', 'evidence_gap')
    elif label == 'unresolved':
        r.update(decision='clarify', reason='The new problem needs details.',
                 reply='Please explain what happened and which charge on '
                       'which bill is affected, including its date and amount.')
    elif label == 'question':
        support(['Billing Dispute Process'], [r'Confirm the account holder'])
        r.update(decision='clarify', reason='Identity is verified; the question is missing.', reply='Your identity is verified. What is your billing question?')
    elif label == 'limit' and state.issue not in ('outage', 'billing_error'):
        support(['Refund Eligibility'], [r'Confirmed billing errors|general.*billing errors|Charges related to'])
        r['reply'] = 'The $75.00 limit is for general billing-error credits; outage-related charges are handled separately. Please identify which charge on which bill, what is wrong with it, and the dates involved.'
        r['reason'] = 'No credit track has been established; no requested amount assumed.'
    elif label == 'deadline':
        if state.outage:
            support(['Service-Outage Credit Policy'], [r'request must be made within|requesting within'], {'Rule 3': [r'30 calendar days']})
            r['governing_policy'] = ['Rule 3']
            r['rejected_policy'] = [{'id': 'Rule 1', 'why': 'The 60-day statement window is not the outage request deadline.'}]
            if state.ticket and state.date:
                end = datetime.fromisoformat(state.ticket['end']).date()
                deadline = end + timedelta(days=30)
                governing, rejected, computed, escalation = evaluate(state)
                r.update(governing_policy=governing, rejected_policy=r['rejected_policy'] + rejected, computed=computed)
                r['computed'].update(request_deadline=deadline.isoformat(), days_since_resolution=(state.date-end).days)
                if escalation:
                    r.update(decision='escalate', escalate_to='Tier 2 Billing Specialist', escalation_basis='policy', escalation_check=escalation)
                r['computed_working'] = [f'deadline {deadline} = {end} + 30 days']
                r['reply'] = f'The request window is 30 calendar days from outage resolution on {end}, with deadline {deadline}. Your request on {state.date} is ' + ('in time.' if 0 <= (state.date-end).days <= 30 else 'outside that window.')
                r['guards'].append(f'60-day window used as the deadline: blocked the statement window; used 30 days from {end} to {deadline}')
                failed = [x for x in evaluate(state)[1] if x['id'] == 'Rule 3']
                if failed:
                    r['reply'] += ' Note: this outage does not qualify for the outage credit. ' + failed[0]['why']
            elif state.start:
                r['governing_policy'].append('Rule 4')
                rule_patterns['Rule 4'] = [r'ticket number cannot be verified']
                handoff('no outage ticket could be verified for the account '
                        'and dates, so no resolution date or deadline can be '
                        'confirmed', confirmed='the request window for an '
                        'outage credit is 30 calendar days from the outage '
                        'resolution date.')
                r['reason'] = ('Rule 4b: no outage ticket could be verified '
                               'for the account and dates')
                r['escalation_check'] = r['reason']
                r['guards'].append('60-day window used as the deadline: did not quote the 60-day statement window; the outage-credit window is 30 days from resolution, and no resolution date is verified')
            else:
                r.update(decision='clarify', reply='Please confirm when the outage started and ended' + (' and which charge on which invoice is disputed (date, amount, and description)' if not state.line or state.amount is None else '') + ' so I can look up its resolution and the 30-calendar-day deadline.')
            r['reason'] = r['reason'] or 'Rule 3 uses 30 calendar days from resolution.'
        else:
            support(['Billing Dispute Process'], [r'within 60 days'], {'Rule 1': [r'60 calendar days']})
            r['governing_policy'] = ['Rule 1']
            r['reply'] = 'You can dispute a specific invoice charge within 60 calendar days of the statement date.'
            if state.statement and state.date:
                deadline = state.statement + timedelta(days=60)
                age = (state.date-state.statement).days
                r['computed'] = {'request_deadline': str(deadline), 'days_since_statement': age}
                r['computed_working'] = [f'deadline {deadline} = {state.statement} + 60 days']
                r['reply'] += f' The deadline is {deadline}; your request is ' + ('in time.' if age <= 60 else 'outside that window.')
                if age > 60:
                    handoff(f'The invoice is {age} days old against the 60-day window')
                    r['reason'] = f'Rule 1: invoice {age} days old exceeds 60 days.'
                    r['escalation_check'] = r['reason']
                    rule_patterns['Rule 1'].append(r'sign-off')
            r['reason'] = r['reason'] or 'Rule 1 uses the statement date.'
    elif state.statement and state.date and (state.date-state.statement).days > 60 and not qualifies(state):
        support(['Billing Dispute Process'], [r'within 60 days'], {'Rule 1': [r'60 calendar days|sign-off']})
        governing, rejected, computed, escalation = evaluate(state)
        r.update(governing_policy=governing, rejected_policy=rejected, computed=computed)
        handoff(f'The invoice is {computed["days_since_statement"]} days old against the 60-day window', confirmed=f'The statement date is {state.statement}.')
    elif (state.outage and not state.start) or not state.line or state.amount is None or state.issue == 'none':
        support(['Billing Dispute Process'], [r'Identify the exact|Confirm the account holder'])
        missing = []
        if state.outage and not state.start:
            missing.append('when the outage started and ended')
        if not state.line or state.amount is None or state.issue == 'none':
            missing.append('which charge on which bill is disputed (date, amount, and description), what is wrong with it, and the dates involved')
        r.update(decision='clarify', governing_policy=['Rule 1'], reason='Required dispute details are missing.', reply='Your identity is verified. Please confirm ' + ' and '.join(missing) + '.')
    else:
        governing, rejected, computed, escalation = evaluate(state)
        if state.issue == 'none' and governing != ['Rule 1']:
            governing, rejected, computed, escalation = [], [], {}, None
        r.update(governing_policy=governing, rejected_policy=rejected, computed=computed)
        if not governing:
            handoff('These documents do not address this question', 'evidence_gap')
        elif 'Rule 1' in governing:
            support(['Billing Dispute Process'], [r'within 60 days'], {'Rule 1': [r'sign-off']})
            age = computed['days_since_statement']
            handoff(f'The invoice is {age} days old against the 60-day window', confirmed=f'The statement date is {state.statement}.')
            r['reason'] = escalation
            r['escalation_check'] = escalation
            r['computed_working'] = [f'invoice age {age} days = {state.date} - {state.statement}']
        elif 'Rule 3' in governing:
            support(['Service-Outage Credit Policy', 'Escalation Rules'], [r'eligible for a prorated|Calculate the credit|above \$75.00 does not|not limited by'], {'Rule 3': [r'Service-Outage Credit =|not capped|30 calendar days|exceeds 4'], 'Rule 4': [r'Service-Outage Credit.*exceeds|ticket number cannot be verified']})
            c = computed.get('credit')
            if c is None:
                handoff('The documents and account record do not supply the recurring charge', 'evidence_gap')
            else:
                days = computed['full_days']
                confirmed = f'The calculated outage credit is ${c:.2f} for {days} full days without service.'
                credit_sentence = f'Your outage credit is ${c:.2f} (${computed["monthly_recurring_charge"]:.2f} / 30 x {days} full days).'
                if label == 'limit':
                    r['reply'] = 'No. The $75.00 limit is for general billing-error credits and does not cap an outage credit. ' + credit_sentence
                else:
                    r['reply'] = (f'Outage ticket {computed["ticket_id"]} confirms {computed["outage_hours"]:g} hours without service, which is {days} full days. '
                                  + credit_sentence + ' That is within the $300.00 and 30-day limits a front-line agent can apply, so no specialist approval is needed.')
                r['reason'] = 'Rule 3 qualifies; Rule 4b thresholds do not require escalation.'
                r['computed_working'] = [f'credit ${c:.2f} = ${state.monthly:.2f} / 30 x {days} full days', f'ticket {state.ticket["id"]}', f'full days {days} = floor({computed["outage_hours"]:g} hours / 24)']
                r['escalation_check'] = f'Rule 4b: credit ${c:.2f} {">" if c > 300 else "<="} $300.00, outage {computed["outage_hours"] / 24:g} days {">" if computed["outage_hours"] > 720 else "<="} 30, ticket verified: ' + ('escalation' if escalation else 'no escalation')
                if c > 75 or label == 'limit':
                    r['guards'].append(f'$75.00 cap on an outage credit: did not apply the Rule 2 ceiling or Rule 4a escalation to the Rule 3 credit of ${c:.2f}')
                if escalation:
                    handoff(escalation.split(': ', 1)[-1], confirmed=confirmed)
                    r['reason'] = escalation
        else:
            support(['Refund Eligibility', 'Escalation Rules'] + (['Service-Outage Credit Policy'] if state.outage else []), [r'Confirmed billing errors|cumulative ceiling|no ticket exists|NOC ticket can.t be verified|request must be made within|more than 4 consecutive hours|general goodwill credit'], {'Rule 2': [r'up to \$75.00|cumulative|above \$75.00'], 'Rule 3': [r'If any condition'], 'Rule 4': [r'general.*goodwill credit|Service-Outage Credit.*exceeds|ticket number cannot be verified']})
            if not state.ticket and state.outage:
                handoff('No outage ticket could be verified for the account and dates')
                r['reason'] = escalation
                r['escalation_check'] = escalation
            else:
                used, remaining = computed['goodwill_credits_last_12_months'], computed['remaining_allowance']
                if state.outage:
                    why = rejected[0]['why']
                    confirmed = f'{why} The general goodwill ceiling is $75.00; ${used:.2f} is already used and ${remaining:.2f} remains. No outage-credit amount is promised.'
                    r['reply'] = confirmed
                else:
                    amount, total = computed['requested_credit'], computed['rolling_total']
                    confirmed = f'The general billing-error credit you are asking for is ${amount:.2f}; credits already used are ${used:.2f}, giving a new rolling 12-month total of ${total:.2f}.'
                    r['reply'] = confirmed + ' That is within the $75.00 a front-line agent may credit without further approval, once the error is confirmed on the invoice.'
                if label == 'limit':
                    fits = state.amount is not None and state.amount <= remaining
                    confirmed = (f'General billing-error credits have a $75.00 limit per account per rolling 12 months; ${used:.2f} is already used and ${remaining:.2f} remains. '
                                 + (f'The requested ${state.amount:.2f} ' + ('fits within the remaining allowance.' if fits else 'exceeds the remaining allowance and requires Tier 2 approval.') if state.amount is not None else 'The documents do not specify an amount for this outage under Rule 2.'))
                    r['reply'] = confirmed
                total = computed.get('rolling_total', used)
                r['escalation_check'] = f'Rule 4a: rolling total ${total:.2f} {">" if total > 75 else "<="} $75.00: ' + ('escalation' if escalation else 'no escalation')
                r['computed_working'] = [f'rolling total ${total:.2f} = ${used:.2f} + ${(state.amount or 0):.2f}', f'remaining allowance ${remaining:.2f} = max(0, $75.00 - ${used:.2f})']
                r['reason'] = 'Rule 2 governs the cumulative general goodwill allowance.'
                if escalation:
                    handoff(escalation.split(': ', 1)[-1], confirmed=confirmed)
                    r['reason'] = escalation
                    if label == 'limit':
                        r['reply'] = 'Confirmed: ' + confirmed + ' Needs approval: ' + escalation.split(': ', 1)[-1] + '. Next: a Tier 2 Billing Specialist needs to review this and decide; nothing is applied until then. A handoff note has been prepared for them.'
        if 'Rule 5' in governing:
            support(['Refund Eligibility', 'Escalation Rules'] if label == 'limit' and 'Rule 2' in governing else ['Escalation Rules'], [r'Confirmed billing errors|cumulative ceiling|second billing dispute|second dispute|fraud indicators|possible fraud'], {'Rule 5': [r'Regardless|Front-line'], 'Rule 4': [r'second billing dispute|Suspected fraud']})
            cap_answer = r['reply'] if label == 'limit' and 'Rule 2' in governing and 'Next:' not in r['reply'] else ''
            handoff(escalation.split(': ', 1)[-1], confirmed=f'The disputed amount is ${state.amount:.2f}.')
            if cap_answer:
                r['reply'] = cap_answer + ' ' + r['reply']
            r['reason'] = escalation
            r['escalation_check'] = escalation
            r['computed_working'].append(f'prior resolved dispute age {state.review_days} days; threshold 90 days' if state.review_days is not None else 'account fraud indicators present')
        if state.outage and rejected and state.ticket and 'credit' in computed:
            r['guards'].append(f'blending two rules: calculated under {governing[0]} only; {rejected[0]["id"]} was rejected ({rejected[0]["why"]})')
    def evidence_priority(sentence, source):
        if label == 'limit' and 'Rule 3' in r['governing_policy']:
            if source == 'Rule 3' and 'not capped' in sentence:
                return 0
            if source == r['driving_article'] and re.search(r'not limited by|not by itself require escalation', sentence):
                return 1
        elif label == 'deadline' and re.search(r'30 calendar days|60 calendar days', sentence):
            return 0
        elif label == 'credit' and re.search(r'Service-Outage Credit =|Calculate the credit|monthly recurring charge ÷ 30', sentence):
            return 0
        elif label == 'tax' and 'recurring plan charge only' in sentence:
            return 0
        return 2

    driving_candidates = retrieved
    if (label == 'limit' and 'Rule 2' in r['governing_policy']) or state.issue == 'billing_error':
        driving_candidates = sorted(retrieved, key=lambda hit: 'Refund Eligibility' not in articles[hit['id']]['category'])
    if label in ('tax', 'scope') and state.outage:
        driving_candidates = sorted(retrieved, key=lambda hit: 'Service-Outage Credit Policy' not in articles[hit['id']]['category'])
    for hit in driving_candidates:
        article = articles[hit['id']]
        category = article['category']
        if any(cat in category for cat in categories):
            if 'not a billing-dispute credit' in category and r['decision'] != 'decline':
                continue
            selected = [s for s in sentences(article) if any(re.search(p, s, re.I) for p in patterns)]
            if selected:
                r['driving_article'] = hit['id']
                selected.sort(key=lambda sentence: evidence_priority(sentence, hit['id']))
                r['evidence'].extend(selected)
                r['evidence_sources'].extend([hit['id']] * len(selected))
                break
    for key in r['governing_policy']:
        selected = [s for s in sentences(rules[key]) if any(re.search(p, s, re.I) for p in rule_patterns.get(key, []))]
        selected.sort(key=lambda sentence: evidence_priority(sentence, key))
        r['evidence'].extend(selected[:3])
        r['evidence_sources'].extend([key] * len(selected[:3]))
    if label in ('bill', 'tax', 'proration') and not state.outage and r['driving_article']:
        r['reply'] = ('For a mid-cycle plan change, the billing system prorates the old and new plan charges using (monthly charge / 30) x days each plan was active.' if label == 'proration' else ' '.join(r['evidence']))
    elif label == 'proration' and r['driving_article']:
        r['reply'] = "For a mid-cycle plan change, the billing system prorates the old and new plan charges using (monthly charge / 30) x days each plan was active. This calculation applies to plan changes."
    if r['decision'] == 'decline' and r['driving_article']:
        r['guards'].append(f'wrong-category article for a dispute: {r["driving_article"]} belongs to {articles[r["driving_article"]]["category"]}; routed to its separate team')
        source = articles[r['driving_article']]['text']
        team = re.search(r'Customer Retention queue|Device Protection team', source)[0]
        r.update(escalate_to=team, reply=f'Confirmed: This request is handled by the {team}. Not covered: Billing dispute policy does not authorize this separate program. Next: please contact the {team}; they handle this request. A handoff note has been prepared.')
    if not r['driving_article'] and patterns:
        if r['evidence']:
            r['reason'] += ' No retrieved article supports this reply; it stands on governing policy evidence.'
        elif r['decision'] != 'clarify':
            handoff('No retrieved source supports an answer to this question', 'evidence_gap')
    if r['escalation_basis'] == 'policy':
        r['guards'].append('front-line credit where Tier 2 must decide: no credit offered by the front line; ' + r['reason'])
    elif r['escalation_basis'] == 'evidence_gap':
        r['guards'].append('answer without evidence: blocked an unsupported answer and handed off the question')
    for hit in retrieved:
        article = articles[hit['id']]
        if (label in ('credit', 'limit', 'retention', 'device') or (label == 'tax' and state.outage)) and hit['id'] != r['driving_article'] and ('not a billing-dispute credit' in article['category'] or 'Account & Billing Basics' in article['category']):
            r['guards'].append(f'wrong-category article for a dispute: {hit["id"]} was not used; category {article["category"]} does not authorize dispute credits')
    ordered = sorted(zip(r['evidence'], r['evidence_sources']), key=lambda item: evidence_priority(*item))
    r['evidence'] = [item[0] for item in ordered]
    r['evidence_sources'] = [item[1] for item in ordered]
    return r


def question_types(text, state):
    base = intent(text, state)
    if base in ('human', 'outside', 'retention', 'device', 'identity', 'acknowledge'):
        return [base]
    t = text.lower()
    found = []
    for label, pattern in [
        ('limit', LIMIT),
        ('deadline', DEADLINE),
        ('scope', r'\b(?:taxes?|surcharges?|fees?|one.time|device charge|add.ons?|other charges)\b'),
        ('credit', r'\b(?:how much|credit amount|refund amount|calculate|calculated)\b'),
    ]:
        match = re.search(pattern, t if label != 'limit' else t.replace('time limit', ' ' * 10))
        if label == 'credit' and not re.search(r'credit|refund|money back', t):
            continue
        if match and (label != 'scope' or (state.outage and re.search(r'credit|refund|give.*back|cover|reduce', t))):
            found.append((match.start(), label))
    return [label for _, label in sorted(found)] or [base]


def respond(turn, number, state, rules, articles, retriever):
    state.update(turn['customer'])
    labels = question_types(turn['customer'], state)
    if state.verified and state.fraud_reported and any(
            label in ('credit', 'limit', 'scope', 'gap', 'tax', 'deadline', 'unresolved')
            for label in labels):
        labels = ['fraud']
    parts = [_respond(turn, number, state, rules, articles, retriever, label) for label in labels]
    r = parts[0]
    replies = [part['reply'] for part in parts]
    ranking = {'answer': 0, 'decline': 1, 'clarify': 2, 'escalate': 3}
    for part in parts[1:]:
        for key in ('governing_policy', 'rejected_policy', 'guards', 'computed_working'):
            r[key].extend(value for value in part[key] if value not in r[key])
        for quote, source in zip(part['evidence'], part['evidence_sources']):
            if (quote, source) not in list(zip(r['evidence'], r['evidence_sources'])):
                r['evidence'].append(quote)
                r['evidence_sources'].append(source)
        r['computed'].update(part['computed'])
        if ranking[part['decision']] > ranking[r['decision']]:
            for key in ('decision', 'escalate_to', 'escalation_basis', 'reason', 'escalation_check'):
                r[key] = part[key]
    r['intent'] = '+'.join(labels)
    r['reply'] = ' '.join(replies)
    if qualifies(state) and labels not in (['fraud'], ['human']):
        governing, rejected, computed, escalation = evaluate(state)
        r['computed'].update(computed)
        bad_cap = re.search(r'(?:Yes\.[^.]*\$75|(?:capped at|limited to|maximum of|no more than)\s+\$75)', r['reply'], re.I)
        if 'Rule 2' in r['governing_policy'] or bad_cap:
            r = _respond(turn, number, state, rules, articles, retriever, 'limit')
            r['guards'].append('Rule 3 lock: replaced incompatible general credit answer')
        if any(label in ('limit', 'deadline', 'credit', 'scope', 'tax') for label in labels):
            r['governing_policy'] = governing
            r['computed'].update(computed)
            if escalation and r['decision'] != 'escalate':
                r.update(decision='escalate', escalate_to='Tier 2 Billing Specialist', escalation_basis='policy')
                r['reply'] += ' Needs approval: ' + escalation + '. A Tier 2 Billing Specialist must decide before applying the credit.'
    if (state.ticket and state.start and 'credit' in r['computed'] and r['decision'] == 'answer'
            and any(label in ('credit', 'limit') for label in labels)):
        t_start = datetime.fromisoformat(state.ticket['start'])
        t_end = datetime.fromisoformat(state.ticket['end'])
        day = timedelta(days=1)
        claimed_end = state.end or state.start
        if state.start < t_start - day or claimed_end > t_end + day:
            c, days = r['computed']['credit'], r['computed']['full_days']
            why = (f'Rule 4b: ticket {state.ticket["id"]} covers {t_start.date()} to {t_end.date()} only; '
                   f'the customer reported {state.start.date()} to {claimed_end.date()} and the rest cannot be verified')
            r.update(decision='escalate', escalate_to='Tier 2 Billing Specialist', escalation_basis='policy',
                     reason=why, escalation_check=why)
            if 'Rule 4' not in r['governing_policy']:
                r['governing_policy'].append('Rule 4')
            r['reply'] = (f'Confirmed: outage ticket {state.ticket["id"]} confirms an outage from {t_start.date()} to {t_end.date()}, '
                          f'which is {days} full days; the credit for that period would be ${c:.2f}. '
                          f'Needs approval: the dates you gave ({state.start.date()} to {claimed_end.date()}) go beyond that ticket, '
                          'and the rest could not be verified. Next: a Tier 2 Billing Specialist needs to review this and decide; '
                          'nothing is applied until then. A handoff note has been prepared for them.')
            r['guards'].append('ticket treated as covering the whole claim: confirmed only the ticket period; the unverified dates go to Tier 2 under Rule 4b')
    if r['decision'] == 'answer' and 'acknowledge' not in labels:
        known = (LIMIT + '|' + DEADLINE + r'|credit|refund|disput|contest|charg|bill|invoice|statement|money back|owed|how much|amount|outage|service|tax|surcharge|fee|prorat|plan|account|card|\bpin\b|\$\d')
        dropped = []
        for sentence in re.split(r'(?<=[.!?])\s+', turn['customer']):
            if '?' not in sentence:
                continue
            for clause in re.split(r',?\s+\band\b\s+|;\s*', sentence):
                words = re.findall(r"[A-Za-z']+", clause)
                if len(words) < 3 or re.search(known, clause, re.I):
                    continue
                if len(words) <= 6 and re.search(r'\b(?:that|this|it|those|these)\b', clause, re.I):
                    continue
                dropped.append(clause.strip(' ?.!'))
        if dropped:
            quoted = '; '.join('"' + item + '"' for item in dropped)
            r.update(decision='escalate', escalate_to='Tier 2 Billing Specialist', escalation_basis='evidence_gap',
                     reason='Part of the request is not covered by the policy or help articles: ' + quoted)
            r['reply'] += (' Not covered: the policy and help articles do not address this part of your request: ' + quoted
                           + '. Next: a Tier 2 Billing Specialist needs to review this and decide; nothing is applied until then. A handoff note has been prepared for them.')
            r['guards'].append('dropping part of a mixed request: answered the supported part and handed off the part the documents do not cover')
    if r['decision'] in ('answer', 'escalate') and ('credit' in r['computed'] or 'rolling_total' in r['computed']):
        state.credit_answered = True
    r = finalize(r, labels, state)
    if r['decision'] == 'clarify':
        if state.clarify_count >= 2:
            r = takeover(r, state, 'stalled_clarification')
    state.clarify_count = state.clarify_count + 1 if r['decision'] == 'clarify' else 0
    return r


def takeover(result, state, basis):
    human = basis == 'customer_request'
    reason = ('The customer asked for a human.' if human else
              'Two clarifying questions brought no new information.')
    reply = ('Confirmed: you asked to speak with a person. Next: a Tier 2 '
             'Billing Specialist needs to take this over; a handoff note '
             'with this conversation has been prepared.' if human else
             'Confirmed: I asked twice for the details needed and do not '
             'have them. Next: a Tier 2 Billing Specialist needs to take '
             'this over; a handoff note has been prepared.')
    if human and not state.verified:
        reply += ' No account details are included because identity is not verified.'
    guard = ('ignoring a request for a human: did not keep the customer in '
             'the automated flow' if human else
             'asking a third time: handed off after two clarifying questions '
             'without progress')
    result.update(decision='escalate', escalate_to='Tier 2 Billing Specialist',
                  escalation_basis=basis, governing_policy=[],
                  rejected_policy=[], driving_article=None, evidence=[],
                  evidence_sources=[], computed={}, computed_working=[],
                  reason=reason, reply=reply, guards=[guard], escalation_check='')
    return result


def finalize(result, labels, state):
    allowed = {hit['id'] for hit in result['retrieved'][:3]} | set(result['governing_policy'])
    surviving = [(quote, source) for quote, source in zip(result['evidence'], result['evidence_sources']) if source in allowed]
    result['evidence'] = [quote for quote, _ in surviving]
    result['evidence_sources'] = [source for _, source in surviving]
    if result['driving_article'] not in allowed:
        result['driving_article'] = None
    if state.outage and any(label in ('scope', 'tax') for label in labels):
        facts = []
        computed = result['computed']
        formula = any(source == 'Rule 3' and 'Service-Outage Credit =' in quote for quote, source in surviving)
        if formula and 'credit' in computed:
            facts.append(f'The outage credit is calculated from the current monthly recurring charge: ${computed["monthly_recurring_charge"]:.2f} / 30 x {computed["full_days"]} full days = ${computed["credit"]:.2f}.')
        scope = any('This credit applies to the recurring plan charge only' in quote for quote, _ in surviving)
        if scope:
            facts.append('The outage credit applies to the recurring plan charge only.')
        prefix = 'Confirmed: ' + ' '.join(facts) + ' ' if facts else ''
        next_step = 'Next: a Tier 2 Billing Specialist needs to review this and decide; nothing is applied until then. A handoff note has been prepared for them.'
        if state.ticket:
            next_step += f' The note includes outage ticket {state.ticket["id"]}.'
        result['reply'] = prefix + 'Not covered: the documents do not say whether those other charges are adjusted or refunded. ' + next_step
    if state.outage and 'deadline' in labels:
        rejection = {'id': 'Rule 1', 'why': 'The 60-day statement window is the dispute window, not the outage-credit deadline.'}
        if not any(item['id'] == 'Rule 1' for item in result['rejected_policy']):
            result['rejected_policy'].append(rejection)
    guards = {}
    calculated = bool(re.search(r'(?:credit[^.]*\$|\$[^.]*credit|/ 30|rolling[^.]*total[^.]*\$)', result['reply'], re.I))
    for guard in result['guards']:
        label = guard.split(':', 1)[0]
        if label == 'blending two rules' and not calculated:
            continue
        guards.setdefault(label, guard)
    result['guards'] = list(guards.values())
    return result
