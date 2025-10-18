from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
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

        # New table for credits/income
        c.execute("""
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

        # Migration: Add person column to existing tables if not present
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN person TEXT DEFAULT 'ashu'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            c.execute("ALTER TABLE credits ADD COLUMN person TEXT DEFAULT 'ashu'")
        except sqlite3.OperationalError:
            pass  # Column already exists

init_db()

@mcp.tool()
def add_expense(date, amount, category, person, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, person) VALUES (?,?,?,?,?,?)",
            (date, amount, category, subcategory, note, person)
        )
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def add_credit(date, amount, source, person, subcategory="", note=""):
    '''Add a new credit/income entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO credits(date, amount, source, subcategory, note, person) VALUES (?,?,?,?,?,?)",
            (date, amount, source, subcategory, note, person)
        )
        return {"status": "ok", "id": cur.lastrowid}
    
@mcp.tool()
def list_expenses(start_date, end_date, person=None):
    '''List expense entries within an inclusive date range. Optionally filter by person.'''
    with sqlite3.connect(DB_PATH) as c:
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

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def list_credits(start_date, end_date, person=None):
    '''List credit/income entries within an inclusive date range. Optionally filter by person.'''
    with sqlite3.connect(DB_PATH) as c:
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

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(start_date, end_date, category=None, person=None):
    '''Summarize expenses by category within an inclusive date range. Optionally filter by category and/or person.'''
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        if person:
            query += " AND person = ?"
            params.append(person)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize_credits(start_date, end_date, source=None, person=None):
    '''Summarize credits/income by source within an inclusive date range. Optionally filter by source and/or person.'''
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT source, SUM(amount) AS total_amount
            FROM credits
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if source:
            query += " AND source = ?"
            params.append(source)

        if person:
            query += " AND person = ?"
            params.append(person)

        query += " GROUP BY source ORDER BY source ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def get_balance(start_date, end_date, person=None):
    '''Calculate net balance (total credits - total expenses) within a date range. Optionally filter by person.'''
    with sqlite3.connect(DB_PATH) as c:
        # Get total expenses
        expense_query = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?"
        expense_params = [start_date, end_date]

        if person:
            expense_query += " AND person = ?"
            expense_params.append(person)

        expense_result = c.execute(expense_query, expense_params).fetchone()
        total_expenses = expense_result[0]

        # Get total credits
        credit_query = "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?"
        credit_params = [start_date, end_date]

        if person:
            credit_query += " AND person = ?"
            credit_params.append(person)

        credit_result = c.execute(credit_query, credit_params).fetchone()
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

@mcp.tool()
def delete_expense(id):
    '''Delete an expense entry by ID.'''
    with sqlite3.connect(DB_PATH) as c:
        # Check if expense exists
        result = c.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()
        if not result:
            return {"status": "error", "message": f"Expense with id {id} not found"}

        # Delete the expense
        c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        return {"status": "ok", "message": f"Expense with id {id} deleted successfully"}

@mcp.tool()
def delete_credit(id):
    '''Delete a credit/income entry by ID.'''
    with sqlite3.connect(DB_PATH) as c:
        # Check if credit exists
        result = c.execute("SELECT * FROM credits WHERE id = ?", (id,)).fetchone()
        if not result:
            return {"status": "error", "message": f"Credit with id {id} not found"}

        # Delete the credit
        c.execute("DELETE FROM credits WHERE id = ?", (id,))
        return {"status": "ok", "message": f"Credit with id {id} deleted successfully"}

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
