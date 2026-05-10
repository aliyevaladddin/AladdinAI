import asyncio
import email
import email.header
import imaplib
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt
from app.database import async_session
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.email_account import EmailAccount


def _decode_mime(value: str) -> str:
    """Decode RFC 2047 encoded-word strings like =?UTF-8?B?...?= or =?UTF-8?Q?...?="""
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(part)
    return " ".join(decoded).strip()


def _parse_email_address(header: str) -> tuple[str, str]:
    """Parse 'Name <email@example.com>' → (name, email)"""
    header = _decode_mime(header)
    if "<" in header:
        parts = header.split("<")
        name = parts[0].strip().strip('"')
        addr = parts[1].rstrip(">").strip()
        return name, addr
    return "", header.strip()


async def test_email_connection(account: EmailAccount) -> tuple[bool, str]:
    if account.provider == "imap":
        return await _test_imap(account)
    return False, f"OAuth for {account.provider} not yet implemented — use IMAP for now"


async def _test_imap(account: EmailAccount) -> tuple[bool, str]:
    try:
        password = decrypt(account.password_encrypted or "")
        def _connect():
            host = account.imap_host or "imap.gmail.com"
            port = account.imap_port or 993
            m = imaplib.IMAP4_SSL(host, port)
            m.login(account.email, password)
            m.logout()
            return True
        await asyncio.to_thread(_connect)
        return True, "IMAP connection successful"
    except Exception as e:
        return False, str(e)


def _detect_sent_folder(m: imaplib.IMAP4_SSL) -> str | None:
    """Try common Sent folder names across providers."""
    candidates = [
        "[Gmail]/Sent Mail", "Sent Items", "Sent", "INBOX.Sent", "sent", "Sent Messages"
    ]
    _, folders = m.list()
    import re
    # IMAP LIST response pattern: (Flags) "Delimiter" FolderName
    # FolderName can be "Quoted" or Unquoted
    pattern = re.compile(r'\((?P<flags>.*?)\)\s+"(?P<delimiter>.*?)"\s+(?P<name>.+)')

    detected_folders = []
    for f in (folders or []):
        if isinstance(f, bytes):
            f = f.decode(errors="ignore")
        match = pattern.search(f)
        if match:
            name = match.group("name").strip()
            # Remove quotes if present
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            detected_folders.append(name)
        else:
            # Fallback for non-standard formats: take everything after the last "
            parts = f.split('"')
            if len(parts) >= 3:
                detected_folders.append(parts[-1].strip())

    for candidate in candidates:
        for df in detected_folders:
            if candidate.lower() == df.lower():
                return df
    return None


async def sync_emails(account_id: int):
    async with async_session() as db:
        result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            return

        # ── Fetch INBOX (incoming) ──────────────────────────────────────
        try:
            inbox_msgs = await _fetch_folder_emails(account, folder="INBOX", limit=30)
        except Exception:
            inbox_msgs = []

        # ── Fetch Sent (outgoing) ───────────────────────────────────────
        try:
            sent_msgs = await _fetch_sent_emails(account, limit=30)
        except Exception:
            sent_msgs = []

        # ── Process incoming ────────────────────────────────────────────
        for msg in inbox_msgs:
            sender_email = msg.get("from_email", "").strip().lower()
            if not sender_email:
                continue

            contact = await _find_contact(db, account.user_id, sender_email)
            await _upsert_activity(db, account, contact.id if contact else None, "email_in", msg)

        # ── Process outgoing ────────────────────────────────────────────
        for msg in sent_msgs:
            to_email = msg.get("to_email", "").strip().lower()
            if not to_email:
                continue

            contact = await _find_contact(db, account.user_id, to_email)
            await _upsert_activity(db, account, contact.id if contact else None, "email_out", msg)

        account.last_synced_at = datetime.now(timezone.utc)
        account.status = "connected"
        await db.commit()


