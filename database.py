# -*- coding: utf-8 -*-
"""
資料庫管理模組 (支援 Supabase PostgreSQL 與 本地 SQLite 自動回退切換)
提供：
1. 用戶目標與狀態 (身形/TDEE、當前定位模式 gps_mode、最新 GPS 座標 last_lat/last_lng/last_address)
2. 每日飲食記帳 (meal_records)
3. 每日喝水累計 (water_records)
4. 美食口袋收藏清單 (favorite_foods)
"""
import os
import json
from datetime import date
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
USE_POSTGRES = bool(SUPABASE_DB_URL and SUPABASE_DB_URL.startswith("postgresql://"))

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def get_connection():
        return psycopg2.connect(SUPABASE_DB_URL)
else:
    import sqlite3

    def get_db_path() -> str:
        custom_path = os.getenv("OUTDOOR_HUB_DB_PATH", "").strip()
        if custom_path:
            return custom_path
        if os.environ.get("VERCEL"):
            return "/tmp/outdoor_hub.db"
        return os.path.join(os.path.dirname(__file__), "outdoor_hub.db")

    def get_connection():
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            gender TEXT DEFAULT '男',
            height REAL DEFAULT 170.0,
            weight REAL DEFAULT 65.0,
            age INTEGER DEFAULT 28,
            activity TEXT DEFAULT '輕度',
            bmr INTEGER DEFAULT 1600,
            tdee INTEGER DEFAULT 2200,
            target_calories INTEGER DEFAULT 2000,
            gps_mode TEXT DEFAULT 'food',
            last_lat REAL,
            last_lng REAL,
            last_address TEXT DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_records (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            record_date TEXT NOT NULL,
            meal_name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein_g INTEGER DEFAULT 0,
            carbs_g INTEGER DEFAULT 0,
            fat_g INTEGER DEFAULT 0,
            meal_type TEXT DEFAULT '餐點',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_records (
            user_id TEXT NOT NULL,
            record_date TEXT NOT NULL,
            amount_ml INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, record_date)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_foods (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT DEFAULT '',
            calories INTEGER DEFAULT 500,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_name)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            created_by TEXT NOT NULL,
            title TEXT NOT NULL,
            options_json TEXT NOT NULL,
            votes_json TEXT DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            gender TEXT DEFAULT '男',
            height REAL DEFAULT 170.0,
            weight REAL DEFAULT 65.0,
            age INTEGER DEFAULT 28,
            activity TEXT DEFAULT '輕度',
            bmr INTEGER DEFAULT 1600,
            tdee INTEGER DEFAULT 2200,
            target_calories INTEGER DEFAULT 2000,
            gps_mode TEXT DEFAULT 'food',
            last_lat REAL,
            last_lng REAL,
            last_address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            record_date TEXT NOT NULL,
            meal_name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein_g INTEGER DEFAULT 0,
            carbs_g INTEGER DEFAULT 0,
            fat_g INTEGER DEFAULT 0,
            meal_type TEXT DEFAULT '餐點',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_records (
            user_id TEXT NOT NULL,
            record_date TEXT NOT NULL,
            amount_ml INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, record_date)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT DEFAULT '',
            calories INTEGER DEFAULT 500,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_name)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            created_by TEXT NOT NULL,
            title TEXT NOT NULL,
            options_json TEXT NOT NULL,
            votes_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    conn.commit()
    cursor.close()
    conn.close()


init_db()


def ensure_user_exists(user_id: str):
    """確保使用者記錄存在"""
    profile = get_user_profile(user_id)
    if not profile:
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(
                "INSERT INTO users (user_id, target_calories, gps_mode) VALUES (%s, 2000, 'food') ON CONFLICT(user_id) DO NOTHING;",
                (user_id,)
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, target_calories, gps_mode) VALUES (?, 2000, 'food');",
                (user_id,)
            )
        conn.commit()
        cursor.close()
        conn.close()


