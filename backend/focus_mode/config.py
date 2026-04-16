from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_BLOCKED_DOMAINS = (
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
    "cdninstagram.com",
    "facebook.com",
    "www.facebook.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "youtube.com",
    "www.youtube.com",
    "web.whatsapp.com",
    "discord.com",
    "www.discord.com",
    "reddit.com",
    "www.reddit.com",
)


@dataclass
class FocusModeConfig:
    db_path: Path = field(default_factory=lambda: Path(__file__).resolve().with_name("focus_mode.db"))
    blocked_domains: tuple[str, ...] = DEFAULT_BLOCKED_DOMAINS
    windows_hosts_path: Path = Path(r"C:\Windows\System32\drivers\etc\hosts")
    hosts_marker_start: str = "# focus-mode start"
    hosts_marker_end: str = "# focus-mode end"
    loopback_ip: str = "127.0.0.1"
