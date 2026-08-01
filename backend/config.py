"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    max_upload_mb: int = 15
    max_pdf_pages_to_image: int = 6
    # Enrich N/A market fields (CMP, market cap, 52-wk range, beta, price history)
    # from yfinance. Best-effort: a lookup/network failure never breaks the report.
    enable_market_data: bool = True

    @property
    def use_mock(self) -> bool:
        """When no API key is present, run deterministic mock extraction."""
        return not self.gemini_api_key.strip()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
