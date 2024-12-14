import sqlite3
from pathlib import Path


def init_database(db_path: Path) -> sqlite3.Connection:
    """Create necessary tables if they don't already exist."""
    db_conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = db_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS releases (
            package_name TEXT NOT NULL,
            url TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    cursor.execute("PRAGMA journal_mode=WAL;")

    db_conn.commit()
    return db_conn


def db_worker_select(db_conn: sqlite3.Connection, url):
    """Select data from the database."""
    cursor = db_conn.execute(
        "SELECT last_updated, version FROM releases WHERE url = ?", (url,)
    )
    return cursor.fetchone()


def db_worker_insert(
    db_conn: sqlite3.Connection, package_name, release_url, version, last_updated
) -> None:
    """Insert or update data in the database."""
    with db_conn:
        db_conn.execute(
            """
            INSERT INTO releases (package_name, url, version, last_updated) 
            VALUES (?, ?, ?, ?) 
            ON CONFLICT(url) DO UPDATE SET
                version = excluded.version,
                last_updated = excluded.last_updated
        """,
            (package_name, release_url, version, last_updated),
        )
