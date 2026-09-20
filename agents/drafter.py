import os

from dotenv import load_dotenv
from llm_service import generate_text, get_llm_model

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", "gemini-1.5-flash"))
client = get_llm_model()


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
        reply = generate_text(prompt, fallback=fallback_reply)
        if reply:
            return reply.strip()

        return fallback_reply

    except Exception as e:
        print("LLM API error:", e)
        return fallback_reply