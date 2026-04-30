import asyncio
import email
import imaplib
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from sqlalchemy import select

from app.database import async_session
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.email_account import EmailAccount


async def test_email_connection(account: EmailAccount) -> tuple[bool, str]:
    if account.provider == "imap":
        return await _test_imap(account)
    return False, f"OAuth for {account.provider} not yet implemented — use IMAP for now"


async def _test_imap(account: EmailAccount) -> tuple[bool, str]:
    try:
        def _connect():
            host = account.imap_host or "imap.gmail.com"
            port = account.imap_port or 993
            m = imaplib.IMAP4_SSL(host, port)
            m.login(account.email, account.password_encrypted or "")
            m.logout()
            return True
        await asyncio.to_thread(_connect)
        return True, "IMAP connection successful"
    except Exception as e:
        return False, str(e)


async def sync_emails(account_id: int):
    async with async_session() as db:
        result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return

        try:
            messages = await _fetch_recent_emails(account, limit=20)
        except Exception:
            return

        for msg in messages:
            sender_email = msg.get("from_email")
            if not sender_email:
                continue

            # Find or create contact
            result = await db.execute(
                select(Contact).where(Contact.user_id == account.user_id, Contact.email == sender_email)
            )
            contact = result.scalar_one_or_none()
            if not contact:
                contact = Contact(
                    user_id=account.user_id,
                    name=msg.get("from_name", sender_email),
                    email=sender_email,
                    source="email",
                )
                db.add(contact)
                await db.flush()

            activity = Activity(
                user_id=account.user_id,
                contact_id=contact.id,
                type="email_in",
                channel=account.provider,
                subject=msg.get("subject", ""),
                content=msg.get("body", "")[:2000],
            )
            db.add(activity)

        account.last_synced_at = datetime.now(timezone.utc)
        account.status = "connected"
        await db.commit()


async def _fetch_recent_emails(account: EmailAccount, limit: int = 20) -> list[dict]:
    def _fetch():
        host = account.imap_host or "imap.gmail.com"
        port = account.imap_port or 993
        m = imaplib.IMAP4_SSL(host, port)
        m.login(account.email, account.password_encrypted or "")
        m.select("INBOX")

        _, data = m.search(None, "ALL")
        ids = data[0].split()[-limit:]
        messages = []

        for eid in ids:
            _, msg_data = m.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_header = msg.get("From", "")
            from_name = ""
            from_email = from_header
            if "<" in from_header:
                parts = from_header.split("<")
                from_name = parts[0].strip().strip('"')
                from_email = parts[1].rstrip(">")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            messages.append({
                "from_name": from_name,
                "from_email": from_email,
                "subject": msg.get("Subject", ""),
                "body": body,
            })

        m.logout()
        return messages

    return await asyncio.to_thread(_fetch)


async def send_email(account: EmailAccount, to_email: str, subject: str, body: str):
    def _send():
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = account.email
        msg["To"] = to_email

        host = account.smtp_host or "smtp.gmail.com"
        port = account.smtp_port or 587
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(account.email, account.password_encrypted or "")
            s.send_message(msg)

    await asyncio.to_thread(_send)