def save_user_profile(
    user_id: str,
    gender: str,
    height: float,
    weight: float,
    age: int,
    activity: str,
    bmr: int,
    tdee: int,
    target_calories: int
):
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
        INSERT INTO users (user_id, gender, height, weight, age, activity, bmr, tdee, target_calories, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            gender=EXCLUDED.gender,
            height=EXCLUDED.height,
            weight=EXCLUDED.weight,
            age=EXCLUDED.age,
            activity=EXCLUDED.activity,
            bmr=EXCLUDED.bmr,
            tdee=EXCLUDED.tdee,
            target_calories=EXCLUDED.target_calories,
            updated_at=CURRENT_TIMESTAMP;
        """, (user_id, gender, height, weight, age, activity, bmr, tdee, target_calories))
    else:
        cursor.execute("""
        INSERT INTO users (user_id, gender, height, weight, age, activity, bmr, tdee, target_calories, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            gender=excluded.gender,
            height=excluded.height,
            weight=excluded.weight,
            age=excluded.age,
            activity=excluded.activity,
            bmr=excluded.bmr,
            tdee=excluded.tdee,
            target_calories=excluded.target_calories,
            updated_at=CURRENT_TIMESTAMP;
        """, (user_id, gender, height, weight, age, activity, bmr, tdee, target_calories))
    conn.commit()
    cursor.close()
    conn.close()


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def save_user_location(user_id: str, lat: float, lng: float, address: str = "", gps_mode: Optional[str] = None):
    """儲存使用者最新 GPS 座標，供『美食 × 洗手間』雙模組無縫共用"""
    ensure_user_exists(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    if gps_mode:
        if USE_POSTGRES:
            cursor.execute("""
            UPDATE users SET last_lat = %s, last_lng = %s, last_address = %s, gps_mode = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s;
            """, (lat, lng, address, gps_mode, user_id))
        else:
            cursor.execute("""
            UPDATE users SET last_lat = ?, last_lng = ?, last_address = ?, gps_mode = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?;
            """, (lat, lng, address, gps_mode, user_id))
    else:
        if USE_POSTGRES:
            cursor.execute("""
            UPDATE users SET last_lat = %s, last_lng = %s, last_address = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s;
            """, (lat, lng, address, user_id))
        else:
            cursor.execute("""
            UPDATE users SET last_lat = ?, last_lng = ?, last_address = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?;
            """, (lat, lng, address, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def set_user_gps_mode(user_id: str, gps_mode: str):
    """設定使用者當前偏好的定位模式 ('food' 或 'toilet')"""
    ensure_user_exists(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("UPDATE users SET gps_mode = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;", (gps_mode, user_id))
    else:
        cursor.execute("UPDATE users SET gps_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?;", (gps_mode, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def get_user_location(user_id: str) -> Optional[Dict[str, Any]]:
    """取得使用者記憶中的最新 GPS 座標與定位模式"""
    profile = get_user_profile(user_id)
    if not profile or profile.get("last_lat") is None or profile.get("last_lng") is None:
        return None
    return {
        "lat": float(profile["last_lat"]),
        "lng": float(profile["last_lng"]),
        "address": profile.get("last_address") or "記憶座標位置",
        "gps_mode": profile.get("gps_mode") or "food"
    }


def add_meal_record(
    user_id: str,
    meal_name: str,
    calories: int,
    protein_g: int = 0,
    carbs_g: int = 0,
    fat_g: int = 0,
    meal_type: str = "餐點"
):
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
        INSERT INTO meal_records (user_id, record_date, meal_name, calories, protein_g, carbs_g, fat_g, meal_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (user_id, today_str, meal_name, calories, protein_g, carbs_g, fat_g, meal_type))
    else:
        cursor.execute("""
        INSERT INTO meal_records (user_id, record_date, meal_name, calories, protein_g, carbs_g, fat_g, meal_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (user_id, today_str, meal_name, calories, protein_g, carbs_g, fat_g, meal_type))
    conn.commit()
    cursor.close()
    conn.close()


def get_today_summary(user_id: str) -> Dict[str, Any]:
    today_str = date.today().isoformat()
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
        SELECT 
            COALESCE(SUM(calories), 0)::integer as total_calories,
            COALESCE(SUM(protein_g), 0)::integer as total_protein,
            COALESCE(SUM(carbs_g), 0)::integer as total_carbs,
            COALESCE(SUM(fat_g), 0)::integer as total_fat,
            COUNT(id)::integer as meal_count
        FROM meal_records
        WHERE user_id = %s AND record_date = %s;
        """, (user_id, today_str))
        summary = dict(cursor.fetchone() or {})

        cursor.execute("""
        SELECT meal_name, calories, protein_g, carbs_g, fat_g, to_char(created_at, 'HH24:MI') as time_str
        FROM meal_records
        WHERE user_id = %s AND record_date = %s
        ORDER BY created_at ASC;
        """, (user_id, today_str))
        meals = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT amount_ml FROM water_records WHERE user_id = %s AND record_date = %s;", (user_id, today_str))
        w_row = cursor.fetchone()
        water_ml = w_row["amount_ml"] if w_row else 0
    else:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            COALESCE(SUM(calories), 0) as total_calories,
            COALESCE(SUM(protein_g), 0) as total_protein,
            COALESCE(SUM(carbs_g), 0) as total_carbs,
            COALESCE(SUM(fat_g), 0) as total_fat,
            COUNT(id) as meal_count
        FROM meal_records
        WHERE user_id = ? AND record_date = ?;
        """, (user_id, today_str))
        summary = dict(cursor.fetchone())

        cursor.execute("""
        SELECT meal_name, calories, protein_g, carbs_g, fat_g, strftime('%H:%M', created_at) as time_str
        FROM meal_records
        WHERE user_id = ? AND record_date = ?
        ORDER BY created_at ASC;
        """, (user_id, today_str))
        meals = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT amount_ml FROM water_records WHERE user_id = ? AND record_date = ?;", (user_id, today_str))
        w_row = cursor.fetchone()
        water_ml = w_row["amount_ml"] if w_row else 0

    cursor.close()
    conn.close()

    profile = get_user_profile(user_id)
    target_calories = profile.get("target_calories", 2000) if profile else 2000
    consumed = int(summary.get("total_calories", 0))
    summary["target_calories"] = int(target_calories)
    summary["remaining_calories"] = int(target_calories) - consumed
    summary["meals"] = meals
    summary["water_ml"] = int(water_ml)
    return summary


def get_remaining_calories(user_id: str) -> Dict[str, int]:
    """回傳使用者今日目標、已攝取與剩餘熱量額度"""
    summary = get_today_summary(user_id)
    return {
        "target_calories": summary["target_calories"],
        "consumed_calories": summary["total_calories"],
        "remaining_calories": summary["remaining_calories"]
    }


def add_water(user_id: str, amount_ml: int = 300) -> int:
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
        INSERT INTO water_records (user_id, record_date, amount_ml)
        VALUES (%s, %s, %s)
        ON CONFLICT(user_id, record_date) DO UPDATE SET
            amount_ml = water_records.amount_ml + EXCLUDED.amount_ml;
        """, (user_id, today_str, amount_ml))
        conn.commit()
        cursor.execute("SELECT amount_ml FROM water_records WHERE user_id = %s AND record_date = %s;", (user_id, today_str))
        row = cursor.fetchone()
        total_water = row[0] if row else amount_ml
    else:
        cursor.execute("""
        INSERT INTO water_records (user_id, record_date, amount_ml)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, record_date) DO UPDATE SET
            amount_ml = amount_ml + excluded.amount_ml;
        """, (user_id, today_str, amount_ml))
        conn.commit()
        cursor.execute("SELECT amount_ml FROM water_records WHERE user_id = ? AND record_date = ?;", (user_id, today_str))
        row = cursor.fetchone()
        total_water = row["amount_ml"] if row else amount_ml

    cursor.close()
    conn.close()
    return int(total_water)


def clear_today_records(user_id: str):
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("DELETE FROM meal_records WHERE user_id = %s AND record_date = %s;", (user_id, today_str))
        cursor.execute("DELETE FROM water_records WHERE user_id = %s AND record_date = %s;", (user_id, today_str))
    else:
        cursor.execute("DELETE FROM meal_records WHERE user_id = ? AND record_date = ?;", (user_id, today_str))
        cursor.execute("DELETE FROM water_records WHERE user_id = ? AND record_date = ?;", (user_id, today_str))
    conn.commit()
    cursor.close()
    conn.close()


def add_favorite_food(user_id: str, item_name: str, category: str = "", calories: int = 500):
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
        INSERT INTO favorite_foods (user_id, item_name, category, calories)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(user_id, item_name) DO NOTHING;
        """, (user_id, item_name, category, calories))
    else:
        cursor.execute("""
        INSERT OR IGNORE INTO favorite_foods (user_id, item_name, category, calories)
        VALUES (?, ?, ?, ?);
        """, (user_id, item_name, category, calories))
    conn.commit()
    cursor.close()
    conn.close()


