"""
data/input/create_sample_db.py
-------------------------------
Creates a sample SQLite database for testing the DBExtractor.
Run once: python data/input/create_sample_db.py
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "sample.db"


def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Customers table ───────────────────────────────────────────────────────
    cursor.execute("DROP TABLE IF EXISTS customers")
    cursor.execute("""
        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY,
            customer_name TEXT,
            email_address TEXT,
            telephone   TEXT,
            city        TEXT,
            country     TEXT,
            company     TEXT
        )
    """)

    customers = [
        (1, "Alice Johnson",  "alice@email.com",  "+1-555-0101", "New York",       "USA",          "Acme Corp"),
        (2, "Bob Smith",      "bob@email.com",    "+1-555-0102", "San Francisco",  "USA",          "TechGlobal"),
        (3, "Carol White",    "carol@email.com",  "+44-555-103", "London",         "UK",           "InnovateLtd"),
        (4, "David Brown",    "david@email.com",  "+91-555-104", "Bangalore",      "India",        "DataDriven"),
        (5, "Eva Martinez",   "eva@email.com",    "+34-555-105", "Madrid",         "Spain",        "CloudSystems"),
    ]
    cursor.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?,?,?)", customers
    )

    # ── Products table ────────────────────────────────────────────────────────
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("""
        CREATE TABLE products (
            id          INTEGER PRIMARY KEY,
            product_name TEXT,
            description TEXT,
            price       REAL,
            quantity    INTEGER,
            category    TEXT
        )
    """)

    products = [
        (1, "Laptop Pro",      "High-performance laptop with 16GB RAM",       1299.99, 50,  "Electronics"),
        (2, "Wireless Mouse",  "Ergonomic wireless mouse with USB receiver",   29.99,  200, "Accessories"),
        (3, "Standing Desk",   "Adjustable height standing desk",              349.00,  30,  "Furniture"),
        (4, "Python Course",   "Complete Python programming course",           49.99,  999, "Education"),
        (5, "Data Science Kit","Comprehensive data science toolkit bundle",    199.00,  20,  "Software"),
    ]
    cursor.executemany(
        "INSERT INTO products VALUES (?,?,?,?,?,?)", products
    )

    conn.commit()
    conn.close()
    print(f"✅ Sample database created: {DB_PATH}")
    print("   Tables: customers, products")


if __name__ == "__main__":
    create_db()
