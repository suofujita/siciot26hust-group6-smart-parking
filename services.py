from datetime import datetime
from database import get_connection, get_active_session, create_session, close_session

FMT = "%Y-%m-%d %H:%M:%S"

import sqlite3


def handle_entry(rfid_uid):
    """Trả về (ok, msg)."""
    rfid_uid = str(rfid_uid)
    now = datetime.now().strftime(FMT)
    conn = get_connection()
    try:
        create_session(conn, rfid_uid, now)
        return True, f"Card {rfid_uid} entered at {now}"
    except (ValueError, sqlite3.IntegrityError):
        return False, f"Card {rfid_uid} is already in use"
    finally:
        conn.close()

def handle_exit(rfid_uid):
    """Return (ok, msg, fee)."""
    rfid_uid = str(rfid_uid)
    now = datetime.now().strftime(FMT)
    conn = get_connection()
    try:
        fee = close_session(conn, rfid_uid, now)
        return True, f"Card {rfid_uid} exited at {now}, fee: {fee} VND", fee
    except ValueError as e:
        return False, f"Card {rfid_uid}: {e}", 0
    finally:
        conn.close()