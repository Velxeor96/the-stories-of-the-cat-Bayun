"""
core/config.py — загрузчик конфига.

Читает config.yaml и secrets.toml (или .env), раздаёт настройки другим модулям.

Использование:
    from core.config import Config
    cfg = Config.load()
    url = cfg.provider_url("kodik")
    key = cfg.provider_key("kodik")
    model_id = cfg.model_id("deepseek_flash")
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError as e:
    raise ImportError(
        "Не установлен PyYAML. Выполни: pip install pyyaml"
    ) from e


class ConfigError(Exception):
    """Ошибка конфига."""


# ============================================================
# Хелперы для чтения secrets
# ============================================================

def _read_secrets_toml(path: Path) -> dict[str, str]:
    """Прочитать .streamlit/secrets.toml вручную (без streamlit)."""
    if not path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}

    with path.open("rb") as f:
        data = tomllib.load(f)

    # Оставляем только строки верхнего уровня
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _read_dotenv(path: Path) -> dict[str, str]:
    """Простой парсер .env (без зависимости от python-dotenv)."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        result[key] = val
    return result


# ============================================================
# Основной класс
# ============================================================

@dataclass
class Provider:
    name: str
    base_url: str
    api_key_env: str


@dataclass
class Model:
    key: str
    id: str
    provider: str
    context: int
    description: str


class Config:
    def __init__(self, data: dict, secrets: dict):
        self.data = data
        self.secrets = secrets
        self._validate()

    # ---------- Загрузка ----------

    @classmethod
    def load(cls, root: Optional[Path] = None) -> "Config":
        if root is None:
            root = Path(__file__).resolve().parents[1]
        root = Path(root)

        yaml_path = root / "config.yaml"
        if not yaml_path.exists():
            raise ConfigError(f"Не найден {yaml_path}")

        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ConfigError("config.yaml должен быть словарём на верхнем уровне")

        # Собираем секреты из двух источников: .streamlit/secrets.toml → .env
        secrets: dict[str, str] = {}
        secrets.update(_read_dotenv(root / ".env"))
        secrets.update(_read_secrets_toml(root / ".streamlit" / "secrets.toml"))

        # Переменные окружения перекрывают всё
        for key in list(secrets.keys()):
            if key in os.environ:
                secrets[key] = os.environ[key]

        return cls(data, secrets)

    # ---------- Валидация ----------

    def _validate(self) -> None:
        if "providers" not in self.data:
            raise ConfigError("В config.yaml нет секции 'providers'")
        if "models" not in self.data:
            raise ConfigError("В config.yaml нет секции 'models'")
        if "roles" not in self.data:
            raise ConfigError("В config.yaml нет секции 'roles'")

        # Все роли ссылаются на существующие модели
        for role, model_key in self.data["roles"].items():
            if model_key not in self.data["models"]:
                raise ConfigError(
                    f"Роль '{role}' ссылается на несуществующую модель '{model_key}'"
                )

        # Все модели ссылаются на существующих провайдеров
        for model_key, model_data in self.data["models"].items():
            prov = model_data.get("provider")
            if prov not in self.data["providers"]:
                raise ConfigError(
                    f"Модель '{model_key}' ссылается на несуществующего провайдера '{prov}'"
                )

    # ---------- Геттеры ----------

    def provider(self, key: str) -> Provider:
        p = self.data["providers"].get(key)
        if not p:
            raise ConfigError(f"Провайдер '{key}' не найден в config.yaml")
        return Provider(
            name=p["name"],
            base_url=p["base_url"],
            api_key_env=p["api_key_env"],
        )

    def provider_url(self, key: str) -> str:
        return self.provider(key).base_url

    def provider_key(self, key: str) -> str:
        env_name = self.provider(key).api_key_env
        val = self.secrets.get(env_name)
        if not val:
            raise ConfigError(
                f"Не найден ключ '{env_name}'. "
                f"Добавь его в .streamlit/secrets.toml или в .env"
            )
        return val

    def model(self, key: str) -> Model:
        m = self.data["models"].get(key)
        if not m:
            raise ConfigError(f"Модель '{key}' не найдена в config.yaml")
        return Model(
            key=key,
            id=m["id"],
            provider=m["provider"],
            context=m.get("context", 0),
            description=m.get("description", ""),
        )

    def model_id(self, key: str) -> str:
        return self.model(key).id

    def role_model(self, role: str) -> Model:
        key = self.data["roles"].get(role)
        if not key:
            raise ConfigError(f"Роль '{role}' не найдена в config.yaml")
        return self.model(key)

    def role_defaults(self) -> dict[str, Any]:
        return dict(self.data.get("defaults", {}))

    def retries(self) -> dict[str, Any]:
        return dict(self.data.get("retries", {}))

    # ---------- Диагностика ----------

    def summary(self) -> str:
        lines = ["=== Config ==="]
        lines.append("Провайдеры:")
        for k, p in self.data["providers"].items():
            has_key = "✅" if self.secrets.get(p["api_key_env"]) else "❌"
            lines.append(f"  {k}: {p['base_url']}  [ключ: {has_key}]")
        lines.append("Роли:")
        for role, model_key in self.data["roles"].items():
            m = self.data["models"][model_key]
            lines.append(f"  {role:10s} → {m['id']}  ({m['provider']})")
        return "\n".join(lines)