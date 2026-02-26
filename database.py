import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger('thronos_bot.database')

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'thronos.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Proposals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            author_id INTEGER NOT NULL,
            author_name TEXT,
            votes_yes INTEGER DEFAULT 0,
            votes_no INTEGER DEFAULT 0,
            message_id INTEGER,
            channel_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Votes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            vote_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposal_id) REFERENCES proposals(id),
            UNIQUE(proposal_id, user_id)
        )
    ''')
    
    # User stats table for leaderboard
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            message_count INTEGER DEFAULT 0,
            reaction_count INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            last_active TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Proposal functions
def create_proposal(title, description, author_id, author_name, message_id, channel_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO proposals (title, description, author_id, author_name, message_id, channel_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, author_id, author_name, message_id, channel_id))
    proposal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return proposal_id

def get_proposal(proposal_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proposals WHERE id = ?', (proposal_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_proposal_votes(proposal_id, votes_yes, votes_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE proposals SET votes_yes = ?, votes_no = ? WHERE id = ?
    ''', (votes_yes, votes_no, proposal_id))
    conn.commit()
    conn.close()

def get_all_proposals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proposals ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Vote functions
def add_vote(proposal_id, user_id, vote_type):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO votes (proposal_id, user_id, vote_type) VALUES (?, ?, ?)
        ''', (proposal_id, user_id, vote_type))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def has_voted(proposal_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM votes WHERE proposal_id = ? AND user_id = ?', (proposal_id, user_id))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# Leaderboard functions
def update_user_stats(user_id, username, messages=0, reactions=0, referrals=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_stats (user_id, username, message_count, reaction_count, referral_count, xp, last_active)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            message_count = user_stats.message_count + excluded.message_count,
            reaction_count = user_stats.reaction_count + excluded.reaction_count,
            referral_count = user_stats.referral_count + excluded.referral_count,
            xp = user_stats.xp + (excluded.message_count * 10) + (excluded.reaction_count * 5) + (excluded.referral_count * 50),
            last_active = CURRENT_TIMESTAMP
    ''', (user_id, username, messages, reactions, referrals))
    conn.commit()
    conn.close()

def get_leaderboard(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, message_count, reaction_count, referral_count, xp
        FROM user_stats ORDER BY xp DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_rank(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) + 1 as rank FROM user_stats 
        WHERE xp > (SELECT COALESCE(xp, 0) FROM user_stats WHERE user_id = ?)
    ''', (user_id,))
    rank = cursor.fetchone()['rank']
    cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return rank, dict(user) if user else None

# Initialize on import
init_db()
