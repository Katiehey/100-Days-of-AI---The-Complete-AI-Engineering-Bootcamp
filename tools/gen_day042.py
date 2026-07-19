#!/usr/bin/env python3
"""Generate all Day 042 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_042"

_cid = 0


def cid():
    global _cid
    _cid += 1
    return f"c{_cid:04d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cid(),
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "ai-course",
                "language": "python",
                "name": "ai-course",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

BASE_IMPORTS = """\
import warnings
warnings.filterwarnings('ignore')
import sqlite3
import pandas as pd"""

SETUP_DB_IMPL = """\
import sqlite3

def setup_db(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id  INTEGER PRIMARY KEY,
            product   TEXT,
            category  TEXT,
            region    TEXT,
            price     REAL,
            quantity  INTEGER,
            revenue   REAL
        )''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product    TEXT PRIMARY KEY,
            category   TEXT,
            unit_price REAL
        )''')
    rows = [
        (1,'Widget','Electronics','North',25.0,10,250.0),
        (2,'Gadget','Electronics','South',150.0,3,450.0),
        (3,'Widget','Electronics','South',25.0,5,125.0),
        (4,'Doohickey','Accessories','East',8.0,50,400.0),
        (5,'Gadget','Electronics','East',150.0,7,1050.0),
        (6,'Widget','Electronics','East',25.0,4,100.0),
        (7,'Doohickey','Accessories','North',8.0,20,160.0),
        (8,'Gadget','Electronics','North',150.0,2,300.0),
        (9,'Widget','Electronics','West',25.0,6,150.0),
        (10,'Doohickey','Accessories','South',8.0,15,120.0),
        (11,'Thingamajig','Accessories','North',200.0,1,200.0),
        (12,'Thingamajig','Accessories','East',200.0,4,800.0),
    ]
    cur.executemany(
        'INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)', rows
    )
    products = [
        ('Widget','Electronics',25.0),
        ('Gadget','Electronics',150.0),
        ('Doohickey','Accessories',8.0),
        ('Thingamajig','Accessories',200.0),
    ]
    cur.executemany(
        'INSERT OR IGNORE INTO products VALUES (?,?,?)', products
    )
    conn.commit()"""

RUN_QUERY_IMPL = """\
def run_query(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]"""

FILTER_ORDERS_IMPL = """\
def filter_orders(conn, region=None, category=None, min_revenue=None):
    conditions = []
    params = []
    if region is not None:
        conditions.append('region = ?')
        params.append(region)
    if category is not None:
        conditions.append('category = ?')
        params.append(category)
    if min_revenue is not None:
        conditions.append('revenue >= ?')
        params.append(min_revenue)
    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    sql = f'SELECT * FROM orders {where} ORDER BY order_id'
    return run_query(conn, sql, tuple(params))"""

GROUP_REVENUE_IMPL = """\
def group_revenue(conn, group_col):
    sql = (
        f'SELECT {group_col}, SUM(revenue) AS total, '
        'COUNT(*) AS orders, ROUND(AVG(revenue), 2) AS avg_revenue '
        f'FROM orders GROUP BY {group_col} ORDER BY total DESC'
    )
    return run_query(conn, sql)"""

JOIN_SUMMARY_IMPL = """\
def join_summary(conn):
    sql = (
        'SELECT o.region, p.category, '
        'SUM(o.revenue) AS total_revenue, COUNT(*) AS order_count '
        'FROM orders o '
        'INNER JOIN products p ON o.product = p.product '
        'GROUP BY o.region, p.category '
        'ORDER BY total_revenue DESC'
    )
    return run_query(conn, sql)"""

ALL_IMPLS = "\n\n\n".join([
    SETUP_DB_IMPL,
    RUN_QUERY_IMPL,
    FILTER_ORDERS_IMPL,
    GROUP_REVENUE_IMPL,
])

# ---------------------------------------------------------------------------
# Exercise 01 — setup_db
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 042 — Exercise 1: setup_db\n\n"
            "**What you'll build:** `setup_db(conn) -> None` — create two tables "
            "(`orders` and `products`) and insert the RETAIL_CSV dataset using "
            "`cursor.executemany`.\n\n"
            "**Why it matters:** Before you can query anything, the data must live "
            "in a database. SQLite needs no server — `sqlite3.connect(':memory:')` "
            "creates a full relational database in RAM in one line. "
            "`executemany` inserts all rows in one call, far faster than a loop of "
            "individual `execute` calls."
        ),
        code(BASE_IMPORTS),
        md("## Your Implementation"),
        code(
            "import sqlite3\n"
            "\n"
            "def setup_db(conn):\n"
            '    """\n'
            "    Create orders and products tables and insert the retail dataset.\n\n"
            "    orders columns: order_id, product, category, region, price, quantity, revenue\n"
            "    products columns: product (PK), category, unit_price\n\n"
            "    Use cursor.executemany with parameterized INSERT OR IGNORE.\n"
            "    Call conn.commit() at the end.\n"
            '    """\n'
            "    cur = conn.cursor()\n"
            "    # TODO: CREATE TABLE IF NOT EXISTS orders (\n"
            "    #           order_id INTEGER PRIMARY KEY, product TEXT,\n"
            "    #           category TEXT, region TEXT, price REAL,\n"
            "    #           quantity INTEGER, revenue REAL)\n"
            "    # TODO: CREATE TABLE IF NOT EXISTS products (\n"
            "    #           product TEXT PRIMARY KEY, category TEXT, unit_price REAL)\n"
            "    # TODO: cur.executemany('INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)', rows)\n"
            "    # TODO: cur.executemany('INSERT OR IGNORE INTO products VALUES (?,?,?)', products)\n"
            "    # TODO: conn.commit()\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'setup_db' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: setup_db is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: orders table has 12 rows\n"
            "    try:\n"
            "        conn = sqlite3.connect(':memory:')\n"
            "        setup_db(conn)\n"
            "        cur = conn.cursor()\n"
            "        cur.execute('SELECT COUNT(*) FROM orders')\n"
            "        n = cur.fetchone()[0]\n"
            "        assert n == 12, f'expected 12 rows, got {n}'\n"
            "        passed += 1; print('\\u2705 Check 2: orders table has 12 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        conn = None\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: total revenue is 4105.0\n"
            "    try:\n"
            "        cur.execute('SELECT SUM(revenue) FROM orders')\n"
            "        total_rev = cur.fetchone()[0]\n"
            "        assert abs(total_rev - 4105.0) < 0.01, f'expected 4105.0, got {total_rev}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: total revenue = {total_rev}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: products table has 4 rows\n"
            "    try:\n"
            "        cur.execute('SELECT COUNT(*) FROM products')\n"
            "        np = cur.fetchone()[0]\n"
            "        assert np == 4, f'expected 4 products, got {np}'\n"
            "        passed += 1; print('\\u2705 Check 4: products table has 4 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: Gadget is in products with unit_price 150.0\n"
            "    try:\n"
            "        cur.execute('SELECT unit_price FROM products WHERE product = ?', ('Gadget',))\n"
            "        price = cur.fetchone()[0]\n"
            "        assert price == 150.0, f'expected 150.0, got {price}'\n"
            "        passed += 1; print('\\u2705 Check 5: Gadget unit_price = 150.0')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "    finally:\n"
            "        if conn: conn.close()\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + SETUP_DB_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — run_query
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    setup = BASE_IMPORTS + "\n\n\n" + SETUP_DB_IMPL + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)"
    return [
        md(
            "# Day 042 — Exercise 2: run_query\n\n"
            "**What you'll build:** `run_query(conn, sql, params=()) -> list[dict]` — "
            "execute any SQL statement and return the rows as a list of dicts, "
            "with column names from `cursor.description`.\n\n"
            "**Why it matters:** `cursor.fetchall()` returns plain tuples — you have "
            "to know column positions to access values. Converting to dicts "
            "(via `cursor.description`) makes results self-documenting and indexable by "
            "name: `row['revenue']` instead of `row[6]`. This single helper replaces "
            "all boilerplate for the rest of the day."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def run_query(conn, sql, params=()):\n"
            '    """\n'
            "    Execute a SQL query and return rows as a list of dicts.\n\n"
            "    Args:\n"
            "        conn   — sqlite3 connection\n"
            "        sql    — SQL string (may contain ? placeholders)\n"
            "        params — tuple of values for ? placeholders (default: empty)\n"
            "    Returns:\n"
            "        list[dict] — one dict per row, keys = column names\n"
            '    """\n'
            "    cur = conn.cursor()\n"
            "    # TODO: cur.execute(sql, params)\n"
            "    # TODO: cols = [col[0] for col in cur.description]\n"
            "    # TODO: return [dict(zip(cols, row)) for row in cur.fetchall()]\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'run_query' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: run_query is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = run_query(conn, 'SELECT * FROM orders')\n"
            "        assert isinstance(result, list), f'expected list, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: returns 12 rows\n"
            "    try:\n"
            "        assert len(result) == 12, f'expected 12 rows, got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 3: SELECT * returns 12 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: rows are dicts with column names\n"
            "    try:\n"
            "        row = result[0]\n"
            "        assert isinstance(row, dict), f'expected dict, got {type(row).__name__}'\n"
            "        assert 'revenue' in row, f'revenue column missing, got {list(row.keys())}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: rows are dicts (keys: {list(row.keys())})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: params= works for WHERE clause\n"
            "    try:\n"
            "        north = run_query(conn,\n"
            "                          'SELECT * FROM orders WHERE region = ?', ('North',))\n"
            "        assert len(north) == 4, f'North should have 4 rows, got {len(north)}'\n"
            "        assert all(r['region'] == 'North' for r in north)\n"
            "        passed += 1; print('\\u2705 Check 5: parameterized WHERE works (North=4 rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + RUN_QUERY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — filter_orders
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + SETUP_DB_IMPL + "\n\n\n"
        + RUN_QUERY_IMPL
        + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)"
    )
    return [
        md(
            "# Day 042 — Exercise 3: filter_orders\n\n"
            "**What you'll build:** `filter_orders(conn, region=None, category=None, "
            "min_revenue=None) -> list[dict]` — build a dynamic WHERE clause from "
            "optional keyword arguments using parameterized queries.\n\n"
            "**Why it matters:** Real queries often need optional filters. "
            "Building the WHERE clause dynamically — appending conditions and params "
            "in parallel lists — is the correct pattern. The `?` placeholder keeps "
            "values out of the SQL string entirely, which prevents SQL injection "
            "and handles quoting correctly for any value type."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def filter_orders(conn, region=None, category=None, min_revenue=None):\n"
            '    """\n'
            "    Query orders with optional WHERE filters.\n\n"
            "    Build conditions and params in parallel lists.\n"
            "    Join conditions with AND. Use run_query.\n\n"
            "    Returns:\n"
            "        list[dict] — matching rows ordered by order_id\n"
            '    """\n'
            "    conditions = []\n"
            "    params = []\n"
            "    # TODO: if region is not None: append 'region = ?' and region\n"
            "    # TODO: if category is not None: append 'category = ?' and category\n"
            "    # TODO: if min_revenue is not None: append 'revenue >= ?' and min_revenue\n"
            "    # TODO: where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''\n"
            "    # TODO: sql = f'SELECT * FROM orders {where} ORDER BY order_id'\n"
            "    # TODO: return run_query(conn, sql, tuple(params))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'filter_orders' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: filter_orders is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: no filters returns all 12 rows\n"
            "    try:\n"
            "        all_rows = filter_orders(conn)\n"
            "        assert len(all_rows) == 12, f'expected 12, got {len(all_rows)}'\n"
            "        passed += 1; print('\\u2705 Check 2: no filter returns all 12 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: region='North' returns 4 rows\n"
            "    try:\n"
            "        north = filter_orders(conn, region='North')\n"
            "        assert len(north) == 4, f'expected 4 North rows, got {len(north)}'\n"
            "        assert all(r['region'] == 'North' for r in north)\n"
            "        passed += 1; print('\\u2705 Check 3: region=North returns 4 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: category='Electronics' returns 7 rows\n"
            "    try:\n"
            "        elec = filter_orders(conn, category='Electronics')\n"
            "        assert len(elec) == 7, f'expected 7 Electronics rows, got {len(elec)}'\n"
            "        assert all(r['category'] == 'Electronics' for r in elec)\n"
            "        passed += 1; print('\\u2705 Check 4: category=Electronics returns 7 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: combined region+category filter works\n"
            "    try:\n"
            "        east_elec = filter_orders(conn, region='East', category='Electronics')\n"
            "        assert len(east_elec) == 2, \\\n"
            "            f'expected 2 East+Electronics rows, got {len(east_elec)}'\n"
            "        assert all(r['region'] == 'East' and r['category'] == 'Electronics'\n"
            "                   for r in east_elec)\n"
            "        passed += 1; print('\\u2705 Check 5: combined region+category filter works')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + FILTER_ORDERS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — group_revenue
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + SETUP_DB_IMPL + "\n\n\n"
        + RUN_QUERY_IMPL + "\n\n\n"
        + FILTER_ORDERS_IMPL
        + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)"
    )
    return [
        md(
            "# Day 042 — Exercise 4: group_revenue\n\n"
            "**What you'll build:** `group_revenue(conn, group_col) -> list[dict]` — "
            "aggregate orders by any column using `GROUP BY`, returning total, "
            "order count, and average revenue per group.\n\n"
            "**Why it matters:** `GROUP BY` in SQL is what `df.groupby().agg()` is in "
            "pandas — but it runs inside the database, which is more efficient for "
            "large datasets. `SUM()`, `COUNT()`, `AVG()`, `MIN()`, `MAX()` are the "
            "standard SQL aggregate functions. `ORDER BY total DESC` sorts the "
            "results largest-first."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def group_revenue(conn, group_col):\n"
            '    """\n'
            "    Aggregate orders by group_col, returning per-group revenue stats.\n\n"
            "    SQL shape:\n"
            "      SELECT {group_col},\n"
            "             SUM(revenue)       AS total,\n"
            "             COUNT(*)           AS orders,\n"
            "             ROUND(AVG(revenue), 2) AS avg_revenue\n"
            "      FROM orders\n"
            "      GROUP BY {group_col}\n"
            "      ORDER BY total DESC\n\n"
            "    Returns:\n"
            "        list[dict] — one dict per group, sorted by total desc\n"
            '    """\n'
            "    # TODO: build the SQL string using an f-string for group_col\n"
            "    # TODO: return run_query(conn, sql)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'group_revenue' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: group_revenue is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a list of dicts\n"
            "    try:\n"
            "        result = group_revenue(conn, 'product')\n"
            "        assert isinstance(result, list) and len(result) > 0\n"
            "        assert isinstance(result[0], dict)\n"
            "        passed += 1; print('\\u2705 Check 2: returns list of dicts')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: group by product gives 4 groups, Gadget first\n"
            "    try:\n"
            "        assert len(result) == 4, f'expected 4 products, got {len(result)}'\n"
            "        assert result[0]['product'] == 'Gadget', \\\n"
            "            f'Gadget should be first (highest total), got {result[0][\"product\"]}'\n"
            "        assert abs(result[0]['total'] - 1800.0) < 0.01\n"
            "        passed += 1; print('\\u2705 Check 3: Gadget leads with 1800.0 total')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 4: result has expected columns\n"
            "    try:\n"
            "        expected_keys = {'product', 'total', 'orders', 'avg_revenue'}\n"
            "        actual_keys = set(result[0].keys())\n"
            "        assert actual_keys == expected_keys, \\\n"
            "            f'expected columns {expected_keys}, got {actual_keys}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: correct columns {expected_keys}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: group by region gives 4 groups\n"
            "    try:\n"
            "        by_region = group_revenue(conn, 'region')\n"
            "        assert len(by_region) == 4, f'expected 4 regions, got {len(by_region)}'\n"
            "        assert 'region' in by_region[0]\n"
            "        passed += 1; print('\\u2705 Check 5: group by region gives 4 groups')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + GROUP_REVENUE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — join_summary
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 042 — Exercise 5: join_summary\n\n"
            "**What you'll build:** `join_summary(conn) -> list[dict]` — "
            "JOIN the `orders` and `products` tables on the product name, "
            "then aggregate by region and category.\n\n"
            "**Why it matters:** JOINs are the defining feature of relational databases. "
            "The `products` table holds category and unit_price — metadata that belongs "
            "to the product, not to each order. By JOINing, you enrich each order row "
            "with product metadata without duplicating it in the orders table. "
            "`INNER JOIN ... ON o.product = p.product` matches rows where the product "
            "name appears in both tables."
        ),
        md("## Provided: All Helper Functions"),
        code(BASE_IMPORTS + "\n\n\n" + ALL_IMPLS),
        code("conn = sqlite3.connect(':memory:')\nsetup_db(conn)"),
        md("## Your Implementation"),
        code(
            "def join_summary(conn):\n"
            '    """\n'
            "    JOIN orders and products, aggregate by region and category.\n\n"
            "    SQL shape:\n"
            "      SELECT o.region, p.category,\n"
            "             SUM(o.revenue) AS total_revenue,\n"
            "             COUNT(*) AS order_count\n"
            "      FROM orders o\n"
            "      INNER JOIN products p ON o.product = p.product\n"
            "      GROUP BY o.region, p.category\n"
            "      ORDER BY total_revenue DESC\n\n"
            "    Returns:\n"
            "        list[dict] — one dict per region/category combo\n"
            '    """\n'
            "    # TODO: build the SQL string (use run_query to execute)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'join_summary' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: join_summary is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a list of dicts\n"
            "    try:\n"
            "        result = join_summary(conn)\n"
            "        assert isinstance(result, list) and len(result) > 0\n"
            "        assert isinstance(result[0], dict)\n"
            "        passed += 1; print('\\u2705 Check 2: returns list of dicts')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: has region, category, total_revenue, order_count columns\n"
            "    try:\n"
            "        expected = {'region', 'category', 'total_revenue', 'order_count'}\n"
            "        actual = set(result[0].keys())\n"
            "        assert actual == expected, f'expected {expected}, got {actual}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: correct columns {expected}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: has 7 rows (4 regions x 2 categories, minus West+Accessories)\n"
            "    try:\n"
            "        assert len(result) == 7, \\\n"
            "            f'expected 7 region/category combos, got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 4: 7 region/category combinations')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: first row has highest total_revenue (East Accessories = 1200.0)\n"
            "    try:\n"
            "        top = result[0]\n"
            "        assert abs(top['total_revenue'] - 1200.0) < 0.01, \\\n"
            "            f'expected top total_revenue = 1200.0, got {top[\"total_revenue\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: top row total_revenue = {top[\"total_revenue\"]}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + JOIN_SUMMARY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_fns = ALL_IMPLS + "\n\n\n" + JOIN_SUMMARY_IMPL
    return [
        md(
            "# Day 042 Project: Query a Database\n\n"
            "## What You're Building\n\n"
            "A set of SQL queries against the retail sales database demonstrating "
            "SELECT, WHERE, GROUP BY, ORDER BY, and INNER JOIN.\n\n"
            "**Deliverable:** All five queries run and `_run_project_checks()` passes.\n\n"
            "## Project Requirements\n\n"
            "1. Create an in-memory database with `setup_db(conn)`\n"
            "2. `q1` — all Accessories orders ordered by revenue desc\n"
            "3. `q2` — revenue summary grouped by region\n"
            "4. `q3` — top product by total revenue (use GROUP BY + ORDER BY + LIMIT 1)\n"
            "5. `q4` — JOIN summary of region × category\n"
            "6. `q5` — query into pandas with `pd.read_sql_query`"
        ),
        code(BASE_IMPORTS + "\n\n\n" + all_fns + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)\nprint('Database ready.')"),
        md("## Your Queries"),
        code(
            "# q1: all Accessories orders, most expensive first\n"
            "# TODO: q1 = filter_orders(conn, category='Accessories')\n"
            "# TODO: q1 = sorted(q1, key=lambda r: r['revenue'], reverse=True)\n"
            "# TODO: print(f'q1: {len(q1)} Accessories orders')\n"
            "\n"
            "# q2: revenue grouped by region\n"
            "# TODO: q2 = group_revenue(conn, 'region')\n"
            "# TODO: print('q2:', [(r['region'], r['total']) for r in q2])\n"
            "\n"
            "# q3: single top product by revenue (raw SQL with LIMIT)\n"
            "# TODO: q3 = run_query(conn,\n"
            "# TODO:     'SELECT product, SUM(revenue) AS total FROM orders'\n"
            "# TODO:     ' GROUP BY product ORDER BY total DESC LIMIT 1')\n"
            "# TODO: print('q3 top product:', q3[0])\n"
            "\n"
            "# q4: JOIN summary\n"
            "# TODO: q4 = join_summary(conn)\n"
            "# TODO: print(f'q4: {len(q4)} region/category combos')\n"
            "\n"
            "# q5: query into pandas\n"
            "# TODO: q5_df = pd.read_sql_query('SELECT * FROM orders', conn)\n"
            "# TODO: print(f'q5 DataFrame shape: {q5_df.shape}')"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: q1 contains only Accessories, >= 5 rows\n"
            "    try:\n"
            "        assert 'q1' in globals(), 'q1 not defined'\n"
            "        assert all(r['category'] == 'Accessories' for r in q1)\n"
            "        assert len(q1) == 5, f'expected 5 Accessories rows, got {len(q1)}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: q1 has {len(q1)} Accessories orders')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: q2 has 4 regions with correct totals\n"
            "    try:\n"
            "        assert 'q2' in globals(), 'q2 not defined'\n"
            "        assert len(q2) == 4, f'expected 4 regions, got {len(q2)}'\n"
            "        totals = {r['region']: r['total'] for r in q2}\n"
            "        assert abs(sum(totals.values()) - 4105.0) < 0.01\n"
            "        passed += 1; print(f'\\u2705 Check 2: q2 sums to 4105.0 across 4 regions')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: q3 identifies Gadget as top product\n"
            "    try:\n"
            "        assert 'q3' in globals(), 'q3 not defined'\n"
            "        assert q3[0]['product'] == 'Gadget', \\\n"
            "            f'expected Gadget, got {q3[0][\"product\"]}'\n"
            "        assert abs(q3[0]['total'] - 1800.0) < 0.01\n"
            "        passed += 1; print(f'\\u2705 Check 3: q3 top product = Gadget (1800.0)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: q4 join summary has 7 rows\n"
            "    try:\n"
            "        assert 'q4' in globals(), 'q4 not defined'\n"
            "        assert len(q4) == 7, f'expected 7 join rows, got {len(q4)}'\n"
            "        assert 'total_revenue' in q4[0]\n"
            "        passed += 1; print(f'\\u2705 Check 4: q4 join summary has 7 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: q5_df is a pandas DataFrame with 12 rows\n"
            "    try:\n"
            "        import pandas as pd\n"
            "        assert 'q5_df' in globals(), 'q5_df not defined'\n"
            "        assert isinstance(q5_df, pd.DataFrame)\n"
            "        assert q5_df.shape[0] == 12, f'expected 12 rows, got {q5_df.shape[0]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: q5_df is DataFrame {q5_df.shape}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Write a query with `HAVING SUM(revenue) > 500` to filter groups\n"
            "- Use `LEFT JOIN` instead of `INNER JOIN` and observe which rows change\n"
            "- Write a subquery: `SELECT * FROM orders WHERE revenue > (SELECT AVG(revenue) FROM orders)`\n"
            "- On Day 43 you will build `ask_sql(conn, question)` — natural language to SQL generation\n"
            "  using the same code-generation pattern from Day 41"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_fns = ALL_IMPLS + "\n\n\n" + JOIN_SUMMARY_IMPL
    return [
        md(
            "# Day 042 Solution — SQL Fundamentals\n\n"
            "setup_db, run_query, filter_orders, group_revenue, join_summary. "
            "All data and functions defined inline. Uses in-memory SQLite."
        ),
        code(BASE_IMPORTS + "\n\n\n" + all_fns),
        md("## Step 1 — Create and Populate Database"),
        code(
            "conn = sqlite3.connect(':memory:')\n"
            "setup_db(conn)\n\n"
            "n = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]\n"
            "assert n == 12\n"
            "np = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]\n"
            "assert np == 4\n"
            "print(f'orders: {n} rows, products: {np} rows')"
        ),
        md("## Step 2 — run_query (SELECT + WHERE)"),
        code(
            "all_orders = run_query(conn, 'SELECT * FROM orders')\n"
            "assert len(all_orders) == 12\n"
            "assert isinstance(all_orders[0], dict)\n"
            "print(f'All orders: {len(all_orders)} rows')\n"
            "print('Columns:', list(all_orders[0].keys()))\n\n"
            "north = run_query(conn,\n"
            "                   'SELECT * FROM orders WHERE region = ?', ('North',))\n"
            "assert len(north) == 4\n"
            "print(f'North orders: {len(north)}')"
        ),
        md("## Step 3 — filter_orders (dynamic WHERE)"),
        code(
            "# No filter\n"
            "assert len(filter_orders(conn)) == 12\n\n"
            "# Single filter\n"
            "acc = filter_orders(conn, category='Accessories')\n"
            "assert len(acc) == 5\n"
            "print(f'Accessories orders: {len(acc)}')\n\n"
            "# Combined filter\n"
            "east_elec = filter_orders(conn, region='East', category='Electronics')\n"
            "assert len(east_elec) == 2\n"
            "print(f'East+Electronics: {len(east_elec)} orders')"
        ),
        md("## Step 4 — group_revenue (GROUP BY + ORDER BY)"),
        code(
            "by_product = group_revenue(conn, 'product')\n"
            "assert len(by_product) == 4\n"
            "assert by_product[0]['product'] == 'Gadget'\n"
            "assert abs(by_product[0]['total'] - 1800.0) < 0.01\n"
            "print('By product (top 2):')\n"
            "for r in by_product[:2]:\n"
            "    print(f\"  {r['product']}: total={r['total']}, orders={r['orders']}\")\n\n"
            "by_region = group_revenue(conn, 'region')\n"
            "assert len(by_region) == 4\n"
            "assert abs(sum(r['total'] for r in by_region) - 4105.0) < 0.01\n"
            "print(f'By region: {len(by_region)} groups, sum={sum(r[\"total\"] for r in by_region)}')"
        ),
        md("## Step 5 — join_summary (INNER JOIN)"),
        code(
            "result = join_summary(conn)\n"
            "assert len(result) == 7\n"
            "assert set(result[0].keys()) == {'region', 'category', 'total_revenue', 'order_count'}\n"
            "assert abs(result[0]['total_revenue'] - 1150.0) < 0.01\n"
            "print(f'Join summary: {len(result)} region/category combinations')\n"
            "for r in result[:3]:\n"
            "    print(f\"  {r['region']} / {r['category']}: {r['total_revenue']}\")"
        ),
        md("## Step 6 — Query into pandas"),
        code(
            "q5_df = pd.read_sql_query('SELECT * FROM orders', conn)\n"
            "assert q5_df.shape == (12, 7)\n"
            "print(f'DataFrame shape: {q5_df.shape}')\n"
            "print(q5_df[['product', 'region', 'revenue']].head(4).to_string(index=False))\n\n"
            "q1 = filter_orders(conn, category='Accessories')\n"
            "q1 = sorted(q1, key=lambda r: r['revenue'], reverse=True)\n"
            "q2 = group_revenue(conn, 'region')\n"
            "q3 = run_query(conn,\n"
            "    'SELECT product, SUM(revenue) AS total FROM orders'\n"
            "    ' GROUP BY product ORDER BY total DESC LIMIT 1')\n"
            "q4 = join_summary(conn)\n\n"
            "assert len(q1) == 5\n"
            "assert len(q2) == 4\n"
            "assert q3[0]['product'] == 'Gadget'\n"
            "assert len(q4) == 7\n"
            "print('All solution checks passed.')\n\n"
            "conn.close()"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 042 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir   / "exercise_01.ipynb", ex01())
    write_nb(ex_dir   / "exercise_02.ipynb", ex02())
    write_nb(ex_dir   / "exercise_03.ipynb", ex03())
    write_nb(ex_dir   / "exercise_04.ipynb", ex04())
    write_nb(ex_dir   / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",     project_nb())
    write_nb(sol_dir  / "solution.ipynb",    solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
