import os
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from .database import get_db_connection, DB_PATH


def _format_screening_id(rowid: int) -> str:
    year = datetime.now().year
    return f"RS-{year}-{rowid:06d}"


def create_screening(
    user_id: int,
    patient_age: Optional[int],
    blood_sugar: Optional[float],
    blood_pressure: Optional[str],
    predicted_class: str,
    confidence: float,
    probabilities: List[float],
    risk_level: str,
    risk_score: float,
    image_filename: Optional[str],
    gradcam_filename: Optional[str],
    audio_filename: Optional[str],
    voice_language: Optional[str],
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO screenings (
            user_id, patient_age, blood_sugar, blood_pressure,
            predicted_class, confidence,
            mild_probability, moderate_probability, no_dr_probability,
            proliferate_dr_probability, severe_probability,
            risk_level, risk_score,
            image_filename, gradcam_filename, audio_filename, voice_language
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            patient_age,
            blood_sugar,
            blood_pressure,
            predicted_class,
            confidence,
            float(probabilities[0]) if len(probabilities) > 0 else None,
            float(probabilities[1]) if len(probabilities) > 1 else None,
            float(probabilities[2]) if len(probabilities) > 2 else None,
            float(probabilities[3]) if len(probabilities) > 3 else None,
            float(probabilities[4]) if len(probabilities) > 4 else None,
            risk_level,
            risk_score,
            image_filename,
            gradcam_filename,
            audio_filename,
            voice_language,
        )
    )
    conn.commit()
    rowid = cursor.lastrowid
    screening_id = _format_screening_id(rowid)
    cursor.execute('UPDATE screenings SET screening_id = ? WHERE id = ?', (screening_id, rowid))
    conn.commit()
    screening = conn.execute('SELECT * FROM screenings WHERE id = ?', (rowid,)).fetchone()
    conn.close()
    return dict(screening) if screening else {}


def get_recent_screenings(user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM screenings WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_screenings_for_user(user_id: int, q: Optional[str] = None, risk: Optional[str] = None, stage: Optional[str] = None, order: str = 'newest') -> List[Dict[str, Any]]:
    conn = get_db_connection()
    sql = 'SELECT * FROM screenings WHERE user_id = ?'
    params: List[Any] = [user_id]
    if q:
        sql += ' AND (screening_id LIKE ? OR predicted_class LIKE ? )'
        qparam = f'%{q}%'
        params.extend([qparam, qparam])
    if risk and risk.lower() != 'all':
        sql += ' AND risk_level = ?'
        params.append(risk)
    if stage and stage.lower() != 'all':
        sql += ' AND predicted_class = ?'
        params.append(stage)
    if order == 'oldest':
        sql += ' ORDER BY created_at ASC'
    else:
        sql += ' ORDER BY created_at DESC'
    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_screening_by_screening_id(user_id: int, screening_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM screenings WHERE screening_id = ? AND user_id = ?', (screening_id, user_id)).fetchone()
    conn.close()
    return dict(row) if row else None


__all__ = [
    'create_screening',
    'get_recent_screenings',
    'get_screenings_for_user',
    'get_screening_by_screening_id',
]
