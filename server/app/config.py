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

    # Add-on widgets (phase 5)
    # Which widget fills the bottom-left zone: week | life | weekofyear | yearprogress | countdown | quarter
    bottom_left_widget: str = os.getenv("BOTTOM_LEFT_WIDGET", "week")
    birthdate: str = os.getenv("BIRTHDATE", "")        # YYYY-MM-DD, for life-in-weeks
    life_years: int = int(os.getenv("LIFE_YEARS", "90"))

    # Countdown widget (phase 10) — your marked events only, as "label:YYYY-MM-DD"
    # entries separated by ';'. Shown when BOTTOM_LEFT_WIDGET=countdown.
    countdowns: str = os.getenv("COUNTDOWNS", "")

    # Calendar integration (phase 6) — personal .ics → Now/Next header banner.
    # Empty URL disables the feature (banner hides, poller never starts).
    calendar_ics_url: str = os.getenv("CALENDAR_ICS_URL", "")
    calendar_tz: str = os.getenv("CALENDAR_TZ", "UTC")  # IANA, e.g. America/Los_Angeles
    calendar_poll_minutes: int = int(os.getenv("CALENDAR_POLL_MINUTES", "15"))
    calendar_render_tick_minutes: int = int(os.getenv("CALENDAR_RENDER_TICK_MINUTES", "5"))

    # Weather integration (phase 7) — Open-Meteo → header icon + temp + high/low.
    # Auto-detects location by IP unless WEATHER_LAT/WEATHER_LON are both set.
    weather_enabled: bool = os.getenv("WEATHER_ENABLED", "true").lower() != "false"
    weather_lat: str = os.getenv("WEATHER_LAT", "")
    weather_lon: str = os.getenv("WEATHER_LON", "")
    weather_units: str = os.getenv("WEATHER_UNITS", "fahrenheit")  # fahrenheit | celsius
    weather_poll_minutes: int = int(os.getenv("WEATHER_POLL_MINUTES", "30"))

    # Sunday weekly-review mode — on Sundays, swap the bottom-left zone to a
    # review view (wins/misses + next-week focus). Reverts to bottom_left_widget
    # Mon–Sat. Set SUNDAY_REVIEW=false to disable.
    sunday_review: bool = os.getenv("SUNDAY_REVIEW", "true").lower() != "false"

    # Core daily tick — an always-on re-render so the date advances and Sunday
    # mode activates even with all integrations (calendar/weather) disabled.
    daily_tick_minutes: int = int(os.getenv("DAILY_TICK_MINUTES", "60"))

    # Moon phase (phase 10) — footer segment with named phase + drawn glyph,
    # computed offline via ephem. Set MOON_ENABLED=false to hide.
    moon_enabled: bool = os.getenv("MOON_ENABLED", "true").lower() != "false"

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "dashboard.db")

    @property
    def png_path(self) -> str:
        return os.path.join(self.data_dir, "dashboard.png")


config = Config()
