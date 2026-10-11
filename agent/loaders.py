import re
from pathlib import Path
from datetime import datetime


def clean(text):
    return text.replace('*', '').replace('`', '')


def documents(path, kind):
    raw = Path(path).read_text(encoding='utf-8')
    pattern = r'^## (Rule \d+) — (.+)$' if kind == 'policy' else r'^### (KB-\d+) — (.+)$'
    matches = list(re.finditer(pattern, raw, re.M))
    result = {}
    for i, match in enumerate(matches):
        body = clean(raw[match.end():matches[i+1].start() if i+1 < len(matches) else len(raw)]).strip()
        category = re.search(r'Category:\s*(.*?)\s*·', body)
        result[match[1]] = dict(id=match[1], title=match[2], text=body, category=category[1] if category else '')
    return result


def sentences(document):
    text = document['text']
    text = re.sub(r'^\s*(?:\d+\.|- [a-d]\.|- |>)\s*', '', text, flags=re.M)
    return [s.strip(' \n-') for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip() and not s.startswith(('---', 'Category:'))]


def conversation(path):
    raw = Path(path).read_text(encoding='utf-8')
    headers = dict(re.findall(r'^(Date|Account Number|Plan):\s*(.+)$', raw, re.M))
    date = None
    for fmt in ('%B %d, %Y', '%Y-%m-%d', '%b %d, %Y'):
        try:
            date = datetime.strptime(headers.get('Date', ''), fmt).date()
            break
        except ValueError:
            pass
    # A missing date must not introduce wall-clock nondeterminism.
    turns = []
    for m in re.finditer(r'^\[(\d{2}:\d{2})\] (Customer|Agent)(?: \([^\n]*?\))?:\s*(.*)$', raw, re.M):
        if m[2] == 'Customer':
            turns.append(dict(time=m[1], customer=m[3]))
        elif turns:
            turns[-1]['original_agent_reply'] = m[3]
    amount = re.search(r'\$([\d,]+(?:\.\d+)?)', headers.get('Plan', ''))
    return headers, date, float(amount[1].replace(',', '')) if amount else None, turns
