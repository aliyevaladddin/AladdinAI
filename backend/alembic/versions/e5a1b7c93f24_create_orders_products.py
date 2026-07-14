# NOTICE: This file is protected under RCF-PL
"""create products, orders, order_items tables

Revision ID: e5a1b7c93f24
Revises: c1d2e3f4a5b6
Create Date: 2026-07-13 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5a1b7c93f24'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    # Guard: skip any table already present (dialect-agnostic; safe on both the
    # Postgres CI run and any environment where a table was created out of band).
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if 'products' not in existing:
        op.create_table(
            'products',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('sku', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('price', sa.Float(), nullable=False, server_default='0'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_products_user_id', 'products', ['user_id'])
        op.create_index('ix_products_sku', 'products', ['sku'])

    if 'orders' not in existing:
        op.create_table(
            'orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('contact_id', sa.Integer(), nullable=False),
            sa.Column('deal_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
            sa.Column('total', sa.Float(), nullable=False, server_default='0'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
            sa.Column('assigned_agent_id', sa.Integer(), nullable=True),
            sa.Column('source', sa.String(length=100), nullable=True),
            sa.Column('campaign', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
            sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_orders_user_id', 'orders', ['user_id'])
        op.create_index('ix_orders_contact_id', 'orders', ['contact_id'])
        op.create_index('ix_orders_status', 'orders', ['status'])

    if 'order_items' not in existing:
        op.create_table(
            'order_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=True),
            sa.Column('product_name', sa.String(length=255), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('unit_price', sa.Float(), nullable=False, server_default='0'),
            sa.Column('line_total', sa.Float(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])


# [RCF:PROTECTED]
def downgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
