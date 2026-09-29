import os, sqlite3
from datetime import datetime
import pricing

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
DATABASE = os.path.join(os.path.dirname(__file__), "parking.db")

def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    """Initialize the database."""
    conn = get_connection()
    with open(SCHEMA_PATH, encoding = "utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def get_active_session(conn, rfid_uid):
    """Get the active parking session for a given RFID UID."""
    return conn.execute(
        "SELECT * FROM parking_sessions WHERE rfid_uid = ? AND status = 'active'",
        (rfid_uid,),
    ).fetchone()

def create_session(conn, rfid_uid, time_in):
    """Create a new parking session."""
    if get_active_session(conn, rfid_uid):
        raise ValueError("A session is already active for this RFID UID.")
    cur = conn.execute(
        "INSERT INTO parking_sessions (rfid_uid, time_in, status) VALUES (?, ?, 'active')",
        (rfid_uid, time_in),
    )
    conn.commit()
    return cur.lastrowid

def close_session(conn, rfid_uid, time_out):
    """Close an active parking session."""
    session = get_active_session(conn, rfid_uid)
    if not session:
        raise ValueError("No active session found for this RFID UID.")
    fee = pricing.calculate_fee(session["time_in"], time_out)
    conn.execute(
        "UPDATE parking_sessions SET time_out = ?, fee = ?, status = 'completed' WHERE session_id = ?",
        (time_out, fee, session["session_id"]),
    )
    conn.commit()
    return fee

def update_slot_status(conn, slot_id, status):
    """Update the status of a parking slot ('empty' or 'occupied')."""
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE parking_slots SET status = ?, updated_at = ? WHERE slot_id = ?",
        (status, updated_at, slot_id),
    )
    conn.commit()

def get_all_slots(conn):
    """Get all parking slots."""
    return conn.execute("SELECT * FROM parking_slots").fetchall()

def get_available_slots(conn, zone_id=None):
    """Get the number of available parking slots."""
    if zone_id is not None:
        return conn.execute("SELECT COUNT(*) AS available FROM parking_slots WHERE status = 'empty' AND zone_id = ?", (zone_id,)).fetchone()["available"]
    return conn.execute("SELECT COUNT(*) AS available FROM parking_slots WHERE status = 'empty'").fetchone()["available"]