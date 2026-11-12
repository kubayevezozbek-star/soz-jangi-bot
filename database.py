import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

def _get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_sync():
    with _get_connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                score INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT,
                user_id INTEGER,
                day INTEGER,
                score INTEGER,
                rank INTEGER,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

async def init_db():
    init_sync()
    logger.info("Database initialized successfully.")

async def get_or_create_user(user_id: int, username: str = "", first_name: str = ""):
    with _get_connection() as db:
        cursor = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            db.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username or "", first_name or "")
            )
            db.commit()
            cursor = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        else:
            if username or first_name:
                db.execute(
                    "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                    (username or row["username"], first_name or row["first_name"], user_id)
                )
                db.commit()
        return dict(row)

async def get_user(user_id: int):
    with _get_connection() as db:
        cursor = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

async def update_user_stats(user_id: int, score_delta: int = 0, is_win: bool = False, correct_delta: int = 0, wrong_delta: int = 0):
    with _get_connection() as db:
        db.execute("""
            UPDATE users SET 
                score = MAX(0, score + ?),
                games_played = games_played + 1,
                wins = wins + ?,
                correct_count = correct_count + ?,
                wrong_count = wrong_count + ?
            WHERE user_id = ?
        """, (score_delta, 1 if is_win else 0, correct_delta, wrong_delta, user_id))
        db.commit()

async def get_top_users(limit: int = 10):
    with _get_connection() as db:
        cursor = db.execute(
            "SELECT * FROM users ORDER BY score DESC, wins DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

async def record_game(room_id: str, user_id: int, day: int, score: int, rank: int):
    with _get_connection() as db:
        db.execute("""
            INSERT INTO game_history (room_id, user_id, day, score, rank)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, user_id, day, score, rank))
        db.commit()

async def get_total_stats():
    with _get_connection() as db:
        cursor = db.execute("SELECT COUNT(*), SUM(games_played) FROM users")
        row = cursor.fetchone()
        total_users = row[0] if row else 0
        total_games = row[1] if row and row[1] else 0
        return {"total_users": total_users, "total_games": total_games}
