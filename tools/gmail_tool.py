import os
import base64
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()


# =========================================================
# GMAIL CONFIGURATION
# =========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


# =========================================================
# CONNECT TO GMAIL
# =========================================================

def get_gmail_service():
    required = {
        "GOOGLE_REFRESH_TOKEN": os.getenv("GOOGLE_REFRESH_TOKEN"),
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing Gmail configuration: "
            + ", ".join(missing)
        )

    credentials = Credentials(
        token=None,
        refresh_token=required["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required["GOOGLE_CLIENT_ID"],
        client_secret=required["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )


# =========================================================
# EXTRACT EMAIL BODY
# =========================================================

def extract_body(payload):
    """
    Extract plain-text body recursively from Gmail payload.
    """

    body_data = payload.get("body", {}).get("data")

    if body_data:
        try:
            return base64.urlsafe_b64decode(
                body_data
            ).decode(
                "utf-8",
                errors="ignore"
            )
        except Exception:
            return ""

    parts = payload.get("parts", [])

    for part in parts:

        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")

            if data:
                try:
                    return base64.urlsafe_b64decode(
                        data
                    ).decode(
                        "utf-8",
                        errors="ignore"
                    )
                except Exception:
                    pass

        nested_body = extract_body(part)

        if nested_body:
            return nested_body

    return ""


def extract_html_body(payload):
    """Extract the original HTML body recursively when available."""

    if payload.get("mimeType") == "text/html":
        body_data = payload.get("body", {}).get("data")

        if body_data:
            try:
                return base64.urlsafe_b64decode(body_data).decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                return ""

    for part in payload.get("parts", []):
        html_body = extract_html_body(part)

        if html_body:
            return html_body

    return ""


def extract_inline_images(gmail_service, message_id, payload):
    """Return inline Gmail images as CID-to-data-URL replacements."""

    images = {}

    def walk_parts(parts):
        for part in parts:
            mime_type = part.get("mimeType", "")
            headers = {
                header.get("name", "").lower(): header.get("value", "")
                for header in part.get("headers", [])
            }
            content_id = headers.get("content-id", "").strip("<>")

            if content_id and mime_type.startswith("image/"):
                image_data = part.get("body", {}).get("data")

                if not image_data and part.get("body", {}).get("attachmentId"):
                    try:
                        attachment = (
                            gmail_service.users()
                            .messages()
                            .attachments()
                            .get(
                                userId="me",
                                messageId=message_id,
                                id=part["body"]["attachmentId"],
                            )
                            .execute()
                        )
                        image_data = attachment.get("data")
                    except Exception:
                        image_data = None

                if image_data:
                    images[content_id] = (
                        f"data:{mime_type};base64,{image_data}"
                    )

            walk_parts(part.get("parts", []))

    walk_parts(payload.get("parts", []))
    return images


# =========================================================
# FETCH UNREAD EMAILS
# =========================================================

def get_unread_emails(gmail_service=None):

    try:
        gmail_service = (
            gmail_service
            if gmail_service
            else get_gmail_service()
        )

        results = (
            gmail_service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["UNREAD"],
                maxResults=10
            )
            .execute()
        )

    except Exception as e:
        print("Gmail API Error:", e)
        return []

    messages = results.get("messages", [])
    emails = []

    for msg in messages:

        try:
            message = (
                gmail_service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="full"
                )
                .execute()
            )

        except Exception as e:
            print(
                f"Error fetching message "
                f"{msg.get('id', 'unknown')}: {e}"
            )
            continue

        subject = ""
        sender = ""

        headers = (
            message
            .get("payload", {})
            .get("headers", [])
        )

        for header in headers:
            name = header.get("name", "")
            value = header.get("value", "")

            if name.lower() == "subject":
                subject = value

            elif name.lower() == "from":
                sender = value

        payload = message.get("payload", {})
        body = extract_body(payload)
        html_body = extract_html_body(payload)

        for content_id, image_url in extract_inline_images(
            gmail_service,
            msg["id"],
            payload,
        ).items():
            html_body = html_body.replace(
                f"cid:{content_id}",
                image_url,
            )

        email_data = {
            "id": msg["id"],
            "sender": sender,
            "subject": subject,
            "snippet": message.get("snippet", ""),
        }

        if body:
            email_data["body"] = body

        if html_body:
            email_data["html_body"] = html_body

        emails.append(email_data)

    return emails


# =========================================================
# CREATE GMAIL DRAFT
# =========================================================

def create_draft(service, to, subject, body):

    message = MIMEText(body)

    message["To"] = to

    if subject.lower().startswith("re:"):
        message["Subject"] = subject
    else:
        message["Subject"] = "Re: " + subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    draft = {
        "message": {
            "raw": raw_message
        }
    }

    return (
        service.users()
        .drafts()
        .create(
            userId="me",
            body=draft
        )
        .execute()
    )


# =========================================================
# ADD LABEL TO EMAIL
# =========================================================

def add_label(service, message_id, label_id):

    return (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={
                "addLabelIds": [label_id]
            }
        )
        .execute()
    )