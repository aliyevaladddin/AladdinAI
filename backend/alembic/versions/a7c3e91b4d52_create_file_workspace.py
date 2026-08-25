# NOTICE: This file is protected under RCF-PL
"""create file workspace tables

File Workspace phase 1: spaces (access boundaries), space_members (roles),
folders, files (soft delete), file_versions (append-only immutable
snapshots) and file_events (append-only audit ledger).

Revision ID: a7c3e91b4d52
Revises: f4b8c2d19a37
Create Date: 2026-08-25 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e91b4d52'
down_revision: Union[str, Sequence[str], None] = 'f4b8c2d19a37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ('spaces', 'space_members', 'folders', 'files',
          'file_versions', 'file_events')


def _existing(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


# [RCF:PROTECTED]
def upgrade() -> None:
    have = _existing(op.get_bind())

    if 'spaces' not in have:
        op.create_table(
            'spaces',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('created_by_user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'space_members' not in have:
        op.create_table(
            'space_members',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False,
                      server_default='viewer'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'],
                                    ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('space_id', 'user_id', name='uq_space_member'),
        )
        op.create_index('ix_space_members_user_id', 'space_members', ['user_id'])

    if 'folders' not in have:
        op.create_table(
            'folders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('parent_id', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'],
                                    ondelete='CASCADE'),
            # Self-reference: SET NULL so a deleted subtree root does not
            # orphan its children's rows.
            sa.ForeignKeyConstraint(['parent_id'], ['folders.id'],
                                    ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_folders_space_id', 'folders', ['space_id'])
        op.create_index('ix_folders_parent_id', 'folders', ['parent_id'])

    if 'files' not in have:
        op.create_table(
            'files',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('folder_id', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('mime_type', sa.String(length=255), nullable=True),
            sa.Column('byte_size', sa.Integer(), nullable=False,
                      server_default='0'),
            sa.Column('current_version_no', sa.Integer(), nullable=False,
                      server_default='0'),
            # Logical ref to file_versions.id — no FK on purpose: it would
            # create a files <-> file_versions cycle SQLite cannot create.
            sa.Column('source_version_id', sa.Integer(), nullable=True),
            sa.Column('created_by_user_id', sa.Integer(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'],
                                    ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['folder_id'], ['folders.id'],
                                    ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_files_space_id', 'files', ['space_id'])
        op.create_index('ix_files_folder_id', 'files', ['folder_id'])

    if 'file_versions' not in have:
        op.create_table(
            'file_versions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('file_id', sa.Integer(), nullable=False),
            sa.Column('version_no', sa.Integer(), nullable=False),
            sa.Column('storage_ref', sa.Text(), nullable=False),
            sa.Column('byte_size', sa.Integer(), nullable=False,
                      server_default='0'),
            sa.Column('uploader_user_id', sa.Integer(), nullable=False),
            sa.Column('author_type', sa.String(length=20), nullable=False,
                      server_default='human'),
            sa.Column('agent_run_id', sa.Integer(), nullable=True),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                                    ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['uploader_user_id'], ['users.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('file_id', 'version_no',
                                name='uq_file_version_no'),
        )
        op.create_index('ix_file_versions_file_id', 'file_versions',
                        ['file_id'])

    if 'file_events' not in have:
        op.create_table(
            'file_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('file_id', sa.Integer(), nullable=False),
            sa.Column('event_type', sa.String(length=40), nullable=False),
            sa.Column('actor_type', sa.String(length=20), nullable=False,
                      server_default='human'),
            sa.Column('actor_user_id', sa.Integer(), nullable=True),
            sa.Column('payload', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                                    ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'],
                                    ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_file_events_file_id', 'file_events', ['file_id'])
        op.create_index('ix_file_events_file_created', 'file_events',
                        ['file_id', 'created_at'])


# [RCF:PROTECTED]
def downgrade() -> None:
    for table in TABLES:
        bind = op.get_bind()
        if table in sa.inspect(bind).get_table_names():
            op.drop_table(table)
