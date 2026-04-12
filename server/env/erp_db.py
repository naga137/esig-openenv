"""
ESIG Simulated ERP/CRM Database (SQLite).
Seeds realistic orders, invoices and customer records so graders
can deterministically verify agent responses.
"""
from __future__ import annotations
import sqlite3
import os
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "esig_erp.db")


# ---------------------------------------------------------------------------
# Schema & seeding
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    tier          TEXT DEFAULT 'silver',
    account_value REAL DEFAULT 0.0,
    sentiment     REAL DEFAULT 0.5,
    open_tickets  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    product       TEXT NOT NULL,
    amount_usd    REAL NOT NULL,
    status        TEXT DEFAULT 'processing',
    created_date  TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id    TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    order_id      TEXT NOT NULL,
    amount_usd    REAL NOT NULL,
    due_date      TEXT NOT NULL,
    paid          INTEGER DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);
"""

SEED_CUSTOMERS = [
    ("CUST001", "Acme Corp",       "billing@acme.com",    "gold",   150000.0, 0.85, 0),
    ("CUST002", "Globex Inc",      "support@globex.com",  "silver",  45000.0, 0.60, 2),
    ("CUST003", "Initech Ltd",     "orders@initech.com",  "at-risk",  8000.0, 0.30, 5),
    ("CUST004", "Umbrella Corp",   "ar@umbrella.com",     "gold",   320000.0, 0.90, 0),
    ("CUST005", "Stark Industries","tony@stark.com",      "gold",   980000.0, 0.95, 0),
]

SEED_ORDERS = [
    ("ORD-2024-001", "CUST001", "Enterprise SaaS Plan",     12500.0, "processing", "2024-11-01"),
    ("ORD-2024-002", "CUST002", "Professional License",      3200.0, "shipped",    "2024-11-03"),
    ("ORD-2024-003", "CUST003", "Starter Pack",               450.0, "on_hold",    "2024-11-05"),
    ("ORD-2024-004", "CUST004", "Platinum Support Bundle",  28000.0, "processing", "2024-11-08"),
    ("ORD-2024-005", "CUST005", "Custom AI Integration",   150000.0, "pending",    "2024-11-10"),
]

SEED_INVOICES = [
    ("INV-2024-0042", "CUST001", "ORD-2024-001", 12500.0, "2024-12-01", 0),
    ("INV-2024-0043", "CUST002", "ORD-2024-002",  3200.0, "2024-12-05", 1),
    ("INV-2024-0044", "CUST003", "ORD-2024-003",   450.0, "2024-11-20", 0),
    ("INV-2024-0045", "CUST004", "ORD-2024-004", 28000.0, "2024-12-10", 0),
    ("INV-2024-0046", "CUST005", "ORD-2024-005",150000.0, "2024-12-15", 0),
]


def seed_database() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    cur.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)", SEED_CUSTOMERS
    )
    cur.executemany(
        "INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?)", SEED_ORDERS
    )
    cur.executemany(
        "INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?)", SEED_INVOICES
    )
    conn.commit()
    conn.close()


def _get_conn() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        seed_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def query_erp(query_key: str, query_value: str) -> Optional[Dict[str, Any]]:
    """
    Look up ERP records by key/value.
    query_key: 'order_id' | 'invoice_id' | 'customer_id' | 'customer_email'
    """
    conn = _get_conn()
    try:
        if query_key == "order_id":
            row = conn.execute(
                "SELECT o.*, c.name, c.tier FROM orders o JOIN customers c "
                "ON o.customer_id = c.customer_id WHERE o.order_id = ?",
                (query_value,)
            ).fetchone()
        elif query_key == "invoice_id":
            row = conn.execute(
                "SELECT i.*, c.name, c.tier FROM invoices i JOIN customers c "
                "ON i.customer_id = c.customer_id WHERE i.invoice_id = ?",
                (query_value,)
            ).fetchone()
        elif query_key == "customer_id":
            row = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (query_value,)
            ).fetchone()
        elif query_key == "customer_email":
            row = conn.execute(
                "SELECT * FROM customers WHERE email = ?", (query_value,)
            ).fetchone()
        else:
            return None
        return dict(row) if row else None
    finally:
        conn.close()


def get_customer_context(customer_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_records() -> Dict[str, List[Dict]]:
    conn = _get_conn()
    try:
        orders = [dict(r) for r in conn.execute("SELECT * FROM orders").fetchall()]
        invoices = [dict(r) for r in conn.execute("SELECT * FROM invoices").fetchall()]
        return {"orders": orders, "invoices": invoices}
    finally:
        conn.close()
