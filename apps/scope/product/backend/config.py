"""
Scope Backend Configuration
============================

Central configuration for the Leo Scope backend.
Loads from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from core import load_env_files

load_env_files()


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # =========================================================================
    # Server
    # =========================================================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000  # Standard backend port
    DEBUG: bool = True
    
    # =========================================================================
    # Database (Supabase) — Leo project: yrkxosaxxgjfwhegopod (EU West)
    # =========================================================================
    SUPABASE_URL: str = os.getenv(
        "SUPABASE_URL",
        os.getenv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321"),
    )
    SUPABASE_ANON_KEY: str = os.getenv(
        "SUPABASE_ANON_KEY",
        os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", ""),
    )
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY",
        os.getenv("SUPABASE_SERVICE_KEY", ""),
    )
    
    # Direct Postgres connection (for asyncpg)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    @property
    def postgres_url(self) -> str:
        """Get Postgres connection URL for asyncpg."""
        if self.DATABASE_URL:
            # Convert postgres:// to postgresql:// if needed
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        # Fallback: Use Supabase REST API instead (no direct DB needed for MVP)
        raise ValueError(
            "DATABASE_URL not set. Get it from Supabase Dashboard → Settings → Database → Connection string (URI)"
        )
    
    # =========================================================================
    # WhatsApp (Meta Cloud API — primary)
    # =========================================================================
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", '')

    # =========================================================================
    # Comms (Resend inbound email webhooks)
    # =========================================================================
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    # Resend uses Svix-style headers: svix-id, svix-timestamp, svix-signature
    # Secret format typically starts with "whsec_..."
    RESEND_WEBHOOK_SECRET: str = os.getenv("RESEND_WEBHOOK_SECRET", "")
    LEO_PROJECT_EMAIL_DOMAIN: str = os.getenv("LEO_PROJECT_EMAIL_DOMAIN", 'example.invalid')
    
    # =========================================================================
    # Voice STT (optional cloud — faster than local Whisper)
    # =========================================================================
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    HUGGINGFACE_HUB_TOKEN: str = os.getenv("HUGGINGFACE_HUB_TOKEN", "")
    HF_WHISPER_MODEL: str = os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")

    # =========================================================================
    # Twilio — Voice SDK caller (internal sales dialer)
    # =========================================================================
    TWILIO_ACCOUNT_SID:    str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN:     str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_TWIML_APP_SID:  str = os.getenv("TWILIO_TWIML_APP_SID", "")
    TWILIO_API_KEY_SID:    str = os.getenv("TWILIO_API_KEY_SID", "")
    TWILIO_API_KEY_SECRET: str = os.getenv("TWILIO_API_KEY_SECRET", "")

    # =========================================================================
    # Contractor Discovery — Cold Outreach Sales Engine
    # =========================================================================
    OUTREACH_TARGET_PER_JOB: int = int(os.getenv("OUTREACH_TARGET_PER_JOB", "25"))
    OUTREACH_MAX_DAILY: int = int(os.getenv("OUTREACH_MAX_DAILY", "80"))
    OUTREACH_STAGGER_SECONDS: int = int(os.getenv("OUTREACH_STAGGER_SECONDS", "8"))
    OUTREACH_FOLLOWUP_1_HOURS: int = int(os.getenv("OUTREACH_FOLLOWUP_1_HOURS", "48"))
    OUTREACH_FOLLOWUP_2_HOURS: int = int(os.getenv("OUTREACH_FOLLOWUP_2_HOURS", "120"))
    OUTREACH_FOUNDER_PHONE: str = os.getenv("OUTREACH_FOUNDER_PHONE", '')

    # =========================================================================
    # Stripe Connect
    # =========================================================================
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    # Test-mode keys for sandbox (sk_test_... / whsec_test...)
    STRIPE_SECRET_KEY_TEST: str = os.getenv("STRIPE_SECRET_KEY_TEST", "")
    STRIPE_WEBHOOK_SECRET_TEST: str = os.getenv("STRIPE_WEBHOOK_SECRET_TEST", "")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")

    # =========================================================================
    # CORS
    # =========================================================================
    CORS_ORIGINS: list[str] = [
        "*",  # Allow all origins for development (file://, localhost:8080, etc.)
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",  # Lean MVP frontend
        "http://localhost:8080",  # Static file server
        "https://*.vercel.app",
    ]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()


# Quick access functions
def get_supabase_url() -> str:
    return settings.SUPABASE_URL


def get_supabase_key() -> str:
    """Get service role key (preferred) or anon key."""
    return settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY


# Debug logging
if settings.DEBUG:
    print(f"[Config] Loaded settings:")
    print(f"  - SUPABASE_URL: {settings.SUPABASE_URL[:40]}...")
    print(f"  - WHATSAPP: {'✓' if settings.WHATSAPP_TOKEN else '✗'}")
    print(f"  - GROQ_STT: {'✓' if settings.GROQ_API_KEY else '✗'}")
    print(f"  - HF_STT: {'✓' if (settings.HF_TOKEN or settings.HUGGINGFACE_HUB_TOKEN) else '✗'}")

