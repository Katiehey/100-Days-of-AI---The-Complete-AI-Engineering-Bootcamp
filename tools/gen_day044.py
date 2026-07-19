#!/usr/bin/env python3
"""Generate all Day 044 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_044"

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
from sqlalchemy import create_engine, String, Float, Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.pool import StaticPool"""

MODEL_CODE = """\
class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = 'items'
    id:       Mapped[int]   = mapped_column(primary_key=True)
    name:     Mapped[str]   = mapped_column(String(100))
    category: Mapped[str]   = mapped_column(String(50))
    price:    Mapped[float] = mapped_column()
    quantity: Mapped[int]   = mapped_column(default=0)

    def __repr__(self):
        return f'Item(id={self.id}, name={self.name!r}, price={self.price})'"""

SETUP_ENGINE_IMPL = """\
def setup_engine(url='sqlite:///:memory:'):
    engine = create_engine(
        url,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine"""

ADD_ITEM_IMPL = """\
def add_item(session, name, category, price, quantity=0):
    item = Item(name=name, category=category, price=price, quantity=quantity)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item"""

GET_ITEMS_IMPL = """\
def get_items(session, category=None):
    stmt = select(Item)
    if category is not None:
        stmt = stmt.where(Item.category == category)
    return list(session.execute(stmt).scalars().all())"""

UPDATE_PRICE_IMPL = """\
def update_price(session, item_id, new_price):
    item = session.get(Item, item_id)
    if item is None:
        return None
    item.price = new_price
    session.commit()
    session.refresh(item)
    return item"""

DELETE_ITEM_IMPL = """\
def delete_item(session, item_id):
    item = session.get(Item, item_id)
    if item is None:
        return False
    session.delete(item)
    session.commit()
    return True"""

ALL_IMPLS = "\n\n\n".join([
    SETUP_ENGINE_IMPL,
    ADD_ITEM_IMPL,
    GET_ITEMS_IMPL,
    UPDATE_PRICE_IMPL,
    DELETE_ITEM_IMPL,
])

