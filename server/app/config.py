"""Central config, loaded from environment / .env."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    vision_provider: str = os.getenv("VISION_PROVIDER", "anthropic")
    vision_model: str = os.getenv("VISION_MODEL", "claude-opus-4-8")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    inbox_dir: str = os.getenv("INBOX_DIR", "/data/inbox")
    data_dir: str = os.getenv("DATA_DIR", "/data")

    panel_width: int = int(os.getenv("PANEL_WIDTH", "2560"))
    panel_height: int = int(os.getenv("PANEL_HEIGHT", "1440"))

    api_port: int = int(os.getenv("API_PORT", "8080"))

    # Voice write-back bot (phase 4, optional)
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "dashboard.db")

    @property
    def png_path(self) -> str:
        return os.path.join(self.data_dir, "dashboard.png")


config = Config()
