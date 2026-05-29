"""Supabase client factory (service-role — server side only)."""
from functools import lru_cache
from supabase import Client, create_client
from app.core.config import settings

def get_client() -> Client:
    """Return a cached service-role Supabase client.

    The service-role key bypasses RLS and must never be exposed to the
    browser. Used only by the FastAPI backend and the Celery worker.
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError(
            "Supabase is not configured: set PP_SUPABASE_URL and PP_SUPABASE_SERVICE_KEY"
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)
