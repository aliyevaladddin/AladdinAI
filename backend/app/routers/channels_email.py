from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.email_account import EmailAccount
from app.models.user import User
from app.schemas.channels import EmailAccountCreate, EmailAccountResponse
from app.security import get_current_user

router = APIRouter(prefix="/channels/email", tags=["channels"])


@router.get("", response_model=list[EmailAccountResponse])
async def list_emails(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=EmailAccountResponse, status_code=201)
async def create_email(body: EmailAccountCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = EmailAccount(
        user_id=user.id,
        provider=body.provider,
        email=body.email,
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        password_encrypted=body.password,
        access_token_encrypted=body.access_token,
        refresh_token_encrypted=body.refresh_token,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.post("/{account_id}/test")
async def test_email(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")

    from app.services.email_service import test_email_connection
    success, message = await test_email_connection(account)

    if success:
        account.status = "connected"
        await db.commit()

    return {"status": "connected" if success else "error", "message": message}


@router.post("/{account_id}/sync")
async def sync_email(
    account_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")

    from app.services.email_service import sync_emails
    background_tasks.add_task(sync_emails, account.id)

    return {"status": "syncing", "message": "Email sync started in background"}


@router.delete("/{account_id}", status_code=204)
async def delete_email(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    await db.delete(account)
    await db.commit()
