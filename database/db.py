"""
SQLite database layer for lottery data persistence.
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lottery.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_conn()
    cur = conn.cursor()
    # 双色球历史表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ssq_history (
            expect TEXT PRIMARY KEY,
            date TEXT,
            red_balls TEXT,
            blue_ball TEXT,
            red_1 INTEGER, red_2 INTEGER, red_3 INTEGER,
            red_4 INTEGER, red_5 INTEGER, red_6 INTEGER,
            blue INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 大乐透历史表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dlt_history (
            expect TEXT PRIMARY KEY,
            date TEXT,
            front_balls TEXT,
            back_balls TEXT,
            front_1 INTEGER, front_2 INTEGER, front_3 INTEGER,
            front_4 INTEGER, front_5 INTEGER,
            back_1 INTEGER, back_2 INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def upsert_ssq(expect: str, date: str, red_balls: str, blue_ball: str,
               r1, r2, r3, r4, r5, r6, blue: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO ssq_history
        (expect, date, red_balls, blue_ball, red_1, red_2, red_3,
         red_4, red_5, red_6, blue, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (expect, date, red_balls, blue_ball, r1, r2, r3, r4, r5, r6, blue,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def upsert_dlt(expect: str, date: str, front_balls: str, back_balls: str,
               f1, f2, f3, f4, f5, b1, b2: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO dlt_history
        (expect, date, front_balls, back_balls,
         front_1, front_2, front_3, front_4, front_5,
         back_1, back_2, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (expect, date, front_balls, back_balls, f1, f2, f3, f4, f5, b1, b2,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_ssq_history(limit: int = 100) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM ssq_history ORDER BY expect DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_dlt_history(limit: int = 100) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM dlt_history ORDER BY expect DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_ssq_count() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ssq_history")
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt


def get_dlt_count() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dlt_history")
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt


# ─────────────────────────────────────────────────────────────
# 预测记录表
# ─────────────────────────────────────────────────────────────

def init_predictions():
    """创建预测记录表"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL,
            strategy_key TEXT NOT NULL,
            expect TEXT NOT NULL,
            predicted_at TEXT NOT NULL,
            red_balls TEXT,
            blue_ball TEXT,
            front_balls TEXT,
            back_balls TEXT,
            red_hit INTEGER DEFAULT 0,
            blue_hit INTEGER DEFAULT 0,
            front_hit INTEGER DEFAULT 0,
            back_hit INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_prediction(
    lottery_type: str,
    strategy_key: str,
    expect: str,
    red_balls: str = None,
    blue_ball: str = None,
    front_balls: str = None,
    back_balls: str = None,
) -> int:
    """保存一组预测，返回自增id"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
        (lottery_type, strategy_key, expect, predicted_at,
         red_balls, blue_ball, front_balls, back_balls)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lottery_type, strategy_key, expect,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        red_balls, blue_ball, front_balls, back_balls
    ))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def update_prediction_result(pred_id: int, red_hit: int = 0, blue_hit: int = 0,
                              front_hit: int = 0, back_hit: int = 0, rank: int = 0):
    """更新预测记录的中奖结果"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE predictions
        SET red_hit=?, blue_hit=?, front_hit=?, back_hit=?, rank=?
        WHERE id=?
    """, (red_hit, blue_hit, front_hit, back_hit, rank, pred_id))
    conn.commit()
    conn.close()


def get_predictions(limit: int = 50, lottery_type: str = None) -> List[sqlite3.Row]:
    """查询预测记录"""
    conn = get_conn()
    cur = conn.cursor()
    if lottery_type:
        cur.execute(
            "SELECT * FROM predictions WHERE lottery_type=? ORDER BY id DESC LIMIT ?",
            (lottery_type, limit)
        )
    else:
        cur.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_prediction(pred_id: int):
    """删除一条预测记录"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM predictions WHERE id=?", (pred_id,))
    conn.commit()
    conn.close()


def clear_predictions(lottery_type: str = None):
    """清空预测记录"""
    conn = get_conn()
    cur = conn.cursor()
    if lottery_type:
        cur.execute("DELETE FROM predictions WHERE lottery_type=?", (lottery_type,))
    else:
        cur.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
