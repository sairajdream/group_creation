import sqlite3

DB_FILE = "groups.db"

# Connect to the database
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Create the required tables
c.execute('''CREATE TABLE IF NOT EXISTS groups
(id INTEGER PRIMARY KEY AUTOINCREMENT,
members TEXT,
vacancies INTEGER,
created_at TIMESTAMP)''')

c.execute('''CREATE TABLE IF NOT EXISTS individuals
(id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
student_id TEXT UNIQUE,
email TEXT,
created_at TIMESTAMP)''')

conn.commit()
conn.close()

print(f"Database '{DB_FILE}' initialized successfully.")
