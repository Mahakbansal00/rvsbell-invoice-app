import os
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import Session

# ✅ Import from the backend package (make sure backend/__init__.py exists)
from backend.db import (
    init_db,
    get_engine,
    Customer,
    Invoice,
    Payment,
    seed_demo_data,
)
from backend.utils import compute_aging_bucket

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)

# Initialize DB (creates tables if needed)
init_db(drop=False)
seed_demo_data()


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/customers")
def get_customers():
    engine = get_engine()
    with Session(engine) as s:
        rows = (
            s.execute(
                select(Customer.customer_id, Customer.name).order_by(Customer.name)
            ).all()
        )
        return jsonify(
            [{"customer_id": r.customer_id, "name": r.name} for r in rows]
        )


@app.get("/api/invoices")
def list_invoices():
    # Query params: customer_id (optional), start (invoice_date), end (invoice_date)
    customer_id = request.args.get("customer_id", type=int)
    start = request.args.get("start")
    end = request.args.get("end")

    engine = get_engine()
    with Session(engine) as s:
        paid_subq = (
            select(
                Payment.invoice_id,
                func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )

        q = (
            select(
                Invoice.invoice_id,
                Customer.name.label("customer_name"),
                Invoice.amount,
                func.coalesce(paid_subq.c.total_paid, 0).label("total_paid"),
                (Invoice.amount - func.coalesce(paid_subq.c.total_paid, 0)).label(
                    "outstanding"
                ),
                Invoice.invoice_date,
                Invoice.due_date,
            )
            .join(Customer, Customer.customer_id == Invoice.customer_id)
            .join(paid_subq, paid_subq.c.invoice_id == Invoice.invoice_id, isouter=True)
        )

        conditions = []
        if customer_id:
            conditions.append(Invoice.customer_id == customer_id)
        if start:
            conditions.append(Invoice.invoice_date >= parse_date(start))
        if end:
            conditions.append(Invoice.invoice_date <= parse_date(end))
        if conditions:
            q = q.where(and_(*conditions))

        rows = s.execute(q.order_by(Invoice.invoice_id.desc())).all()

        result = []
        today = date.today()
        for r in rows:
            outstanding = float(r.outstanding)
            # Aging bucket applies to unpaid portion only; mark fully paid as "Paid"
            if outstanding <= 0:
                aging_bucket = "Paid"
            else:
                aging_bucket = compute_aging_bucket(r.due_date, today)

            result.append(
                {
                    "invoice_id": r.invoice_id,
                    "customer_name": r.customer_name,
                    "amount": float(r.amount),
                    "total_paid": float(r.total_paid),
                    "outstanding": outstanding,
                    "invoice_date": r.invoice_date.isoformat(),
                    "due_date": r.due_date.isoformat(),
                    "aging_bucket": aging_bucket,
                }
            )
        return jsonify(result)


@app.post("/api/payments")
def add_payment():
    data = request.get_json(force=True)
    invoice_id = int(data["invoice_id"])
    amount = Decimal(str(data["amount"]))
    payment_date = parse_date(data["payment_date"])

    engine = get_engine()
    with Session(engine) as s:
        inv = s.get(Invoice, invoice_id)
        if inv is None:
            return jsonify({"error": "Invoice not found"}), 404

        paid = s.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice_id
            )
        ).scalar_one()

        outstanding = inv.amount - paid
        if amount <= 0 or amount > outstanding:
            return (
                jsonify(
                    {
                        "error": f"Invalid amount. Outstanding is {float(outstanding):.2f}"
                    }
                ),
                400,
            )

        p = Payment(invoice_id=invoice_id, payment_date=payment_date, amount=amount)
        s.add(p)
        s.commit()
        return jsonify({"status": "ok", "payment_id": p.payment_id})


@app.get("/api/top_customers_outstanding")
def top_customers_outstanding():
    engine = get_engine()
    with Session(engine) as s:
        paid_subq = (
            select(
                Payment.invoice_id,
                func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )
        q = (
            select(
                Customer.customer_id,
                Customer.name,
                func.sum(
                    Invoice.amount - func.coalesce(paid_subq.c.total_paid, 0)
                ).label("total_outstanding"),
            )
            .join(Invoice, Invoice.customer_id == Customer.customer_id)
            .join(paid_subq, paid_subq.c.invoice_id == Invoice.invoice_id, isouter=True)
            .group_by(Customer.customer_id, Customer.name)
            .order_by(desc("total_outstanding"))
            .limit(5)
        )
        rows = s.execute(q).all()
        return jsonify(
            [
                {
                    "customer_id": r.customer_id,
                    "name": r.name,
                    "total_outstanding": float(r.total_outstanding),
                }
                for r in rows
            ]
        )


@app.get("/api/kpis")
def kpis():
    engine = get_engine()
    with Session(engine) as s:
        total_invoiced = s.execute(
            select(func.coalesce(func.sum(Invoice.amount), 0))
        ).scalar_one()
        total_received = s.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
        ).scalar_one()

        paid_subq = (
            select(
                Payment.invoice_id,
                func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
            )
            .group_by(Payment.invoice_id)
            .subquery()
        )
        invs = s.execute(
            select(
                Invoice.due_date,
                (Invoice.amount - func.coalesce(paid_subq.c.total_paid, 0)).label(
                    "outstanding"
                ),
            ).join(paid_subq, paid_subq.c.invoice_id == Invoice.invoice_id, isouter=True)
        ).all()

        total_outstanding = sum(float(r.outstanding) for r in invs)
        today = date.today()
        overdue_outstanding = sum(
            float(r.outstanding)
            for r in invs
            if r.due_date < today and float(r.outstanding) > 0
        )
        pct_overdue = (
            (overdue_outstanding / total_outstanding * 100.0)
            if total_outstanding > 0
            else 0.0
        )

        return jsonify(
            {
                "total_invoiced": float(total_invoiced),
                "total_received": float(total_received),
                "total_outstanding": float(total_outstanding),
                "percent_overdue": round(pct_overdue, 2),
            }
        )


if __name__ == "__main__":
    # Running directly (useful during development)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
