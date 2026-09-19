import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

client = None

if API_KEY:
    client = genai.Client(api_key=API_KEY)


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

    # If Gemini API is not configured, use fallback
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
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        result = response.text.strip()

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
        print("Gemini error:", e)
        return fallback