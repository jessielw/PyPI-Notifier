import sqlite3
from pathlib import Path


def init_database(db_path: Path) -> sqlite3.Connection:
    """Create necessary tables if they don't already exist."""
    db_conn = sqlite3.connect(db_path)
    cursor = db_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS releases (
            package_name TEXT NOT NULL,
            url TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    db_conn.commit()
    return db_conn
