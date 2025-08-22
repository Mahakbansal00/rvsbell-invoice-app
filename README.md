# Invoicing & Payments Dashboard

Stack: **Python (Flask)** + **SQLAlchemy** + **Postgres (or SQLite for quick start)** + **Vanilla JS + Chart.js**.

## 1) Run locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set DB (Postgres) — example:
export DATABASE_URL=postgresql+psycopg2://USER:PASS@localhost:5432/invoice_db

# Or skip this to use local SQLite dev.db
python app.py  # http://localhost:8000
```

Open `http://localhost:8000` in your browser.

The app auto-creates tables and seeds a few demo rows on first run.

## 2) Schema

Tables match your spec (constraints included): `customers`, `invoices`, `payments`.
See `backend/db.py` for SQLAlchemy model definitions.

## 3) Parameterized operations

- **List invoices with totals/outstanding/aging**: `GET /api/invoices?customer_id=&start=&end=`  
- **Add payment (partial allowed)**: `POST /api/payments` with JSON `{invoice_id, amount, payment_date}`  
- **Top 5 customers by outstanding**: `GET /api/top_customers_outstanding`  
- **KPIs**: `GET /api/kpis`

## 4) Utility function + tests

- `backend/utils.py` → `compute_aging_bucket(due_date, today)`  
- Tests: `backend/tests/test_utils.py` (pytest)

```bash
cd backend
pytest -q
```

## 5) GitHub workflow

```bash
git init
git add .
git commit -m "chore: bootstrap project"

git branch -M main
git checkout -b feature/invoice-dashboard
git commit --allow-empty -m "feat: invoice dashboard (PR)"
git push origin feature/invoice-dashboard

# On GitHub: open a Pull Request from feature/invoice-dashboard -> main
```

PR description template:
- What: dashboard + KPIs + aging + payments + chart
- Why: ops visibility & cash collection
- How: Flask API, parameterized queries (SQLAlchemy), vanilla JS
- Testing: pytest for aging buckets
- Screens: see `/screenshots`

## 6) Environment

- `DATABASE_URL` (Postgres/MySQL/SQLite URI). Examples:
  - Postgres: `postgresql+psycopg2://USER:PASS@HOST:PORT/DBNAME`
  - MySQL: `mysql+pymysql://USER:PASS@HOST:PORT/DBNAME`
  - SQLite (default for quick start): `sqlite+pysqlite:///./dev.db`

## 7) Endpoints (cURL)

```bash
curl http://localhost:8000/api/customers
curl "http://localhost:8000/api/invoices?start=2025-01-01&end=2025-12-31"
curl -X POST http://localhost:8000/api/payments -H "Content-Type: application/json"   -d '{"invoice_id":1,"amount":500,"payment_date":"2025-08-22"}'
curl http://localhost:8000/api/top_customers_outstanding
curl http://localhost:8000/api/kpis
```

---

Made for: **RVSBELL Analytics Private Limited** spec.
# rvsbell-invoice-app
![alt text](<Screenshot 2025-08-22 at 11.37.03-1.png>)