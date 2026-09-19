# MailMind AI

MailMind AI is a Streamlit email inbox triage assistant. It connects to Gmail, reads unread messages, classifies them, explains the classification, generates replies, and creates Gmail drafts.

## Features

- Gmail unread inbox sync
- AI-assisted email classification
- Local keyword fallback when Gemini is unavailable
- Category views for urgent, important, reply-needed, spam, newsletters, and general mail
- Search and category filters
- Full email reading with HTML and inline image support
- One-click AI reply generation
- AI-generated mail composer
- Gmail draft creation
- Appearance themes and animated MailMind robot branding
- Clear Workspace reset

## Project Structure

```text
app.py                  Main Streamlit application and UI
streamlit_app.py        Lightweight legacy Streamlit entry point
agents/                 Standalone classifier, reader, and drafter helpers
tools/gmail_tool.py     Gmail authentication, reading, HTML/image extraction, drafts
prompts/                Prompt modules used by earlier agent flows
graph/workflow.py       Reserved workflow layer
oauth.py                OAuth refresh-token generator
generate_refresh_token.py OAuth helper script
utils/parser.py         Parser utility module
requirements.txt        Python dependencies
ARCHITECTURE.md         Detailed system and data-flow explanation
```

## Requirements

- Python 3.10+
- A Google Cloud project with the Gmail API enabled
- Gmail OAuth credentials
- Optional Gemini API key for AI classification and generation

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
GOOGLE_REFRESH_TOKEN=your_refresh_token
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
ABSTRACT_EMAIL_VALIDATION_API_KEY=your_abstract_api_key
```

The optional Abstract API key enables deliverability checks for login and new-user email addresses. Without it, the app still checks the email format locally.

Copy your Google OAuth client file to `credentials.json` only for local development. Generate a refresh token with:

```powershell
python oauth.py
```

The Gmail scopes used by the app are read-only access and compose access.

## Run

```powershell
streamlit run app.py
```

Open the URL shown by Streamlit, usually `http://localhost:8501`.

## Typical Workflow

1. Open MailMind AI.
2. Click **Connect Gmail**.
3. Click **Sync Inbox**.
4. Open **Inbox** and analyze the loaded emails.
5. Review categories and AI explanations.
6. Use **Read Full Mail** or **Instant Reply** on an email.
7. Edit the reply and create a Gmail draft.

HTML emails are previewed in their original format when available. Image-only emails are not sent to text-only summary logic.

## Security Notes

- Never commit `.env`, `credentials.json`, refresh tokens, or API keys.
- Rotate credentials immediately if they are accidentally exposed.
- Gmail content is rendered in an isolated HTML preview, but treat external email HTML as untrusted content.

## Tests and Checks

Run the available tests with:

```powershell
python -m pytest -q
```

For a quick syntax check:

```powershell
python -m compileall -q app.py tools agents graph utils
```
