from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import encrypt
from app.database import get_db
from app.models.email_account import EmailAccount
from app.models.user import User
from app.schemas.channels import EmailAccountCreate, EmailAccountResponse, EmailAccountUpdate
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
        password_encrypted=encrypt(body.password) if body.password else None,
        access_token_encrypted=encrypt(body.access_token) if body.access_token else None,
        refresh_token_encrypted=encrypt(body.refresh_token) if body.refresh_token else None,
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


@router.put("/{account_id}", response_model=EmailAccountResponse)
async def update_email(account_id: int, body: EmailAccountUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    if body.email is not None:
        account.email = body.email
    if body.imap_host is not None:
        account.imap_host = body.imap_host
    if body.imap_port is not None:
        account.imap_port = body.imap_port
    if body.smtp_host is not None:
        account.smtp_host = body.smtp_host
    if body.smtp_port is not None:
        account.smtp_port = body.smtp_port
    if body.password is not None:
        account.password_encrypted = encrypt(body.password)
    account.status = "disconnected"  # reset status after edit — require re-test
    await db.commit()
    await db.refresh(account)
    return account


class SendEmailBody(BaseModel):
    to_email: str
    subject: str
    body: str
    contact_id: int | None = None


@router.post("/{account_id}/send")
async def send_email_endpoint(account_id: int, payload: SendEmailBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    from app.services.email_service import send_email
    try:
        await send_email(db, account, payload.to_email, payload.subject, payload.body, payload.contact_id)
        return {"status": "sent", "message": f"Email sent to {payload.to_email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.delete("/{account_id}", status_code=204)
async def delete_email(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    await db.delete(account)
    await db.commit()

