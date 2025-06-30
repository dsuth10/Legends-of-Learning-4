import sqlite3
import threading
import time
import os
from flask import current_app

LATEST_ALEMBIC_REVISION = 'yyyy'

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'legends.db')


def check_db_version(app):
    """
    Check the current Alembic migration version in the database and compare to the latest.
    Print a warning if out of date.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('SELECT version_num FROM alembic_version')
            row = cur.fetchone()
            if not row:
                print('[DB Version Check] No alembic_version found!')
            elif row[0] != LATEST_ALEMBIC_REVISION:
                print(f'[DB Version Check] WARNING: DB version {row[0]} does not match latest migration {LATEST_ALEMBIC_REVISION}')
            else:
                print('[DB Version Check] Database schema is up to date.')
    except Exception as e:
        print(f'[DB Version Check] Error: {e}')


def run_integrity_check():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('PRAGMA integrity_check')
            result = cur.fetchone()
            if result and result[0] != 'ok':
                print(f'[DB Integrity Check] WARNING: Integrity check failed: {result[0]}')
            else:
                print('[DB Integrity Check] Database integrity OK.')
    except Exception as e:
        print(f'[DB Integrity Check] Error: {e}')


def start_weekly_integrity_check(app):
    """
    Start a background thread that runs PRAGMA integrity_check every 7 days.
    """
    def loop():
        while True:
            run_integrity_check()
            time.sleep(7 * 24 * 60 * 60)  # 7 days
    t = threading.Thread(target=loop, daemon=True)
    t.start() 