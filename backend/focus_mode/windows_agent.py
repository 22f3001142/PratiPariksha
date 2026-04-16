import ctypes
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import FocusModeConfig


@dataclass
class AgentResult:
    applied: bool
    changed_hosts_file: bool = False
    changed_notifications: bool = False
    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "applied": self.applied,
            "changed_hosts_file": self.changed_hosts_file,
            "changed_notifications": self.changed_notifications,
            "actions": self.actions,
            "warnings": self.warnings,
        }


class WindowsFocusAgent:
    def __init__(self, config: FocusModeConfig):
        self.config = config

    def apply(self, blocked_domains: list[str], commit: bool = False) -> AgentResult:
        result = AgentResult(applied=False)
        if not self._is_windows():
            result.warnings.append("Windows controls were skipped because this agent is designed for Windows.")
            return result

        hosts_block = self._build_hosts_block(blocked_domains)
        result.actions.append("Block distracting domains such as Instagram through the Windows hosts file.")
        result.actions.append("Quiet Windows toast notifications during the focus session.")

        if not commit:
            result.warnings.append("Dry run only. Pass commit=True when embedding to actually apply OS-level controls.")
            return result

        if not self._is_admin():
            result.warnings.append("Administrator access is required to update the hosts file.")
        else:
            self._write_hosts_block(hosts_block)
            result.changed_hosts_file = True

        notifications_changed = self._set_toast_notifications(enabled=False)
        result.changed_notifications = notifications_changed
        if not notifications_changed:
            result.warnings.append("Windows notification mute could not be confirmed on this device.")

        result.applied = result.changed_hosts_file or result.changed_notifications
        return result

    def release(self, commit: bool = False) -> AgentResult:
        result = AgentResult(applied=False)
        if not self._is_windows():
            result.warnings.append("Windows controls were skipped because this agent is designed for Windows.")
            return result

        result.actions.append("Restore the hosts file after the focus session ends.")
        result.actions.append("Re-enable Windows toast notifications.")

        if not commit:
            result.warnings.append("Dry run only. Pass commit=True when embedding to actually release OS-level controls.")
            return result

        if self._is_admin():
            self._remove_hosts_block()
            result.changed_hosts_file = True
        else:
            result.warnings.append("Administrator access is required to restore hosts file entries automatically.")

        notifications_changed = self._set_toast_notifications(enabled=True)
        result.changed_notifications = notifications_changed
        if not notifications_changed:
            result.warnings.append("Windows notification restore could not be confirmed on this device.")

        result.applied = result.changed_hosts_file or result.changed_notifications
        return result

    @staticmethod
    def _is_windows() -> bool:
        return str(Path.home().drive).upper().startswith("C:")

    @staticmethod
    def _is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _build_hosts_block(self, blocked_domains: list[str]) -> str:
        lines = [self.config.hosts_marker_start]
        for domain in blocked_domains:
            lines.append(f"{self.config.loopback_ip} {domain}")
        lines.append(self.config.hosts_marker_end)
        return "\n".join(lines) + "\n"

    def _write_hosts_block(self, hosts_block: str) -> None:
        hosts_path = self.config.windows_hosts_path
        current = hosts_path.read_text(encoding="utf-8", errors="ignore") if hosts_path.exists() else ""
        cleaned = self._strip_existing_hosts_block(current).rstrip()
        next_content = f"{cleaned}\n\n{hosts_block}" if cleaned else hosts_block
        hosts_path.write_text(next_content, encoding="utf-8")

    def _remove_hosts_block(self) -> None:
        hosts_path = self.config.windows_hosts_path
        if not hosts_path.exists():
            return
        current = hosts_path.read_text(encoding="utf-8", errors="ignore")
        hosts_path.write_text(self._strip_existing_hosts_block(current).rstrip() + "\n", encoding="utf-8")

    def _strip_existing_hosts_block(self, text: str) -> str:
        start = self.config.hosts_marker_start
        end = self.config.hosts_marker_end
        if start not in text or end not in text:
            return text
        prefix, remainder = text.split(start, 1)
        _, suffix = remainder.split(end, 1)
        return (prefix + suffix).strip()

    @staticmethod
    def _set_toast_notifications(enabled: bool) -> bool:
        value = "1" if enabled else "0"
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\PushNotifications' -Force | Out-Null; "
                f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\PushNotifications' -Name 'ToastEnabled' -Type DWord -Value {value}"
            ),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
            return completed.returncode == 0
        except Exception:
            return False
