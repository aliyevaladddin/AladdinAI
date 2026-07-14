# NOTICE: This file is protected under RCF-PL
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.crm import ProductCreate, ProductResponse, ProductUpdate
from app.security import get_current_user

router = APIRouter(prefix="/crm/products", tags=["crm"])


# [RCF:PROTECTED]
@router.get("", response_model=list[ProductResponse])
# [RCF:PROTECTED]
async def list_products(
    search: str | None = None,
    active: bool | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Product).where(Product.user_id == user.id)
    if active is not None:
        q = q.where(Product.active == active)
    if search:
        q = q.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(Product.updated_at.desc()))
    return result.scalars().all()


# [RCF:PROTECTED]
@router.post("", response_model=ProductResponse, status_code=201)
# [RCF:PROTECTED]
async def create_product(body: ProductCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dup = await db.execute(
        select(Product).where(Product.user_id == user.id, Product.sku == body.sku)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"SKU '{body.sku}' already exists")
    product = Product(user_id=user.id, **body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


# [RCF:PROTECTED]
@router.get("/{product_id}", response_model=ProductResponse)
# [RCF:PROTECTED]
async def get_product(product_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user.id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# [RCF:PROTECTED]
@router.put("/{product_id}", response_model=ProductResponse)
# [RCF:PROTECTED]
async def update_product(product_id: int, body: ProductUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user.id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = body.model_dump(exclude_unset=True)
    # Guard the per-user SKU uniqueness on rename.
    new_sku = updates.get("sku")
    if new_sku and new_sku != product.sku:
        dup = await db.execute(
            select(Product).where(Product.user_id == user.id, Product.sku == new_sku)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"SKU '{new_sku}' already exists")
    for key, value in updates.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


# [RCF:PROTECTED]
@router.delete("/{product_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_product(product_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user.id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()
