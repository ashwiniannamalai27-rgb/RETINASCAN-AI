import os
import sqlite3


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
DB_PATH = os.path.join(DB_DIR, 'retinascan.db')


def ensure_db_directory():
    os.makedirs(DB_DIR, exist_ok=True)


def get_db_connection():
    ensure_db_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    ensure_db_directory()
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Screenings table stores historical screening records linked to users
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screening_id TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            patient_age INTEGER,
            blood_sugar REAL,
            blood_pressure TEXT,
            predicted_class TEXT,
            confidence REAL,
            mild_probability REAL,
            moderate_probability REAL,
            no_dr_probability REAL,
            proliferate_dr_probability REAL,
            severe_probability REAL,
            risk_level TEXT,
            risk_score REAL,
            image_filename TEXT,
            gradcam_filename TEXT,
            audio_filename TEXT,
            voice_language TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


__all__ = ["DB_PATH", "get_db_connection", "init_db"]
