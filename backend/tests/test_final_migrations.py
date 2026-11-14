"""Migration checks run only against disposable SQLite databases."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest

@pytest.mark.parametrize('existing',[False,True])
def test_retry_migration_preserves_existing_rows(tmp_path,existing):
    path=tmp_path/'migration.db'
    if existing:
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE listings (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, title TEXT NOT NULL)')
            db.execute("INSERT INTO listings VALUES (1, 7, 'Preserved report')")
            db.execute('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)')
            db.execute("INSERT INTO alembic_version VALUES ('0002_revoked_tokens')")
    env={**os.environ,'DATABASE_URL':f'sqlite:///{path}','ENVIRONMENT':'development'}
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    with sqlite3.connect(path) as db:
        assert 'client_request_id' in {r[1] for r in db.execute('PRAGMA table_info(listings)')}
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0003_report_idempotency'
        if existing: assert db.execute('SELECT title,client_request_id FROM listings').fetchone()==('Preserved report',None)
