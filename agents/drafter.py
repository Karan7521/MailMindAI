import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
client = genai.Client(api_key=API_KEY) if API_KEY else None


def draft_reply(subject, body):

    fallback_reply = (
        "Thank you for your email. "
        "I have received your message and will get back to you shortly."
    )

    if client is None:
        return fallback_reply

    prompt = f"""
Write a short and professional reply to this email.

Subject:
{subject}

Email:
{body}

Rules:
- Return only the email reply.
- Keep it professional.
- Keep it concise.
"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        if response.text:
            return response.text.strip()

        return fallback_reply

    except Exception as e:
        print("Gemini API error:", e)
        return fallback_reply