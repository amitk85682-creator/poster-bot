# -*- coding: utf-8 -*-
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict
from contextlib import contextmanager

# Supabase PostgreSQL Connection String
DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Get database connection"""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    finally:
        if conn:
            conn.close()

@contextmanager
def get_db_cursor(commit=False):
    """Get database cursor"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        finally:
            cursor.close()

class ForceSubDB:
    
    @staticmethod
    def init_db():
        """Initialize database tables"""
        with get_db_cursor(commit=True) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS force_subscribe (
                    id SERIAL PRIMARY KEY,
                    main_chat_id BIGINT NOT NULL,
                    main_chat_title TEXT,
                    target_chat_id BIGINT NOT NULL,
                    target_chat_title TEXT,
                    target_link TEXT NOT NULL,
                    added_by BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(main_chat_id, target_chat_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_main_chat 
                ON force_subscribe(main_chat_id)
            ''')
    
    @staticmethod
    def add_force_sub(main_chat_id: int, main_chat_title: str, 
                      target_chat_id: int, target_chat_title: str,
                      target_link: str, added_by: int) -> bool:
        """Add a force subscribe channel"""
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute('''
                    INSERT INTO force_subscribe 
                    (main_chat_id, main_chat_title, target_chat_id, target_chat_title, target_link, added_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (main_chat_id, target_chat_id) 
                    DO UPDATE SET 
                        target_link = EXCLUDED.target_link,
                        target_chat_title = EXCLUDED.target_chat_title
                ''', (main_chat_id, main_chat_title, target_chat_id, target_chat_title, target_link, added_by))
            return True
        except Exception as e:
            print(f"Error adding force sub: {e}")
            return False
    
    @staticmethod
    def remove_force_sub(main_chat_id: int, target_chat_id: int) -> bool:
        """Remove a force subscribe channel"""
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute('''
                    DELETE FROM force_subscribe 
                    WHERE main_chat_id = %s AND target_chat_id = %s
                ''', (main_chat_id, target_chat_id))
            return True
        except Exception as e:
            print(f"Error removing force sub: {e}")
            return False
    
    @staticmethod
    def get_force_subs(main_chat_id: int) -> List[Dict]:
        """Get all force subscribe channels for a group"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM force_subscribe 
                    WHERE main_chat_id = %s
                ''', (main_chat_id,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting force subs: {e}")
            return []
    
    @staticmethod
    def remove_all_force_subs(main_chat_id: int) -> bool:
        """Remove all force subscribe channels for a group"""
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute('''
                    DELETE FROM force_subscribe 
                    WHERE main_chat_id = %s
                ''', (main_chat_id,))
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    @staticmethod
    def get_all_groups() -> List[Dict]:
        """Get all unique groups with force sub"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute('''
                    SELECT DISTINCT main_chat_id, main_chat_title 
                    FROM force_subscribe
                ''')
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"Error: {e}")
            return []

# Initialize database on import
try:
    ForceSubDB.init_db()
    print("✅ Database initialized!")
except Exception as e:
    print(f"⚠️ Database init error: {e}")
