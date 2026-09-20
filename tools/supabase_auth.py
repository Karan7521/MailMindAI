import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseAuthError(RuntimeError):
    """Raised when Supabase authentication cannot complete."""

    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


_supabase_client = None


def get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
    ).strip()

    if not supabase_url or not supabase_key:
        raise SupabaseAuthError(
            "Supabase is not configured. Add SUPABASE_URL and "
            "SUPABASE_ANON_KEY to your .env file."
        )

    parsed_url = urlparse(supabase_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise SupabaseAuthError("SUPABASE_URL must be a full project URL.")

    try:
        _supabase_client = create_client(supabase_url, supabase_key)
    except Exception as error:
        raise SupabaseAuthError(_format_error(error)) from error
    return _supabase_client


def sign_in(email: str, password: str):
    try:
        response = get_supabase_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as error:
        raise SupabaseAuthError(
            _format_error(error), _retry_after_seconds(error)
        ) from error

    if not response.user:
        raise SupabaseAuthError("Email or password is incorrect.")
    return response.user


def request_password_reset(email: str) -> None:
    try:
        get_supabase_client().auth.reset_password_for_email(email)
    except Exception as error:
        raise SupabaseAuthError(
            _format_error(error), _retry_after_seconds(error)
        ) from error


def sign_up(email: str, password: str):
    try:
        response = get_supabase_client().auth.sign_up(
            {"email": email, "password": password}
        )
    except Exception as error:
        raise SupabaseAuthError(
            _format_error(error), _retry_after_seconds(error)
        ) from error

    if not response.user:
        raise SupabaseAuthError("Unable to create the account.")
    return response.user, response.session


def sign_out() -> None:
    try:
        get_supabase_client().auth.sign_out()
    except Exception as error:
        raise SupabaseAuthError(_format_error(error)) from error


def _format_error(error: Exception) -> str:
    message = str(error).strip()
    lowered = message.lower()
    if "invalid login credentials" in lowered:
        return "Email or password is incorrect."
    if "email not confirmed" in lowered:
        return "Confirm your email address before logging in."
    if "user already registered" in lowered:
        return "This email is already registered. Log in instead."
    if "error sending confirmation email" in lowered:
        return (
            "Supabase could not send the confirmation email. Check SMTP settings "
            "or disable email confirmation for local development."
        )
    if "rate limit" in lowered or "security purposes" in lowered:
        retry_after = _retry_after_seconds(error)
        return (
            f"Too many requests. Please wait {retry_after} seconds and try again."
            if retry_after
            else "Too many requests. Please wait and try again."
        )
    return message or "Supabase authentication failed."


def _retry_after_seconds(error: Exception) -> int | None:
    match = re.search(r"after\s+(\d+)\s+seconds?", str(error), re.IGNORECASE)
    return int(match.group(1)) if match else None