def get_favorite_foods(user_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM favorite_foods WHERE user_id = %s ORDER BY created_at DESC;", (user_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM favorite_foods WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


def create_poll(poll_id: str, created_by: str, title: str, options: List[Dict[str, Any]]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    options_json = json.dumps(options, ensure_ascii=False)
    votes_json = json.dumps({}, ensure_ascii=False)
    if USE_POSTGRES:
        cursor.execute("""
        INSERT INTO polls (poll_id, created_by, title, options_json, votes_json)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT(poll_id) DO UPDATE SET options_json=EXCLUDED.options_json;
        """, (poll_id, created_by, title, options_json, votes_json))
    else:
        cursor.execute("""
        INSERT OR REPLACE INTO polls (poll_id, created_by, title, options_json, votes_json)
        VALUES (?, ?, ?, ?, ?);
        """, (poll_id, created_by, title, options_json, votes_json))
    conn.commit()
    cursor.close()
    conn.close()
    return {"poll_id": poll_id, "title": title, "options": options, "votes": {}}


def vote_poll(poll_id: str, user_id: str, option_idx: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if USE_POSTGRES else conn.cursor()
    if USE_POSTGRES:
        cursor.execute("SELECT * FROM polls WHERE poll_id = %s;", (poll_id,))
    else:
        cursor.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return None
    r_dict = dict(row)
    votes = json.loads(r_dict.get("votes_json") or "{}")
    votes[user_id] = option_idx
    new_votes_json = json.dumps(votes, ensure_ascii=False)

    update_cursor = conn.cursor()
    if USE_POSTGRES:
        update_cursor.execute("UPDATE polls SET votes_json = %s WHERE poll_id = %s;", (new_votes_json, poll_id))
    else:
        update_cursor.execute("UPDATE polls SET votes_json = ? WHERE poll_id = ?;", (new_votes_json, poll_id))
    conn.commit()
    update_cursor.close()
    cursor.close()
    conn.close()

    options = json.loads(r_dict.get("options_json") or "[]")
    return {
        "poll_id": poll_id,
        "title": r_dict.get("title", ""),
        "options": options,
        "votes": votes
    }


def get_poll(poll_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if USE_POSTGRES else conn.cursor()
    if USE_POSTGRES:
        cursor.execute("SELECT * FROM polls WHERE poll_id = %s;", (poll_id,))
    else:
        cursor.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    r_dict = dict(row)
    return {
        "poll_id": poll_id,
        "title": r_dict.get("title", ""),
        "options": json.loads(r_dict.get("options_json") or "[]"),
        "votes": json.loads(r_dict.get("votes_json") or "{}"),
        "created_by": r_dict.get("created_by", "")
    }


def get_recent_history(user_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """取得最近幾天的飲食與熱量統計（供 LIFF 圖表使用）"""
    from datetime import timedelta
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if USE_POSTGRES else conn.cursor()
    
    result = []
    today = date.today()
    for i in range(days - 1, -1, -1):
        target_date = today - timedelta(days=i)
        d_str = target_date.isoformat()
        if USE_POSTGRES:
            cursor.execute("""
            SELECT COALESCE(SUM(calories), 0) as total_cal,
                   COALESCE(SUM(protein_g), 0) as total_protein,
                   COALESCE(SUM(carbs_g), 0) as total_carbs,
                   COALESCE(SUM(fat_g), 0) as total_fat
            FROM meal_records WHERE user_id = %s AND record_date = %s;
            """, (user_id, d_str))
        else:
            cursor.execute("""
            SELECT COALESCE(SUM(calories), 0) as total_cal,
                   COALESCE(SUM(protein_g), 0) as total_protein,
                   COALESCE(SUM(carbs_g), 0) as total_carbs,
                   COALESCE(SUM(fat_g), 0) as total_fat
            FROM meal_records WHERE user_id = ? AND record_date = ?;
            """, (user_id, d_str))
        row = cursor.fetchone()
        row_dict = dict(row) if row else {}
        result.append({
            "date": d_str,
            "display_date": target_date.strftime("%m/%d"),
            "calories": int(row_dict.get("total_cal", 0)),
            "protein": int(row_dict.get("total_protein", 0)),
            "carbs": int(row_dict.get("total_carbs", 0)),
            "fat": int(row_dict.get("total_fat", 0))
        })
    cursor.close()
    conn.close()
    return result

