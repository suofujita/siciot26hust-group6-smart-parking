from datetime import datetime

from flask import Flask, render_template
from database import get_connection, init_db

app = Flask(__name__)

TOTAL_SLOTS = 4          # phải bằng TOTAL_SLOTS trong hardware/display.py
HISTORY_LIMIT = 20       # số dòng lịch sử hiển thị

@app.route("/")
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        # Lịch sử: mới nhất trước
        sessions = conn.execute(
            "SELECT * FROM parking_sessions ORDER BY time_in DESC LIMIT ?",
            (HISTORY_LIMIT,),
        ).fetchall()

        # Doanh thu hôm nay = tổng phí các lượt ĐÃ RA trong ngày
        daily_revenue = conn.execute(
            "SELECT COALESCE(SUM(fee), 0) FROM parking_sessions "
            "WHERE status = 'completed' AND time_out LIKE ?",
            (today + "%",),
        ).fetchone()[0]

        # Trạng thái từng ô đỗ (do cảm biến cập nhật)
        slots = conn.execute(
            "SELECT slot_code, status, updated_at FROM parking_slots ORDER BY slot_code"
        ).fetchall()

        # Hai số hiển thị trên màn hình thật, cùng công thức với hardware/display.py
        active = conn.execute(
            "SELECT COUNT(*) FROM parking_sessions WHERE status = 'active'"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT zone_id, COUNT(*) AS n FROM parking_slots "
            "WHERE status = 'empty' GROUP BY zone_id"
        ).fetchall()
        counts = {r["zone_id"]: r["n"] for r in rows}
    finally:
        conn.close()

    return render_template(
        "index.html",
        sessions=sessions,
        daily_revenue=daily_revenue,
        active_sessions=slots,                 # template dùng tên này cho danh sách ô đỗ
        lcd_free=max(TOTAL_SLOTS - active, 0),
        oled_left=counts.get("left", 0),
        oled_right=counts.get("right", 0),
        total_slots=TOTAL_SLOTS,
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)