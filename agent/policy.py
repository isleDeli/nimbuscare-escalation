from datetime import datetime, timedelta
import math


def qualifies(state):
    if not state.verified or not state.ticket or not state.date:
        return False
    start = datetime.fromisoformat(state.ticket['start'])
    end = datetime.fromisoformat(state.ticket['end'])
    return (end-start).total_seconds() > 4*3600 and 0 <= (state.date-end.date()).days <= 30


def evaluate(state):
    computed, rejected = {}, []
    if state.statement and state.date and not qualifies(state):
        age = (state.date - state.statement).days
        computed['days_since_statement'] = age
        if age > 60:
            if state.review:
                why = (f'Rule 5: prior resolved dispute {state.review_days} days ago is within 90 days' if state.review_days is not None else 'Rule 5: fraud indicators require Tier 2 review regardless of amount')
                return ['Rule 1', 'Rule 4', 'Rule 5'], rejected, computed, why
            return ['Rule 1'], rejected, computed, f'Rule 1: invoice is {age} days old against the 60-day window'
    if state.issue not in ('outage', 'billing_error'):
        return [], [], computed, None
    governing = ['Rule 2']
    escalation = None
    if state.outage:
        if not state.ticket:
            ids = ['Rule 2', 'Rule 4'] + (['Rule 5'] if state.review else [])
            why = 'Rule 4b: no outage ticket could be verified for the account and dates'
            if state.review:
                why = (f'Rule 5: prior resolved dispute {state.review_days} days ago is within 90 days' if state.review_days is not None else 'Rule 5: fraud indicators require Tier 2 review regardless of amount')
            return ids, [{'id': 'Rule 3', 'why': 'No verifiable NOC ticket for this account and dates.'}], {}, why
        start = datetime.fromisoformat(state.ticket['start'])
        end = datetime.fromisoformat(state.ticket['end'])
        hours = (end - start).total_seconds() / 3600
        age = (state.date - end.date()).days if state.date else None
        computed.update(outage_hours=hours, ticket_id=state.ticket['id'], days_since_resolution=age, request_deadline=(end.date() + timedelta(days=30)).isoformat())
        failure = None
        if hours <= 4:
            failure = f'Ticket duration {hours:g} hours does not exceed 4 consecutive hours.'
        elif age is None or not 0 <= age <= 30:
            failure = f'Request {age} days after resolution is outside the 30-calendar-day window.'
        if failure:
            rejected.append({'id': 'Rule 3', 'why': failure})
        else:
            governing = ['Rule 3']
            rejected.append({'id': 'Rule 2', 'why': 'The separate outage policy is not capped by the general $75.00 ceiling; Rule 4a does not apply.'})
            days = math.floor(hours / 24)
            computed.update(full_days=days, monthly_recurring_charge=state.monthly)
            if state.monthly is None:
                escalation = 'The monthly recurring charge is missing'
            else:
                credit = round(state.monthly / 30 * days, 2)
                computed['credit'] = credit
                if credit > 300:
                    escalation = f'Rule 4b: calculated credit ${credit:.2f} exceeds $300.00'
                elif hours > 720:
                    escalation = f'Rule 4b: outage {hours / 24:g} days exceeds 30 consecutive days'
    if 'Rule 2' in governing:
        assert state.issue == 'billing_error' or (state.outage and any(x['id'] == 'Rule 3' for x in rejected))
        used = float(state.account.get('goodwill_credits_last_12_months', 0))
        computed.update(goodwill_credits_last_12_months=used, remaining_allowance=round(max(0, 75-used), 2))
        if state.amount is not None:
            total = round(used + state.amount, 2)
            computed.update(requested_credit=state.amount, rolling_total=total, excess=round(max(0, total-75), 2))
            if total > 75:
                escalation = f'Rule 4a: rolling 12-month total ${total:.2f} exceeds $75.00'
    if state.review:
        governing += ['Rule 4', 'Rule 5']
        escalation = (f'Rule 5: prior resolved dispute {state.review_days} days ago is within 90 days' if state.review_days is not None else 'Rule 5: fraud indicators require Tier 2 review regardless of amount')
    elif escalation and escalation.startswith('Rule 4'):
        governing.append('Rule 4')
    return list(dict.fromkeys(governing)), rejected, computed, escalation
