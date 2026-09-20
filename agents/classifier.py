import os
from dotenv import load_dotenv
from llm_service import generate_text, get_llm_model

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", "gemini-1.5-flash"))
client = get_llm_model()


def classify_email(subject, body):

    # Fallback classification
    text = (subject + " " + body).lower()

    if any(word in text for word in [
        "security", "otp", "password", "alert", "verify"
    ]):
        fallback = "Urgent"

    elif any(word in text for word in [
        "unsubscribe", "newsletter", "offer", "sale", "discount"
    ]):
        fallback = "Newsletter"

    elif any(word in text for word in [
        "win", "lottery", "free money", "crypto"
    ]):
        fallback = "Spam"

    else:
        fallback = "Needs Reply"

    if client is None:
        return fallback

    prompt = f"""
Classify this email into EXACTLY ONE category:

Urgent
Newsletter
Spam
Needs Reply

Subject:
{subject}

Body:
{body}

Return ONLY the category name.
"""

    try:
        result = generate_text(prompt, fallback=fallback)

        categories = [
            "Urgent",
            "Newsletter",
            "Spam",
            "Needs Reply"
        ]

        for category in categories:
            if category.lower() in result.lower():
                return category

        return fallback

    except Exception as e:
        print("LLM error:", e)
        return fallback