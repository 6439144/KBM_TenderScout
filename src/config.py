"""
Configuration loader for KBM Tender Scout.
Loads YAML configuration and overrides with environment settings without hardcoding.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path("config/config.example.yaml")
USER_CONFIG_PATH = Path("config/config.yaml")

class AppConfig(BaseModel):
    name: str = "KBM Tender Monitoring Agent"
    version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

class ComplianceConfig(BaseModel):
    automation_permitted: bool = False
    enforce_human_presence_until_permitted: bool = True

class RateLimitingConfig(BaseModel):
    min_delay_seconds: float = 3.0
    max_delay_seconds: float = 8.0
    max_pages_per_run: int = 20
    max_retries_per_day: int = 1

class BrowserConfig(BaseModel):
    headless: bool = True
    timeout_ms: int = 30000
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (KBM-TenderScout-Reader)"
    )

class PortalAuthConfig(BaseModel):
    username_secret: str
    password_secret: str
    account_type: str = "shared"
    has_otp: bool = False

class PortalConfig(BaseModel):
    enabled: bool = True
    name: str
    base_url: str
    login_url: str
    tenders_url: str
    auth: PortalAuthConfig
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)

class CollectConfig(BaseModel):
    notice_types: List[str] = [
        "tender", "practice", "prequal", "addendum", "cancellation", "award"
    ]
    backfill_days: int = 30
    download_attachments: bool = False
    attachments_dir: str = "data/attachments"

class FilterConfig(BaseModel):
    enabled: bool = True
    mode: str = "tag_only"
    store_unmatched: bool = True
    keywords_ar: List[str] = []
    keywords_en: List[str] = []

class LLMConfig(BaseModel):
    enabled: bool = False
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.0
    timeout_seconds: int = 15
    max_retries: int = 2
    strip_sensitive_fields: bool = True

class ClassificationConfig(BaseModel):
    clients_master_file: str = "data/clients.csv"
    sectors_file: str = "data/sectors.yaml"
    clients_pending_file: str = "data/clients_pending.csv"
    confidence_threshold: float = 0.75
    llm: LLMConfig = Field(default_factory=LLMConfig)

class OutputConfig(BaseModel):
    translate_titles: bool = False

class ExcelConfig(BaseModel):
    mode: str = "both"
    output_dir: str = "output/reports"
    daily_filename_pattern: str = "KBM_Tenders_{date}.xlsx"
    latest_filename: str = "KBM_Tenders_Latest.xlsx"
    closing_soon_days: int = 7
    sheets: List[str] = [
        "summary", "new_today", "all_open", "by_sector",
        "by_client", "needs_review", "run_log"
    ]

class ScheduleConfig(BaseModel):
    cron: str = "0 6 * * 0-4"
    timezone: str = "Asia/Kuwait"
    active_days: List[str] = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

class SecretsConfig(BaseModel):
    provider: str = "env"

class RootConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    portals: Dict[str, PortalConfig]
    collect: CollectConfig = Field(default_factory=CollectConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    excel: ExcelConfig = Field(default_factory=ExcelConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)

def load_config(config_path: Optional[Path] = None) -> RootConfig:
    """Loads configuration from YAML file with fallback to example file."""
    path = config_path or (USER_CONFIG_PATH if USER_CONFIG_PATH.exists() else DEFAULT_CONFIG_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return RootConfig(**data)
