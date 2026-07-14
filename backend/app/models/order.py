# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# [RCF:PROTECTED]
class Order(Base):
    """A committed sale with delivery lifecycle.

    Distinct from Deal (a pipeline opportunity that may never close): an Order
    is the fulfilment record — line items, a denormalised `total` recomputed
    from those items, and a delivery `status` that moves through a fixed graph
    (see ALLOWED_TRANSITIONS in the router). Status history is written to the
    `activities` timeline, not stored here.
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    total: Mapped[float] = mapped_column(Float, default=0.0)  # denormalised Σ line_total
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # marketing attribution
    campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        cascade="all, delete-orphan",
        back_populates="order",
        lazy="selectin",
    )


# [RCF:PROTECTED]
class OrderItem(Base):
    """One line on an order. Snapshots product name + unit price at creation so
    later catalog edits never mutate a placed order."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