async def _find_contact(db, user_id: int, addr: str) -> Contact | None:
    result = await db.execute(
        select(Contact).where(Contact.user_id == user_id, Contact.email == addr)
    )
    return result.scalar_one_or_none()


async def _upsert_activity(db, account: EmailAccount, contact_id: int | None, activity_type: str, msg: dict):
    """Insert or update activity with robust deduplication."""
    subject = msg.get("subject", "")
    message_id = msg.get("message_id", "")
    
    # 1. Try to find existing by Message-ID if available
    existing_activity = None
    if message_id:
        # We fetch all emails for this user/type/subject and check Message-ID in Python
        # to avoid complex SQLite JSON path issues
        res = await db.execute(
            select(Activity).where(
                and_(
                    Activity.user_id == account.user_id,
                    Activity.subject == subject,
                    Activity.type == activity_type
                )
            )
        )
        for act in res.scalars().all():
            if act.metadata_json and act.metadata_json.get("message_id") == message_id:
                existing_activity = act
                break

    if existing_activity:
        # Update attachments if missing
        meta = dict(existing_activity.metadata_json or {})
        raw_msg = msg.get("_raw")
        if raw_msg and not meta.get("attachments"):
            attachments_meta = _save_attachments(raw_msg, existing_activity.id)
            if attachments_meta:
                meta["attachments"] = attachments_meta
                existing_activity.metadata_json = meta
        return

    # 2. If no message_id match, try subject + type (legacy/fallback)
    # But ONLY if we haven't already found it. 
    # For replies, message_id is unique, so subject matching is only for very old emails.
    
    # Ensure from/to metadata is in json
    metadata_json = {
        "from_name": msg.get("from_name", ""),
        "from_email": msg.get("from_email", ""),
        "to_name": msg.get("to_name", ""),
        "to_email": msg.get("to_email", ""),
        "message_id": message_id,
    }

    activity = Activity(
        user_id=account.user_id,
        contact_id=contact_id,
        type=activity_type,
        channel=account.provider,
        subject=subject,
        content=msg.get("body", "")[:20000],
        metadata_json=metadata_json,
    )
    db.add(activity)
    await db.flush()  # get activity.id

    # Save attachments to disk and store metadata
    raw_msg = msg.get("_raw")
    if raw_msg:
        attachments_meta = _save_attachments(raw_msg, activity.id)
        if attachments_meta:
            updated_meta = dict(activity.metadata_json or {})
            updated_meta["attachments"] = attachments_meta
            activity.metadata_json = updated_meta


ATTACHMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "media", "attachments")


def _save_attachments(msg: email.message.Message, activity_id: int) -> list[dict]:
    """Extract and save email attachments to disk. Returns list of metadata dicts."""
    saved = []
    import mimetypes
    import uuid
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
            
        content_type = part.get_content_type() or "application/octet-stream"
        filename = part.get_filename()
        
        if not filename:
            # Skip email body parts
            if content_type in ["text/plain", "text/html"]:
                continue
            ext = mimetypes.guess_extension(content_type)
            if ext:
                filename = f"attachment_{uuid.uuid4().hex[:8]}{ext}"
            else:
                continue

        filename = _decode_mime(filename)
        # Sanitize filename
        filename = os.path.basename(filename).replace("/", "_").replace("\\", "_")
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        # Save to disk
        folder = os.path.join(ATTACHMENTS_DIR, str(activity_id))
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, filename)
        with open(file_path, "wb") as f:
            f.write(payload)
        saved.append({
            "filename": filename,
            "content_type": content_type,
            "size": len(payload),
        })
    return saved


