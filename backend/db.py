import os
from datetime import date
from sqlalchemy import create_engine, Column, Integer, Numeric, Date, Text, ForeignKey, CheckConstraint, func, select
from sqlalchemy.orm import declarative_base, relationship, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./dev.db")  # default to sqlite for quick start

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    invoices = relationship("Invoice", back_populates="customer", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_invoice_amount_nonneg"),
    )
    customer = relationship("Customer", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_pos"),
    )
    invoice = relationship("Invoice", back_populates="payments")

def get_engine():
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    return engine

def init_db(drop=False):
    engine = get_engine()
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine

def seed_demo_data():
    engine = get_engine()
    with Session(engine) as s:
        if s.query(Customer).count() > 0:
            return
        # Seed customers
        acme = Customer(name="ACME Corp")
        globex = Customer(name="Globex LLC")
        initech = Customer(name="Initech")
        s.add_all([acme, globex, initech])
        s.flush()

        from datetime import timedelta
        today = date.today()
        invoices = [
            Invoice(customer_id=acme.customer_id, invoice_date=today.replace(day=1), due_date=today.replace(day=15), amount=10000),
            Invoice(customer_id=acme.customer_id, invoice_date=today.replace(day=5), due_date=today.replace(day=20), amount=4500),
            Invoice(customer_id=globex.customer_id, invoice_date=today.replace(day=2), due_date=today.replace(day=10), amount=7000),
            Invoice(customer_id=initech.customer_id, invoice_date=today.replace(day=3), due_date=today.replace(day=25), amount=9000),
        ]
        s.add_all(invoices)
        s.flush()

        payments = [
            Payment(invoice_id=invoices[0].invoice_id, payment_date=today, amount=2500),
            Payment(invoice_id=invoices[2].invoice_id, payment_date=today, amount=1000),
        ]
        s.add_all(payments)
        s.commit()
