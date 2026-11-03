"""Migration regression limited to temporary schemas in a test/CI database."""
import os
import uuid
import pytest
from sqlalchemy import text,inspect
from sqlalchemy.engine import make_url

def test_mcp_clean_and_existing_schema_upgrade(monkeypatch):
    original=os.environ.get('NEXUS_DATABASE_URL','')
    if not original:pytest.skip('Requires isolated PostgreSQL CI database')
    parsed=make_url(original)
    if parsed.host not in ('127.0.0.1','localhost') or not any(s in (parsed.database or '') for s in ('test','ci')):
        pytest.skip('Only loopback test/ci databases are permitted')
    from app.nexus.db import engine
    from alembic.config import Config
    from alembic import command
    schema='mcp_migration_test_'+uuid.uuid4().hex[:12]
    with engine(original).begin() as db:
        db.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        db.execute(text('CREATE SCHEMA '+schema))
    monkeypatch.setenv('NEXUS_DATABASE_URL',original+'?options=-csearch_path%3D'+schema+',public')
    try:
        cfg=Config('alembic-nexus.ini')
        command.upgrade(cfg,'head')
        assert inspect(engine()).has_table('mcp_connections')
        with engine().begin() as db:db.execute(text('DROP TABLE '+schema+'.mcp_connections'))
        command.stamp(cfg,'0004_answer_hint')
        command.upgrade(cfg,'head')
        assert inspect(engine()).has_table('mcp_connections')
    finally:
        engine().dispose()
        with engine(original).begin() as db:db.execute(text('DROP SCHEMA '+schema+' CASCADE'))
