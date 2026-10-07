from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils.database import get_db_connection


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE email = ?', (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(name, email, password):
    clean_name = (name or '').strip()
    clean_email = (email or '').strip().lower()
    if not clean_name:
        raise ValueError('Full name is required.')
    if not clean_email:
        raise ValueError('Email is required.')
    if len(password or '') < 6:
        raise ValueError('Password must be at least 6 characters long.')

    existing = get_user_by_email(clean_email)
    if existing:
        raise ValueError('An account with this email already exists.')

    password_hash = hash_password(password)
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        (clean_name, clean_email, password_hash)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return get_user_by_email(clean_email)


def login_user(user):
    session.clear()
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']


def logout_user():
    session.clear()


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not get_current_user():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


__all__ = [
    'create_user',
    'get_current_user',
    'get_user_by_email',
    'hash_password',
    'login_required',
    'login_user',
    'logout_user',
    'verify_password',
]
