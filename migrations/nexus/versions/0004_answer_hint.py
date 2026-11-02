"""Store an optional student-facing hint that is not used for grading."""
from alembic import op
from sqlalchemy import inspect

revision='0004_answer_hint'
down_revision='0003_chunk_options'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    if 'answer_hint' not in {column['name'] for column in inspect(connection).get_columns('assignments')}:
        op.execute("ALTER TABLE assignments ADD COLUMN answer_hint TEXT NOT NULL DEFAULT ''")


def downgrade():
    raise RuntimeError('Restore an approved database backup instead of destructive downgrade')
