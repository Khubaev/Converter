"""Конфигурация из окружения / .env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DEFAULT_VISION_URL = "https://smarty.mail.ru/api/v1/text/recognize"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class VkVisionSettings:
    """Параметры клиента VK Vision."""

    oauth_token: str
    oauth_provider: str = "mcs"
    api_url: str = _DEFAULT_VISION_URL
    timeout_seconds: float = 60.0

    @property
    def is_configured(self) -> bool:
        return bool(self.oauth_token.strip())


def load_env_file() -> None:
    """Подхватывает .env из корня проекта и из текущей папки."""
    # override=True: значение из .env важнее пустой переменной окружения.
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
    load_dotenv(Path.cwd() / ".env", override=True)


@dataclass(frozen=True, slots=True)
class N8nSettings:
    """Адрес webhook n8n, куда уходит JSON распознанного текста."""

    path: str
    timeout_seconds: float = 30.0

    @property
    def is_configured(self) -> bool:
        return self.path.startswith(("http://", "https://"))


def load_api_docs_enabled() -> bool:
    """True только если API_DOCS_ENABLED явно включён. На рабочем сервере docs закрыты."""
    load_env_file()
    return os.getenv("API_DOCS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def load_job_ttl_seconds() -> int:
    """Срок жизни задания в секундах. По умолчанию 5 минут."""
    load_env_file()
    raw = os.getenv("JOB_TTL_SECONDS", "300").strip() or "300"
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("JOB_TTL_SECONDS должен быть целым числом секунд.") from exc
    if value < 60:
        raise ValueError("JOB_TTL_SECONDS не может быть меньше 60.")
    return value


def load_n8n_settings() -> N8nSettings:
    """Читает PATH_N8N — полный URL приёмника сборки."""
    load_env_file()
    return N8nSettings(path=os.getenv("PATH_N8N", "").strip())


def load_vk_vision_settings() -> VkVisionSettings:
    """Читает VK_VISION_* из окружения."""
    load_env_file()
    return VkVisionSettings(
        oauth_token=os.getenv("VK_VISION_OAUTH_TOKEN", "").strip(),
        oauth_provider=os.getenv("VK_VISION_OAUTH_PROVIDER", "mcs").strip() or "mcs",
        api_url=os.getenv("VK_VISION_URL", _DEFAULT_VISION_URL).strip() or _DEFAULT_VISION_URL,
        timeout_seconds=float(os.getenv("VK_VISION_TIMEOUT_SECONDS", "60")),
    )
