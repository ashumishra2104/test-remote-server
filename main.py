from fastmcp import FastMCP
import os
import aiosqlite
import tempfile
from pathlib import Path
import json
from contextlib import asynccontextmanager
import aiofiles

# Use temp directory for cloud deployment (writable)
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

async def init_db():
    """Initialize database asynchronously on startup"""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")

            # Create expenses table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    person TEXT DEFAULT 'ashu'
                )
            """)

            # Create credits table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS credits(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    source TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    person TEXT DEFAULT 'ashu'
                )
            """)

            # Test write access
            await conn.execute("INSERT OR IGNORE INTO expenses(date, amount, category, person) VALUES ('2000-01-01', 0, 'test', 'system')")
            await conn.execute("DELETE FROM expenses WHERE category = 'test'")

            await conn.commit()
            print("Database initialized successfully with write access")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastMCP"""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed
    print("Shutting down ExpenseTracker")

mcp = FastMCP("ExpenseTracker", lifespan=lifespan)

@mcp.tool()
async def add_expense(date: str, amount: float, category: str, person: str, subcategory: str = "", note: str = ""):
    """Add a new expense entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            cursor = await conn.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note, person) VALUES (?,?,?,?,?,?)",
                (date, float(amount), category, subcategory, note, person)
            )
            expense_id = cursor.lastrowid
            await conn.commit()
            return {"status": "ok", "id": expense_id, "message": f"Expense added successfully with ID {expense_id}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to add expense: {str(e)}"}

@mcp.tool()
async def add_credit(date: str, amount: float, source: str, person: str, subcategory: str = "", note: str = ""):
    """Add a new credit/income entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            cursor = await conn.execute(
                "INSERT INTO credits(date, amount, source, subcategory, note, person) VALUES (?,?,?,?,?,?)",
                (date, float(amount), source, subcategory, note, person)
            )
            credit_id = cursor.lastrowid
            await conn.commit()
            return {"status": "ok", "id": credit_id, "message": f"Credit added successfully with ID {credit_id}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to add credit: {str(e)}"}
    
@mcp.tool()
async def list_expenses(start_date: str, end_date: str, person: str = None):
    """List expense entries within an inclusive date range. Optionally filter by person."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            
            query = """
                SELECT id, date, amount, category, subcategory, note, person
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if person:
                query += " AND person = ?"
                params.append(person)

            query += " ORDER BY date ASC, id ASC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Failed to list expenses: {str(e)}"}

@mcp.tool()
async def list_credits(start_date: str, end_date: str, person: str = None):
    """List credit/income entries within an inclusive date range. Optionally filter by person."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            
            query = """
                SELECT id, date, amount, source, subcategory, note, person
                FROM credits
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if person:
                query += " AND person = ?"
                params.append(person)

            query += " ORDER BY date ASC, id ASC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Failed to list credits: {str(e)}"}

@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str = None, person: str = None):
    """Summarize expenses by category within an inclusive date range. Optionally filter by category and/or person."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            
            query = """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            if person:
                query += " AND person = ?"
                params.append(person)

            query += " GROUP BY category ORDER BY category ASC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Failed to summarize expenses: {str(e)}"}

@mcp.tool()
async def summarize_credits(start_date: str, end_date: str, source: str = None, person: str = None):
    """Summarize credits/income by source within an inclusive date range. Optionally filter by source and/or person."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            
            query = """
                SELECT source, SUM(amount) AS total_amount
                FROM credits
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if source:
                query += " AND source = ?"
                params.append(source)

            if person:
                query += " AND person = ?"
                params.append(person)

            query += " GROUP BY source ORDER BY source ASC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Failed to summarize credits: {str(e)}"}

@mcp.tool()
async def get_balance(start_date: str, end_date: str, person: str = None):
    """Calculate net balance (total credits - total expenses) within a date range. Optionally filter by person."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            # Get total expenses
            expense_query = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?"
            expense_params = [start_date, end_date]

            if person:
                expense_query += " AND person = ?"
                expense_params.append(person)

            cursor = await conn.execute(expense_query, expense_params)
            expense_result = await cursor.fetchone()
            total_expenses = expense_result[0]

            # Get total credits
            credit_query = "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?"
            credit_params = [start_date, end_date]

            if person:
                credit_query += " AND person = ?"
                credit_params.append(person)

            cursor = await conn.execute(credit_query, credit_params)
            credit_result = await cursor.fetchone()
            total_credits = credit_result[0]

            net_balance = total_credits - total_expenses

            result = {
                "start_date": start_date,
                "end_date": end_date,
                "total_credits": total_credits,
                "total_expenses": total_expenses,
                "net_balance": net_balance
            }

            if person:
                result["person"] = person

            return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to calculate balance: {str(e)}"}

@mcp.tool()
async def delete_expense(id: int):
    """Delete an expense entry by ID."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            # Check if expense exists
            cursor = await conn.execute("SELECT * FROM expenses WHERE id = ?", (id,))
            result = await cursor.fetchone()
            
            if not result:
                return {"status": "error", "message": f"Expense with id {id} not found"}

            # Delete the expense
            await conn.execute("DELETE FROM expenses WHERE id = ?", (id,))
            await conn.commit()
            return {"status": "ok", "message": f"Expense with id {id} deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete expense: {str(e)}"}

@mcp.tool()
async def delete_credit(id: int):
    """Delete a credit/income entry by ID."""
    try:
        async with aiosqlite.connect(DB_PATH, timeout=10.0) as conn:
            # Check if credit exists
            cursor = await conn.execute("SELECT * FROM credits WHERE id = ?", (id,))
            result = await cursor.fetchone()
            
            if not result:
                return {"status": "error", "message": f"Credit with id {id} not found"}

            # Delete the credit
            await conn.execute("DELETE FROM credits WHERE id = ?", (id,))
            await conn.commit()
            return {"status": "ok", "message": f"Credit with id {id} deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete credit: {str(e)}"}

@mcp.resource("expense://categories", mime_type="application/json")
async def categories():
    """Read categories from JSON file asynchronously"""
    try:
        # Default categories
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }

        # Try to read from file asynchronously, fallback to defaults
        try:
            async with aiofiles.open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                content = await f.read()
                return content
        except FileNotFoundError:
            return json.dumps(default_categories, indent=2)

    except Exception as e:
        return f'{{"error": "Failed to read categories: {str(e)}"}}'


# For cloud deployment - run as HTTP server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.get_asgi_app(), host="0.0.0.0", port=8080)