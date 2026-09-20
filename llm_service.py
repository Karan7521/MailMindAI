import os
from dotenv import load_dotenv

load_dotenv()


def get_llm_model():
    """Return a configured Gemini model when an API key is present."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai

        model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-1.5-flash"
        client = genai.Client(api_key=api_key)
        return client.models
    except Exception:
        return None


def generate_text(prompt, fallback=""):
    """Generate text via the configured LLM or return the fallback."""
    model = get_llm_model()
    if model is None:
        return fallback

    try:
        response = model.generate_content(
            model=os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-1.5-flash",
            contents=prompt,
        )
        return getattr(response, "text", "") or fallback
    except Exception:
        return fallback
