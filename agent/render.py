import os
import sys
import textwrap


_WIDTH = 78
_LABEL = 12
_COLORS = {
    'answer': '30;42',
    'clarify': '30;46',
    'escalate': '30;43',
    'decline': '1;97;41',
}


def _cut(value, width):
    value = str(value)
    if len(value) <= width:
        return value
    return value[:max(0, width - 3)] + '...'


def _lines(value, width, limit=None):
    lines = []
    for paragraph in str(value).splitlines() or ['']:
        wrap_width = width
        while True:
            wrapped = textwrap.wrap(
                paragraph, width=wrap_width, break_long_words=True,
                break_on_hyphens=False, replace_whitespace=False,
            ) or ['']
            excess = max(len(line.encode('utf-8')) - width for line in wrapped)
            if excess <= 0 or wrap_width <= 1:
                break
            wrap_width = max(1, wrap_width - excess)
        lines.extend(wrapped)
    if limit and len(lines) > limit:
        lines = lines[:limit]
        last = lines[-1].rstrip(' .')
        while len(last.encode('utf-8')) > width - 3:
            last = last[:-1]
        lines[-1] = last.rstrip() + '...'
    return lines


def render(result, *, handoff_only=False):
    color = (sys.stdout.isatty() and 'NO_COLOR' not in os.environ
             and os.environ.get('TERM') != 'dumb')

    def style(value, code):
        return '\033[' + code + 'm' + value + '\033[0m' if color else value

    def row(label, value, limit=None, dim=False, hanging=0):
        lines = _lines(str(value)[hanging:], _WIDTH - _LABEL - hanging, limit)
        for index, line in enumerate(lines):
            prefix = label.ljust(_LABEL) if index == 0 else ' ' * _LABEL
            line = (str(value)[:hanging] if index == 0 else ' ' * hanging) + line
            if dim:
                print(style(prefix + line, '2'))
            else:
                print((style(prefix, '1') if index == 0 else prefix) + line)

    def speaker(label, prefix, value, limit=None, dim=False):
        lines = _lines(prefix + str(value), _WIDTH - _LABEL, limit)
        remaining = len(prefix)
        for index, line in enumerate(lines):
            column = label.ljust(_LABEL) if index == 0 else ' ' * _LABEL
            count = min(remaining, len(line))
            named = style(line[:count], '1') + line[count:] if count else line
            remaining = max(0, remaining - len(line) - 1)
            print((style(column, '1') if index == 0 else column) + named)

    def handoffs():
        notes = result.get('handoff_notes') or []
        if not notes:
            print('No handoff: nothing needs a human.')
        fields = ('customer', 'decision_needed', 'why_a_human',
                  'what_happened', 'already_settled', 'not_promised')
        for note in notes:
            print()
            heading = '== HANDOFF NOTE (prepared, not sent) for ' + str(note['for']) + ' '
            for line in _lines(heading + '====', _WIDTH):
                print(line.ljust(_WIDTH, '='))
            total = 1
            for key in fields:
                values = note[key] if isinstance(note[key], list) else [note[key]]
                total += sum(len(_lines(value, _WIDTH - 17, 2 if key == 'what_happened' else None)) for value in values)
            for key in fields:
                values = note[key] if isinstance(note[key], list) else [note[key]]
                for position, value in enumerate(values):
                    label = key.replace('_', ' ').upper() if position == 0 else ''
                    limit = None
                    for index, line in enumerate(_lines(value, _WIDTH - 17, limit)):
                        column = label.ljust(17) if index == 0 else ' ' * 17
                        print((style(column, '1') if index == 0 else column) + line)

    people = result.get('participants') or {}
    customer_name = str(people.get('customer') or 'Customer')
    human_name = people.get('human_agent')
    turns = result.get('turns') or []
    titles = result.get('rule_titles') or {}
    sources = result.get('sources') or {}
    print('NimbusCare billing-support agent - per-turn trace')
    row('FILE', result.get('conversation', '-'))
    row('SOURCES', 'policy: ' + str(sources.get('policy') or
        'data/policy-bil-pol-014.md') + '   kb: ' + str(sources.get('kb') or
        'data/kb-billing-credits.md') + '   network: none')
    print()

    if handoff_only:
        handoffs()
        return

    for index, turn in enumerate(turns, 1):
        decision = str(turn.get('decision') or 'clarify').lower()
        tag = '[' + decision.upper() + ']'
        left = '== TURN ' + str(turn.get('turn', index)) + '/' + str(len(turns))
        left += '  ' + str(turn.get('time') or '--:--') + ' '
        right = ' ' + tag + ' =='
        header = left + '=' * max(0, _WIDTH - len(left) - len(right))
        print(header + ' ' + style(tag, _COLORS.get(decision, '0')) + ' ==')
        destination = str(turn.get('escalate_to') or '-')
        explanation = decision.upper()
        if decision == 'escalate':
            explanation += ' -> ' + destination
        elif decision == 'decline':
            explanation += ' out of scope -> ' + destination
        speaker('CUSTOMER', customer_name + ': ', turn.get('customer') or '')
        row('ISSUE', str(turn.get('issue') or 'none') + ' (question: ' +
            str(turn.get('intent') or '-') + ')')

        driving = turn.get('driving_article')
        articles = sorted(turn.get('retrieved') or [],
                          key=lambda item: float(item.get('score') or 0),
                          reverse=True)[:3]
        if not articles:
            row('ARTICLES', '- none')
        for position, article in enumerate(articles):
            identifier = str(article.get('id') or '-')
            active = driving is not None and identifier == driving
            start = ('> ' if active else '  ') + identifier + '  '
            end = '  ' + format(float(article.get('score') or 0), '.1f')
            if active:
                end += '  DROVE'
            title = _cut(article.get('title') or '',
                         max(3, _WIDTH - _LABEL - len(start) - len(end)))
            row('ARTICLES' if position == 0 else '', start + title + end)

        governing = turn.get('governing_policy') or []
        if not governing:
            row('RULE', '- none')
        for position, identifier in enumerate(governing):
            title = titles.get(identifier)
            value = '> ' + identifier
            if title:
                value += '  ' + _cut(title, _WIDTH - _LABEL - len(value) - 11)
            row('RULE' if position == 0 else '', value + '  GOVERNS')
        for rejected in turn.get('rejected_policy') or []:
            prefix = 'x ' + str(rejected.get('id') or '-') + '  rejected: '
            row('', prefix + str(rejected.get('why') or '-'), hanging=len(prefix))

        check = turn.get('escalation_check') or ''
        row('ESCALATION', check or '- none checked')
        basis = str(turn.get('escalation_basis') or 'policy').replace('_', ' ')
        if decision == 'escalate':
            row('', '-> ' + destination + ' (' + basis + ')')
        elif decision == 'decline':
            row('', 'out of scope -> ' + destination)

        quotes = turn.get('evidence') or []
        identifiers = turn.get('evidence_sources') or []
        selected = list(range(len(quotes)))
        for count, position in enumerate(selected[:2]):
            source = identifiers[position] if position < len(identifiers) else None
            quote = (str(source) + '  ' if source else '') + '"' + str(quotes[position]) + '"'
            row('EVIDENCE' if count == 0 else '', quote, limit=2, hanging=len(str(source)) + 3 if source else 1)
        if turn.get('escalation_basis') == 'evidence_gap':
            row('EVIDENCE' if not quotes else '',
                'GAP      no rule or retrieved article answers the escalated part')

        working = turn.get('computed_working') or []
        if working:
            row('NUMBERS', '   '.join(str(item) for item in working))
        for position, guard in enumerate(turn.get('guards') or []):
            row('AVOIDED' if position == 0 else '', '! ' + str(guard))
        row('DECISION', explanation + ' - ' + str(turn.get('reason') or '-'))
        speaker('REPLY', 'NimbusCare agent (automated): ', turn.get('reply') or '')
        if turn.get('original_agent_reply'):
            prefix = (str(human_name) + ' (human agent, not evidence): '
                      if human_name else 'Human agent (not evidence): ')
            speaker('ORIGINAL', prefix, turn['original_agent_reply'], limit=2)
        print()

    counts = {key: sum(turn.get('decision') == key for turn in turns)
              for key in _COLORS}
    summary = '== SUMMARY  ' + str(len(turns)) + ' turns: ' + ', '.join(
        str(counts[key]) + ' ' + key for key in _COLORS) + ' '
    for line in _lines(summary, _WIDTH):
        print((line.rstrip() + ' ').ljust(_WIDTH, '='))
    print(' #  TIME   DECISION   RULE    ARTICLE  MISTAKE AVOIDED')
    for index, turn in enumerate(turns, 1):
        decision = str(turn.get('decision') or 'clarify').lower()
        rules = turn.get('governing_policy') or []
        guards = turn.get('guards') or []
        mistake = str(guards[0]).split(': ', 1)[0] if guards else '-'
        start = (str(turn.get('turn', index)).rjust(2) + '  ' +
                 str(turn.get('time') or '--:--').ljust(5) + '  ')
        cell = decision.upper().ljust(9)
        rest = ('  ' + (str(rules[0]) if rules else '-').ljust(6) + '  ' +
                str(turn.get('driving_article') or '-').ljust(7) + '  ')
        available = _WIDTH - len(start) - len(cell) - len(rest)
        print(start + style(cell, _COLORS.get(decision, '0')) + rest +
              _cut(mistake, max(3, available)))
    handoffs()
