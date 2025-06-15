import sqlite3
import os

db_path = "/app/db_data/data.sqlite"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolios';")
    result = cursor.fetchone()

    if result:
        print("✅ La table 'portfolios' existe.")
    else:
        print("❌ La table 'portfolios' est absente.")

    conn.close()
else:
    print("❌ Le fichier data.sqlite n'existe pas.")