# ---------------------------------------------------------------------------
# Exercise 01 — setup_engine
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 044 — Exercise 1: setup_engine\n\n"
            "**What you'll build:** `setup_engine(url='sqlite:///:memory:') -> Engine` — "
            "create a SQLAlchemy engine, configure it for in-memory SQLite, "
            "and call `Base.metadata.create_all(engine)` to create all ORM tables.\n\n"
            "**Why it matters:** The engine is SQLAlchemy's entry point to the database. "
            "It holds the connection pool and knows which database to talk to via a URL. "
            "`create_all` inspects every class that inherits from `Base` and creates the "
            "corresponding tables — replacing the manual `CREATE TABLE IF NOT EXISTS` DDL "
            "from Day 42 with a single call."
        ),
        code(BASE_IMPORTS + "\n\n\n" + MODEL_CODE),
        md("## Your Implementation"),
        code(
            "def setup_engine(url='sqlite:///:memory:'):\n"
            '    """\n'
            "    Create a SQLAlchemy engine and create all ORM-mapped tables.\n\n"
            "    Use StaticPool and check_same_thread=False so that the in-memory\n"
            "    SQLite database is shared across all connections from this engine.\n\n"
            "    Returns:\n"
            "        Engine — the connected engine with tables created\n"
            '    """\n'
            "    # TODO: engine = create_engine(\n"
            "    # TODO:     url,\n"
            "    # TODO:     connect_args={'check_same_thread': False},\n"
            "    # TODO:     poolclass=StaticPool,\n"
            "    # TODO: )\n"
            "    # TODO: Base.metadata.create_all(engine)\n"
            "    # TODO: return engine\n"
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
            "        assert 'setup_engine' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: setup_engine is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns an Engine\n"
            "    try:\n"
            "        from sqlalchemy.engine import Engine\n"
            "        engine = setup_engine()\n"
            "        assert isinstance(engine, Engine), \\\n"
            "            f'expected Engine, got {type(engine).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns an Engine')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: items table was created\n"
            "    try:\n"
            "        from sqlalchemy import inspect as sa_inspect\n"
            "        inspector = sa_inspect(engine)\n"
            "        tables = inspector.get_table_names()\n"
            "        assert 'items' in tables, \\\n"
            "            f'items table not found; got {tables}'\n"
            "        passed += 1; print('\\u2705 Check 3: items table created')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: can open a Session\n"
            "    try:\n"
            "        with Session(engine) as session:\n"
            "            assert session is not None\n"
            "        passed += 1; print('\\u2705 Check 4: Session opens without error')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: items table has correct columns\n"
            "    try:\n"
            "        from sqlalchemy import inspect as sa_inspect\n"
            "        cols = {c['name'] for c in sa_inspect(engine).get_columns('items')}\n"
            "        required = {'id', 'name', 'category', 'price', 'quantity'}\n"
            "        assert required <= cols, \\\n"
            "            f'missing columns: {required - cols}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: items has columns {required}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + SETUP_ENGINE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — add_item
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL
        + "\n\n\nengine = setup_engine()\nsession = Session(engine)"
    )
    return [
        md(
            "# Day 044 — Exercise 2: add_item\n\n"
            "**What you'll build:** `add_item(session, name, category, price, quantity=0) -> Item` — "
            "create an Item ORM object, add it to the session, commit, and return the "
            "persisted instance with its `id` populated.\n\n"
            "**Why it matters:** `session.add(obj)` stages the object for insertion. "
            "`session.commit()` flushes the change to the database and ends the transaction. "
            "`session.refresh(obj)` reloads the object from the database — essential for "
            "reading back auto-generated values like the primary key `id`."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def add_item(session, name, category, price, quantity=0):\n"
            '    """\n'
            "    Create and persist a new Item.\n\n"
            "    Steps:\n"
            "    1. item = Item(name=name, category=category, price=price, quantity=quantity)\n"
            "    2. session.add(item)\n"
            "    3. session.commit()\n"
            "    4. session.refresh(item)   # reload from DB to populate id\n"
            "    5. return item\n"
            '    """\n'
            "    # TODO: item = Item(name=name, category=category, price=price, quantity=quantity)\n"
            "    # TODO: session.add(item)\n"
            "    # TODO: session.commit()\n"
            "    # TODO: session.refresh(item)\n"
            "    # TODO: return item\n"
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
            "        assert 'add_item' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: add_item is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns an Item\n"
            "    try:\n"
            "        item = add_item(session, 'Laptop', 'Electronics', 999.99, 5)\n"
            "        assert isinstance(item, Item), \\\n"
            "            f'expected Item, got {type(item).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: returns an Item ({item})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: id is set (auto-assigned by DB)\n"
            "    try:\n"
            "        assert item.id is not None, 'id should be set after commit'\n"
            "        assert isinstance(item.id, int)\n"
            "        passed += 1; print(f'\\u2705 Check 3: id set to {item.id}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: attributes are correct\n"
            "    try:\n"
            "        assert item.name == 'Laptop'\n"
            "        assert item.category == 'Electronics'\n"
            "        assert abs(item.price - 999.99) < 0.01\n"
            "        assert item.quantity == 5\n"
            "        passed += 1; print('\\u2705 Check 4: all attributes correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: item is persisted (visible via fresh query)\n"
            "    try:\n"
            "        from sqlalchemy import select\n"
            "        result = session.execute(select(Item).where(Item.id == item.id)).scalar_one()\n"
            "        assert result.name == 'Laptop'\n"
            "        passed += 1; print('\\u2705 Check 5: item persisted and queryable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + ADD_ITEM_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — get_items
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + ADD_ITEM_IMPL
        + "\n\n\n"
        "engine = setup_engine()\nsession = Session(engine)\n\n"
        "# Seed data\n"
        "add_item(session, 'Laptop',    'Electronics', 999.99, 5)\n"
        "add_item(session, 'Headphones','Electronics', 149.99, 12)\n"
        "add_item(session, 'Desk Chair','Furniture',   349.00, 3)\n"
        "add_item(session, 'Bookcase',  'Furniture',   199.00, 8)\n"
        "add_item(session, 'Pen Set',   'Stationery',   12.99, 50)"
    )
    return [
        md(
            "# Day 044 — Exercise 3: get_items\n\n"
            "**What you'll build:** `get_items(session, category=None) -> list[Item]` — "
            "query all items, or filter by category when provided.\n\n"
            "**Why it matters:** `select(Item)` is the SQLAlchemy 2.x ORM query. "
            "`.where(Item.category == category)` appends a WHERE clause using Python "
            "attribute access — no SQL string needed. "
            "`session.execute(stmt).scalars().all()` converts the result set into "
            "a list of ORM objects, each with full attribute access."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def get_items(session, category=None):\n"
            '    """\n'
            "    Return all items, optionally filtered by category.\n\n"
            "    Use select(Item) as the base statement.\n"
            "    Append .where(Item.category == category) if category is not None.\n"
            "    Execute with session.execute(stmt).scalars().all().\n"
            "    Return a list.\n"
            '    """\n'
            "    # TODO: stmt = select(Item)\n"
            "    # TODO: if category is not None:\n"
            "    # TODO:     stmt = stmt.where(Item.category == category)\n"
            "    # TODO: return list(session.execute(stmt).scalars().all())\n"
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
            "        assert 'get_items' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: get_items is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = get_items(session)\n"
            "        assert isinstance(result, list), \\\n"
            "            f'expected list, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: no filter returns all 5 seeded items\n"
            "    try:\n"
            "        assert len(result) == 5, \\\n"
            "            f'expected 5 items, got {len(result)}'\n"
            "        assert all(isinstance(i, Item) for i in result)\n"
            "        passed += 1; print('\\u2705 Check 3: no filter returns all 5 items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: category filter returns only matching items\n"
            "    try:\n"
            "        elec = get_items(session, category='Electronics')\n"
            "        assert len(elec) == 2, \\\n"
            "            f'expected 2 Electronics, got {len(elec)}'\n"
            "        assert all(i.category == 'Electronics' for i in elec)\n"
            "        passed += 1; print('\\u2705 Check 4: category=Electronics returns 2 items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: non-existent category returns empty list\n"
            "    try:\n"
            "        none_found = get_items(session, category='NonExistent')\n"
            "        assert none_found == [], \\\n"
            "            f'expected [], got {none_found}'\n"
            "        passed += 1; print('\\u2705 Check 5: non-existent category returns []')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + GET_ITEMS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — update_price
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + ADD_ITEM_IMPL + "\n\n\n"
        + GET_ITEMS_IMPL
        + "\n\n\n"
        "engine  = setup_engine()\nsession = Session(engine)\n\n"
        "laptop  = add_item(session, 'Laptop', 'Electronics', 999.99, 5)\n"
        "chair   = add_item(session, 'Desk Chair', 'Furniture', 349.00, 3)"
    )
    return [
        md(
            "# Day 044 — Exercise 4: update_price\n\n"
            "**What you'll build:** `update_price(session, item_id, new_price) -> Item | None` — "
            "fetch an item by primary key, update its price, commit, and return "
            "the updated item. Return `None` if the id does not exist.\n\n"
            "**Why it matters:** `session.get(Model, pk)` is the efficient ORM method "
            "for lookup by primary key — it checks the session's identity map first "
            "(no SQL if already loaded), then queries the DB. Mutating the attribute "
            "directly (`item.price = new_price`) marks the object as 'dirty'; the next "
            "`commit()` generates the UPDATE statement automatically."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def update_price(session, item_id, new_price):\n"
            '    """\n'
            "    Update the price of an item by id. Return None if not found.\n\n"
            "    Steps:\n"
            "    1. item = session.get(Item, item_id)  — None if not found\n"
            "    2. if item is None: return None\n"
            "    3. item.price = new_price\n"
            "    4. session.commit()\n"
            "    5. session.refresh(item)\n"
            "    6. return item\n"
            '    """\n'
            "    # TODO: item = session.get(Item, item_id)\n"
            "    # TODO: if item is None: return None\n"
            "    # TODO: item.price = new_price\n"
            "    # TODO: session.commit()\n"
            "    # TODO: session.refresh(item)\n"
            "    # TODO: return item\n"
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
            "        assert 'update_price' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: update_price is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns the updated Item\n"
            "    try:\n"
            "        updated = update_price(session, laptop.id, 899.99)\n"
            "        assert isinstance(updated, Item), \\\n"
            "            f'expected Item, got {type(updated).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns an Item')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: price was updated\n"
            "    try:\n"
            "        assert abs(updated.price - 899.99) < 0.01, \\\n"
            "            f'expected 899.99, got {updated.price}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: price updated to {updated.price}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: change is persisted (re-fetch from DB)\n"
            "    try:\n"
            "        re_fetched = session.get(Item, laptop.id)\n"
            "        assert abs(re_fetched.price - 899.99) < 0.01, \\\n"
            "            f'persisted price mismatch: {re_fetched.price}'\n"
            "        passed += 1; print('\\u2705 Check 4: change persisted in DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: non-existent id returns None\n"
            "    try:\n"
            "        result = update_price(session, 99999, 1.0)\n"
            "        assert result is None, f'expected None for missing id, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 5: missing id returns None')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + UPDATE_PRICE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — delete_item
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + ADD_ITEM_IMPL + "\n\n\n"
        + GET_ITEMS_IMPL + "\n\n\n"
        + UPDATE_PRICE_IMPL
        + "\n\n\n"
        "engine  = setup_engine()\nsession = Session(engine)\n\n"
        "item_a = add_item(session, 'Widget',  'Parts',  5.99, 100)\n"
        "item_b = add_item(session, 'Gadget',  'Parts', 19.99,  50)\n"
        "item_c = add_item(session, 'Doohickey','Parts', 3.49, 200)"
    )
    return [
        md(
            "# Day 044 — Exercise 5: delete_item\n\n"
            "**What you'll build:** `delete_item(session, item_id) -> bool` — "
            "fetch an item by id, delete it, commit, and return `True`. "
            "Return `False` if the id does not exist.\n\n"
            "**Why it matters:** `session.delete(obj)` marks the object for deletion. "
            "The DELETE SQL is generated on the next `commit()`. This is the ORM way "
            "to delete — you operate on Python objects, not SQL strings. "
            "The bool return lets callers check whether a deletion actually happened "
            "without needing to inspect the database again."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def delete_item(session, item_id):\n"
            '    """\n'
            "    Delete an item by id. Return True if deleted, False if not found.\n\n"
            "    Steps:\n"
            "    1. item = session.get(Item, item_id)\n"
            "    2. if item is None: return False\n"
            "    3. session.delete(item)\n"
            "    4. session.commit()\n"
            "    5. return True\n"
            '    """\n'
            "    # TODO: item = session.get(Item, item_id)\n"
            "    # TODO: if item is None: return False\n"
            "    # TODO: session.delete(item)\n"
            "    # TODO: session.commit()\n"
            "    # TODO: return True\n"
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
            "        assert 'delete_item' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: delete_item is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns True for existing item\n"
            "    try:\n"
            "        result = delete_item(session, item_a.id)\n"
            "        assert result is True, f'expected True, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns True for existing item')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: item no longer in DB\n"
            "    try:\n"
            "        gone = session.get(Item, item_a.id)\n"
            "        assert gone is None, \\\n"
            "            f'item should be deleted but found: {gone}'\n"
            "        passed += 1; print('\\u2705 Check 3: item no longer in DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: only 2 items remain\n"
            "    try:\n"
            "        remaining = get_items(session)\n"
            "        assert len(remaining) == 2, \\\n"
            "            f'expected 2 remaining, got {len(remaining)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(remaining)} items remain')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: returns False for non-existent id\n"
            "    try:\n"
            "        result2 = delete_item(session, 99999)\n"
            "        assert result2 is False, \\\n"
            "            f'expected False for missing id, got {result2}'\n"
            "        passed += 1; print('\\u2705 Check 5: returns False for missing id')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + DELETE_ITEM_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 044 Project: Inventory Management App\n\n"
            "## What You're Building\n\n"
            "A data-backed inventory manager using SQLAlchemy ORM with SQLite. "
            "Add items, search by category, update prices, delete items — "
            "all through Python objects, with no raw SQL.\n\n"
            "**Deliverable:** All five CRUD functions wired up, 5+ items managed, "
            "and `_run_project_checks()` passes.\n\n"
            "## Project Requirements\n\n"
            "1. Call `setup_engine()` and open a `Session`\n"
            "2. Add at least 5 items across at least 2 categories\n"
            "3. Use `get_items(category=...)` to filter by at least one category\n"
            "4. Use `update_price` to change at least one price\n"
            "5. Use `delete_item` to remove at least one item\n"
            "6. Store all added items in a list called `inventory`"
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + MODEL_CODE + "\n\n\n"
            + ALL_IMPLS
            + "\n\n\nengine  = setup_engine()\nsession = Session(engine)\nprint('Inventory DB ready.')"
        ),
        md("## Step 1 — Stock the Inventory"),
        code(
            "inventory = []\n\n"
            "# TODO: add at least 5 items in at least 2 categories\n"
            "# Example:\n"
            "# inventory.append(add_item(session, 'Laptop',    'Electronics', 999.99, 5))\n"
            "# inventory.append(add_item(session, 'Headphones','Electronics', 149.99, 12))\n"
            "# inventory.append(add_item(session, 'Desk Chair','Furniture',   349.00, 3))\n"
            "# inventory.append(add_item(session, 'Bookcase',  'Furniture',   199.00, 8))\n"
            "# inventory.append(add_item(session, 'Pen Set',   'Stationery',   12.99, 50))\n"
            "print(f'Stocked {len(inventory)} items')"
        ),
        md("## Step 2 — Browse by Category"),
        code(
            "# TODO: filter by one of your categories\n"
            "# category_items = get_items(session, category='Electronics')\n"
            "# print(f'{len(category_items)} Electronics items:')\n"
            "# for item in category_items:\n"
            "#     print(f'  {item}')"
        ),
        md("## Step 3 — Update a Price"),
        code(
            "# TODO: update the price of one item\n"
            "# updated = update_price(session, inventory[0].id, 849.99)\n"
            "# print(f'Updated: {updated}')"
        ),
        md("## Step 4 — Remove an Item"),
        code(
            "# TODO: delete one item\n"
            "# removed = delete_item(session, inventory[-1].id)\n"
            "# print(f'Deleted: {removed}')\n"
            "# print(f'Remaining: {len(get_items(session))} items')"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: inventory list has >= 5 items\n"
            "    try:\n"
            "        assert 'inventory' in globals(), 'inventory not defined'\n"
            "        assert len(inventory) >= 5, \\\n"
            "            f'expected >= 5 items in inventory, got {len(inventory)}'\n"
            "        assert all(isinstance(i, Item) for i in inventory)\n"
            "        passed += 1; print(f'\\u2705 Check 1: {len(inventory)} items stocked')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: get_items returns all persisted items (at least 4 — may have deleted some)\n"
            "    try:\n"
            "        all_items = get_items(session)\n"
            "        assert len(all_items) >= 4, \\\n"
            "            f'expected >= 4 items in DB, got {len(all_items)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(all_items)} items in DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: category filtering works\n"
            "    try:\n"
            "        categories = list({i.category for i in get_items(session)})\n"
            "        assert len(categories) >= 2, \\\n"
            "            f'expected >= 2 categories, got {categories}'\n"
            "        sample_cat = categories[0]\n"
            "        filtered = get_items(session, category=sample_cat)\n"
            "        assert all(i.category == sample_cat for i in filtered)\n"
            "        passed += 1; print(f'\\u2705 Check 3: category filter works ({sample_cat}: {len(filtered)} items)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: update_price works\n"
            "    try:\n"
            "        first = get_items(session)[0]\n"
            "        new_p = round(first.price * 0.9, 2)\n"
            "        u = update_price(session, first.id, new_p)\n"
            "        assert u is not None\n"
            "        assert abs(u.price - new_p) < 0.01\n"
            "        passed += 1; print(f'\\u2705 Check 4: update_price works (id={first.id} → {new_p})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: delete_item works\n"
            "    try:\n"
            "        temp = add_item(session, '_tmp_delete_check', 'Test', 0.01, 1)\n"
            "        assert delete_item(session, temp.id) is True\n"
            "        assert session.get(Item, temp.id) is None\n"
            "        passed += 1; print('\\u2705 Check 5: delete_item removes item from DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Add a `search_items(session, keyword)` function using "
            "`Item.name.ilike(f'%{keyword}%')` (SQLAlchemy case-insensitive LIKE)\n"
            "- Switch from `sqlite:///:memory:` to `sqlite:///inventory.db` "
            "and verify that data persists between sessions\n"
            "- Add a second model (`Category`) and a ForeignKey relationship, "
            "then use `relationship()` to navigate between models\n"
            "- On Day 45 you will build an ETL pipeline that writes results "
            "into a SQLAlchemy-backed database"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    return [
        md(
            "# Day 044 Solution — Databases in Python\n\n"
            "setup_engine, add_item, get_items, update_price, delete_item. "
            "All in-memory SQLite via SQLAlchemy 2.x ORM. Self-contained."
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + MODEL_CODE + "\n\n\n"
            + ALL_IMPLS
        ),
        md("## Step 1 — Engine and Session"),
        code(
            "engine  = setup_engine()\nsession = Session(engine)\n\n"
            "from sqlalchemy import inspect as sa_inspect\n"
            "tables = sa_inspect(engine).get_table_names()\n"
            "assert 'items' in tables\n"
            "print(f'Tables: {tables}')"
        ),
        md("## Step 2 — add_item"),
        code(
            "laptop  = add_item(session, 'Laptop',     'Electronics', 999.99, 5)\n"
            "phones  = add_item(session, 'Headphones', 'Electronics', 149.99, 12)\n"
            "chair   = add_item(session, 'Desk Chair', 'Furniture',   349.00, 3)\n"
            "book    = add_item(session, 'Bookcase',   'Furniture',   199.00, 8)\n"
            "pens    = add_item(session, 'Pen Set',    'Stationery',   12.99, 50)\n\n"
            "assert laptop.id is not None\n"
            "assert laptop.name == 'Laptop'\n"
            "assert abs(laptop.price - 999.99) < 0.01\n"
            "print(f'Added: {laptop}')"
        ),
        md("## Step 3 — get_items"),
        code(
            "all_items = get_items(session)\n"
            "assert len(all_items) == 5\n"
            "assert all(isinstance(i, Item) for i in all_items)\n"
            "print(f'All items: {len(all_items)}')\n\n"
            "elec = get_items(session, category='Electronics')\n"
            "assert len(elec) == 2\n"
            "assert all(i.category == 'Electronics' for i in elec)\n"
            "print(f'Electronics: {[i.name for i in elec]}')\n\n"
            "empty = get_items(session, category='NonExistent')\n"
            "assert empty == []\n"
            "print(f'NonExistent: {empty}')"
        ),
        md("## Step 4 — update_price"),
        code(
            "updated = update_price(session, laptop.id, 849.99)\n"
            "assert updated is not None\n"
            "assert abs(updated.price - 849.99) < 0.01\n"
            "print(f'Updated: {updated}')\n\n"
            "not_found = update_price(session, 99999, 1.0)\n"
            "assert not_found is None\n"
            "print(f'Missing id: {not_found}')"
        ),
        md("## Step 5 — delete_item"),
        code(
            "before = len(get_items(session))\n"
            "deleted = delete_item(session, pens.id)\n"
            "assert deleted is True\n"
            "assert session.get(Item, pens.id) is None\n"
            "after = len(get_items(session))\n"
            "assert after == before - 1\n"
            "print(f'Deleted pens. Before: {before}, after: {after}')\n\n"
            "not_deleted = delete_item(session, 99999)\n"
            "assert not_deleted is False\n"
            "print(f'Missing id: {not_deleted}')\n\n"
            "print('\\nAll solution checks passed.')\n"
            "session.close()"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 044 notebooks...")
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
