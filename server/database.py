import sqlite3
from contextlib import contextmanager
from config import DATABASE_FILE


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            session_id TEXT PRIMARY KEY,
            candidates TEXT,
            end_time REAL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes(
            participation_id TEXT PRIMARY KEY,
            session_id TEXT,
            choice INTEGER,
            vote_hash TEXT
        )
        """)


def create_session(session_id, candidates, end_time):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (session_id, "|".join(candidates), end_time.timestamp())
        )


def get_session(session_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE session_id=?",
            (session_id,)
        )
        return cursor.fetchone()


def register_vote(participation_id, session_id, choice, vote_hash):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO votes
        VALUES (?, ?, ?, ?)
        """, (participation_id, session_id, choice, vote_hash))


def get_votes(session_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT choice FROM votes WHERE session_id=?",
            (session_id,)
        )
        return cursor.fetchall()


def get_votes_with_hash(session_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT choice, vote_hash FROM votes WHERE session_id=?",
            (session_id,)
        )
        return cursor.fetchall()