async def _fetch_folder_emails(account: EmailAccount, folder: str, limit: int = 50) -> list[dict]:
    """Fetch emails from a given IMAP folder. Extracts From/Subject/Body."""
    password = decrypt(account.password_encrypted or "")

    def _fetch():
        host = account.imap_host or "imap.gmail.com"
        port = account.imap_port or 993
        m = imaplib.IMAP4_SSL(host, port)
        m.login(account.email, password)
        m.select(folder)

        _, data = m.search(None, "ALL")
        ids = data[0].split()[-limit:]
        messages = []

        for eid in ids:
            _, msg_data = m.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_name, from_email = _parse_email_address(msg.get("From", ""))
            to_name, to_email = _parse_email_address(msg.get("To", ""))
            body = _extract_body(msg)

            messages.append({
                "from_name": from_name,
                "from_email": from_email,
                "to_name": to_name,
                "to_email": to_email,
                "subject": _decode_mime(msg.get("Subject", "")),
                "body": body,
                "message_id": msg.get("Message-ID", "").strip(),
                "_raw": msg,  # passed to _save_attachments
            })

        m.logout()
        return messages

    return await asyncio.to_thread(_fetch)


async def _fetch_sent_emails(account: EmailAccount, limit: int = 50) -> list[dict]:
    """Fetch emails from the Sent folder, auto-detecting folder name."""
    password = decrypt(account.password_encrypted or "")

    def _fetch():
        host = account.imap_host or "imap.gmail.com"
        port = account.imap_port or 993
        m = imaplib.IMAP4_SSL(host, port)
        m.login(account.email, password)

        sent_folder = _detect_sent_folder(m)
        if not sent_folder:
            m.logout()
            return []

        status, _ = m.select(sent_folder)
        if status != "OK":
            m.logout()
            return []

        _, data = m.search(None, "ALL")
        ids = data[0].split()[-limit:]
        messages = []

        for eid in ids:
            _, msg_data = m.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_name, from_email = _parse_email_address(msg.get("From", ""))
            to_name, to_email = _parse_email_address(msg.get("To", ""))
            body = _extract_body(msg)

            messages.append({
                "from_name": from_name,
                "from_email": from_email,
                "to_name": to_name,
                "to_email": to_email,
                "subject": _decode_mime(msg.get("Subject", "")),
                "body": body,
                "message_id": msg.get("Message-ID", "").strip(),
                "_raw": msg,
            })

        m.logout()
        return messages

    return await asyncio.to_thread(_fetch)


def _extract_body(msg: email.message.Message) -> str:
    """Extract body from email, prefer text/html over text/plain."""
    html_body = ""
    plain_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            ct = part.get_content_type()
            if ct == "text/plain" and not plain_body:
                plain_body = part.get_payload(decode=True).decode(errors="ignore")
            elif ct == "text/html" and not html_body:
                html_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        body_bytes = msg.get_payload(decode=True)
        if body_bytes:
            plain_body = body_bytes.decode(errors="ignore")
            if msg.get_content_type() == "text/html":
                html_body = plain_body
    return html_body if html_body else plain_body


async def send_email(db: AsyncSession, account: EmailAccount, to_email: str, subject: str, body: str, contact_id: int | None = None):
    """Send email via SMTP and save to database immediately."""
    password = decrypt(account.password_encrypted or "")
    
    # Create local Message-ID for tracking/deduplication
    import uuid
    local_msg_id = f"<local-{uuid.uuid4()}@{account.email.split('@')[-1]}>"

    def _send():
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = account.email
        msg["To"] = to_email
        msg["Message-ID"] = local_msg_id

        host = account.smtp_host or "smtp.gmail.com"
        port = account.smtp_port or 587
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(account.email, password)
            s.send_message(msg)

    await asyncio.to_thread(_send)

    # Save to database immediately so it appears in Sent folder
    activity = Activity(
        user_id=account.user_id,
        contact_id=contact_id,
        type="email_out",
        channel=account.provider,
        subject=subject,
        content=body,
        metadata_json={
            "from_name": "",
            "from_email": account.email,
            "to_name": "",
            "to_email": to_email,
            "message_id": local_msg_id,
        }
    )
    db.add(activity)
    await db.commit()
