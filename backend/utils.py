from datetime import date

def compute_aging_bucket(due_date: date, today: date | None = None) -> str:
    if today is None:
        today = date.today()
    delta = (today - due_date).days
    if delta <= 0:
        return "0"
    if delta <= 30:
        return "0–30"
    if delta <= 60:
        return "31–60"
    if delta <= 90:
        return "61–90"
    return "90+"
