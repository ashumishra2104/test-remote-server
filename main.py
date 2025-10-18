from fastmcp import FastMCP
import os
import sqlite3
from pathlib import Path

# Use absolute paths and ensure directory exists
BASE_DIR = Path(__file__).parent.absolute()
DB_PATH = BASE_DIR / "expenses.db"
CATEGORIES_PATH = BASE_DIR / "categories.json"

mcp = FastMCP("ExpenseTracker")

def init_db():
    """Initialize database with proper error handling"""
    try:
        # Ensure directory exists
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        
        cursor = conn.cursor()
        
        # Create expenses table
        cursor.execute("""
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
        cursor.execute("""
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

        # Migration: Add person column if not present
        try:
            cursor.execute("ALTER TABLE expenses ADD COLUMN person TEXT DEFAULT 'ashu'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE credits ADD COLUMN person TEXT DEFAULT 'ashu'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

init_db()

@mcp.tool()
def add_expense(date: str, amount: float, category: str, person: str, subcategory: str = "", note: str = ""):
    """Add a new expense entry to the database."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, person) VALUES (?,?,?,?,?,?)",
            (date, float(amount), category, subcategory, note, person)
        )
        
        expense_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "ok", "id": expense_id, "message": f"Expense added successfully with ID {expense_id}"}
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to add expense: {str(e)}"}

@mcp.tool()
def add_credit(date: str, amount: float, source: str, person: str, subcategory: str = "", note: str = ""):
    """Add a new credit/income entry to the database."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO credits(date, amount, source, subcategory, note, person) VALUES (?,?,?,?,?,?)",
            (date, float(amount), source, subcategory, note, person)
        )
        
        credit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "ok", "id": credit_id, "message": f"Credit added successfully with ID {credit_id}"}
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to add credit: {str(e)}"}
    
@mcp.tool()
def list_expenses(start_date: str, end_date: str, person: str = None):
    """List expense entries within an inclusive date range. Optionally filter by person."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to list expenses: {str(e)}"}

@mcp.tool()
def list_credits(start_date: str, end_date: str, person: str = None):
    """List credit/income entries within an inclusive date range. Optionally filter by person."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to list credits: {str(e)}"}

@mcp.tool()
def summarize(start_date: str, end_date: str, category: str = None, person: str = None):
    """Summarize expenses by category within an inclusive date range. Optionally filter by category and/or person."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to summarize expenses: {str(e)}"}

@mcp.tool()
def summarize_credits(start_date: str, end_date: str, source: str = None, person: str = None):
    """Summarize credits/income by source within an inclusive date range. Optionally filter by source and/or person."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to summarize credits: {str(e)}"}

@mcp.tool()
def get_balance(start_date: str, end_date: str, person: str = None):
    """Calculate net balance (total credits - total expenses) within a date range. Optionally filter by person."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        cursor = conn.cursor()
        
        # Get total expenses
        expense_query = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?"
        expense_params = [start_date, end_date]

        if person:
            expense_query += " AND person = ?"
            expense_params.append(person)

        expense_result = cursor.execute(expense_query, expense_params).fetchone()
        total_expenses = expense_result[0]

        # Get total credits
        credit_query = "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?"
        credit_params = [start_date, end_date]

        if person:
            credit_query += " AND person = ?"
            credit_params.append(person)

        credit_result = cursor.execute(credit_query, credit_params).fetchone()
        total_credits = credit_result[0]

        conn.close()

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
def delete_expense(id: int):
    """Delete an expense entry by ID."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        cursor = conn.cursor()
        
        # Check if expense exists
        result = cursor.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()
        if not result:
            conn.close()
            return {"status": "error", "message": f"Expense with id {id} not found"}

        # Delete the expense
        cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        
        return {"status": "ok", "message": f"Expense with id {id} deleted successfully"}
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete expense: {str(e)}"}

@mcp.tool()
def delete_credit(id: int):
    """Delete a credit/income entry by ID."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        cursor = conn.cursor()
        
        # Check if credit exists
        result = cursor.execute("SELECT * FROM credits WHERE id = ?", (id,)).fetchone()
        if not result:
            conn.close()
            return {"status": "error", "message": f"Credit with id {id} not found"}

        # Delete the credit
        cursor.execute("DELETE FROM credits WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        
        return {"status": "ok", "message": f"Credit with id {id} deleted successfully"}
    
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete credit: {str(e)}"}

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Read categories from JSON file"""
    try:
        if not CATEGORIES_PATH.exists():
            return '{"categories": []}'
        
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f'{{"error": "Failed to read categories: {str(e)}"}}'


# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
