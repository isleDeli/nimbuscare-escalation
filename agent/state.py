import re
from datetime import datetime, timedelta

MONTHS = {name.lower(): i for i, name in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS['sept'] = 9
DATE = r'\b(?:\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2})?|(?:' + '|'.join(MONTHS) + r')\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm))?)'


def dates(text, year):
    result = []
    for m in re.finditer(DATE, text, re.I):
        s = m[0]
        try:
            if re.match(r'\d{4}-', s):
                d = datetime.fromisoformat(s)
            else:
                parts = re.match(r'(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?(?:\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm))?', s, re.I)
                if not (parts[3] or year):
                    continue
                hour = int(parts[4] or 0)
                if parts[6]:
                    hour = hour % 12 + (12 if parts[6].lower() == 'pm' else 0)
                d = datetime(int(parts[3] or year), MONTHS[parts[1].lower()], int(parts[2]), hour, int(parts[5] or 0))
            result.append((m.start(), d))
        except ValueError:
            continue
    return result


class State:
    def __init__(self, headers, date, monthly, fixtures):
        self.date, self.monthly, self.fixtures = date, monthly, fixtures
        self.account_id = headers.get('Account Number')
        self.account = {}
        self.verified = False
        self.mismatch = False
        self.issue = 'none'
        self.dispute = False
        self.start = self.end = self.statement = self.amount = self.line = None
        self.ticket = None
        self.review = False
        self.review_days = None
        self.incident_dates = []
        self.problem = False
        self.error = False
        self.other_team = None
        self.fraud_reported = False
        self.clarify_count = 0

    @property
    def outage(self):
        return self.issue == 'outage'

    def update(self, text):
        account = re.search(r'\bNMB-[\w-]+\b', text, re.I)
        if account and account[0].upper() != self.account_id:
            self.account_id = account[0].upper()
            self.verified = False
            self.account = {}
        credentials = re.search(r'(?:card(?:\s+\w+){0,3}|last\s*4(?:\s+digits)?|ending(?:\s+is)?|pin(?:\s+is)?)\D{0,15}(\d{4})\b', text, re.I)
        if credentials:
            record = self.fixtures.get('accounts', {}).get(self.account_id, {})
            key = 'pin' if 'pin' in credentials[0].lower() else 'card_last4'
            self.verified = bool(record) and str(record.get(key)) == credentials[1]
            self.mismatch = not self.verified
            self.account = record if self.verified else {}
        t = text.lower().replace("’", "'")
        fraud = re.search(
            r"\b(?:unauthori[sz]ed|not authori[sz]ed|didn't make|did not make|"
            r"never made|not me|someone else used|stolen identity|identity theft|"
            r"hacked|fraud)\b|\b(?:sim|device|line|phone number)\b[^.?!]{0,80}"
            r"\b(?:not registered|not on|not mine|unknown|unrecognized|"
            r"never registered|not registered|isn.t registered|wasn.t registered|"
            r"do not recognize|don.t recognize|not associated|not linked|"
            r"doesn.t belong|don.t own|never owned)\b|"
            r"\b(?:unknown|unrecognized|stolen)\s+(?:sim|line|device)\b|"
            r"\bsim\s+(?:was\s+)?stolen\b", t)
        self.fraud_reported |= bool(fraud)
        parsed = dates(text, self.date.year if self.date else None)
        incident = []
        statement = None
        for pos, value in parsed:
            prefix = text[max(0, pos-55):pos]
            if re.search(r'(?:invoice|statement|bill)\s+(?:(?:dated|date|of|from|on)\s+)?$', prefix, re.I):
                statement = value.date()
            else:
                incident.append(value)
        amounts = list(re.finditer(r'\$([\d,]+(?:\.\d+)?)', text))
        values = [float(m[1].replace(',', '')) for m in amounts]
        dispute_verb = bool(re.search(r'disput|contest|question(?:ing)?|challeng', t))
        scope = bool(re.search(r'also|as well|other charges|cover|reduce|give.*back', t) and
                     re.search(r'credit|refund', t) and not dispute_verb and statement is None)
        error = bool(re.search(r'(?:charg|bill)\w*.*(?:twice|double)|duplicate|double|too much|overcharg|extra|more than|wrong|incorrect|mistake|error|mis.billed|(?:promo|promotion|discount|coupon|code).*?(?:not applied|never applied|never.*applied|missing)|(?:add.on).*?(?:not ordered|never ordered|didn.t sign up)|never ordered', t))
        error |= bool(re.search(r"(?:never|didn't|did not)\s+(?:\w+\s+){0,3}(?:sign(?:ed)? up|order(?:ed)?|ask(?:ed)?|agree(?:d)?|request(?:ed)?|authoriz(?:e|ed)|want(?:ed)?|add(?:ed)?)\b|unauthori[sz]ed|not mine|shouldn.t be there", t))
        charge = bool(values and (statement or re.search(r'charge|fee|add.on|billed|charged|line item', t) or dispute_verb))
        new_item = not scope and (statement is not None or (dispute_verb and values and values[0] != self.amount))
        if new_item:
            self.line = self.amount = self.statement = None
            self.error = False
            if not incident:
                self.issue = 'none'
                if error:
                    self.incident_dates = []
                    self.start = self.end = None
        if statement:
            self.statement = statement
        if charge and not scope and (new_item or self.amount is None):
            chosen = values[0]
            for match, value in zip(amounts, values):
                around = t[max(0, match.start()-35):match.end()+35]
                if re.search(r'too much|overcharg|credit.*back|refund|give.*back|wrong|extra', around):
                    chosen = value
            self.amount, self.line = chosen, text
        self.error |= error and not scope
        self.dispute |= dispute_verb or (error and charge)
        if incident:
            self.incident_dates = incident
            self.start = incident[0]
            self.end = incident[1] if len(incident) > 1 else None
        matching = None
        if self.account_id and self.incident_dates:
            for ticket in self.fixtures.get('noc_tickets', []):
                if ticket.get('account') != self.account_id:
                    continue
                start = datetime.fromisoformat(ticket['start'])
                end = datetime.fromisoformat(ticket['end'])
                points = self.incident_dates
                if any(start.date() <= d.date() <= end.date() for d in points) or (len(points) > 1 and start <= points[-1] and end >= points[0]):
                    matching = ticket
                    break
        service = r'\b(?:service|signal|coverage|network|internet|connection|connect|reconnected|offline|online|bars|reception|calls|data|phones?|lines?)\b'
        failure = r'\b(?:no|nothing|lost|out|down|dead|stopped|cut off|offline|reconnected|not working|wasn.t working|couldn.t|unable|without|restored|came back|back up)\b'
        interruption = bool(re.search(r'outage|dead zone|it went out|\bcut off\b|\b(?:reconnect(?:ed)?|offline)\b', t) or
                            (re.search(service, t) and re.search(failure, t)))
        self.other_team = None
        device_noun = re.search(r"\b(?:my|our|his|her|their)\s+(?:[\w']+\s+){0,2}(?:phone|tablet|watch|handset|hotspot|router|modem|device|screen)(?:'s|s)?\b", t)
        device_harm = re.search(r'\b(?:cracked|broken|broke|smashed|damaged|lost|stolen|not working|malfunction\w*|replace|replacement|repair|claim)\b', t)
        device_plan = re.search(r'\b(?:protection|insurance) plan\b|\bdevice (?:protection|insurance)\b', t)
        device_request = bool((device_noun and device_harm) or device_plan)
        if device_request and not interruption and not self.fraud_reported:
            self.issue = 'other_team'
            self.other_team = 'device'
        elif matching or interruption:
            self.issue = 'outage'
        elif re.search(r'device protection|protection plan|replacement credit|(?:my|a|the) (?:phone|device|sim) (?:was |is |got )?(?:lost|stolen|broken|damaged|malfunctioning)|lost my (?:phone|device)|cracked screen', t):
            self.issue = 'other_team'
            self.other_team = 'device'
        elif re.search(r'(?:retention|loyalty)\s+credit|retention|(?:will|going to|want to|considering)\s+(?:cancel|leave|switch)|leaving|cancel(?:ling|ing)? (?:my |the )?service|switch carrier', t):
            self.issue = 'other_team'
            self.other_team = 'retention'
        elif self.error and self.amount is not None and (self.statement or self.line):
            self.issue = 'billing_error'
        self.problem |= bool(interruption or error or charge or re.search(r'bill|invoice|statement|problem|something|issue|isn.t right|doesn.t look right|help|money back|payment|stolen|still broken|happened again|down again', t))
        self.review = False
        self.review_days = None
        if self.verified:
            self.monthly = self.account.get('monthly_recurring_charge', self.monthly)
            if self.date:
                ages = [(self.date - datetime.fromisoformat(d).date()).days for d in self.account.get('resolved_disputes', [])]
                recent = [d for d in ages if 0 <= d <= 90]
                if recent:
                    self.review_days = min(recent)
            self.review = self.review_days is not None or bool(self.account.get('fraud_flags'))
        self.ticket = matching if self.verified and self.outage else None
