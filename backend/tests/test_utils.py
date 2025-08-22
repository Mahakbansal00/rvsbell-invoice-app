from datetime import date, timedelta
from backend.utils import compute_aging_bucket

def test_future_due_date():
    assert compute_aging_bucket(date.today() + timedelta(days=5)) == "0"

def test_bucket_0_30():
    assert compute_aging_bucket(date.today() - timedelta(days=30)) == "0–30"

def test_bucket_31_60():
    assert compute_aging_bucket(date.today() - timedelta(days=45)) == "31–60"

def test_bucket_61_90():
    assert compute_aging_bucket(date.today() - timedelta(days=75)) == "61–90"

def test_bucket_90_plus():
    assert compute_aging_bucket(date.today() - timedelta(days=120)) == "90+"
