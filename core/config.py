"""core/config.py — читает config.yaml и secrets.toml."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigError(Exception):
    """Ошибка конфига."""


def _read_secrets_toml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        return {}
    with path.open("rb") as f:
        data = tomllib.load(f)
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


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

    @classmethod
    def load(cls, root: Optional[Path] = None) -> "Config":
        if root is None:
            root = Path(__file__).resolve().parents[1]
        root = Path(root)

        yaml_path = root / "config.yaml"
        if not yaml_path.exists():
            raise ConfigError(f"не найден {yaml_path}")

        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        secrets: dict[str, str] = {}
        secrets.update(_read_dotenv(root / ".env"))
        secrets.update(_read_secrets_toml(root / ".streamlit" / "secrets.toml"))

        for k in list(secrets.keys()):
            if k in os.environ:
                secrets[k] = os.environ[k]

        return cls(data, secrets)

    def _validate(self) -> None:
        for section in ("providers", "models", "roles"):
            if section not in self.data:
                raise ConfigError(f"в config.yaml нет секции '{section}'")
        for role, mk in self.data["roles"].items():
            if mk not in self.data["models"]:
                raise ConfigError(f"роль '{role}' ссылается на модель '{mk}', которой нет")
        for mk, md in self.data["models"].items():
            if md.get("provider") not in self.data["providers"]:
                raise ConfigError(f"модель '{mk}' ссылается на провайдера '{md.get('provider')}', которого нет")

    def provider(self, key: str) -> Provider:
        p = self.data["providers"].get(key)
        if not p:
            raise ConfigError(f"провайдер '{key}' не найден")
        return Provider(p["name"], p["base_url"], p["api_key_env"])

    def provider_url(self, key: str) -> str:
        return self.provider(key).base_url

    def provider_key(self, key: str) -> str:
        env_name = self.provider(key).api_key_env
        val = self.secrets.get(env_name)
        if not val:
            raise ConfigError(f"нет ключа '{env_name}' в secrets.toml")
        return val

    def model(self, key: str) -> Model:
        m = self.data["models"].get(key)
        if not m:
            raise ConfigError(f"модель '{key}' не найдена")
        return Model(
            key=key, id=m["id"], provider=m["provider"],
            context=m.get("context", 0), description=m.get("description", ""),
        )

    def model_id(self, key: str) -> str:
        return self.model(key).id

    def role_model(self, role: str) -> Model:
        key = self.data["roles"].get(role)
        if not key:
            raise ConfigError(f"роль '{role}' не найдена")
        return self.model(key)

    def role_defaults(self) -> dict[str, Any]:
        return dict(self.data.get("defaults", {}))

    def retries(self) -> dict[str, Any]:
        return dict(self.data.get("retries", {}))

    def summary(self) -> str:
        lines = ["=== Config ===", "Провайдеры:"]
        for k, p in self.data["providers"].items():
            has = "OK" if self.secrets.get(p["api_key_env"]) else "--"
            lines.append(f"  {k}: {p['base_url']}  [ключ: {has}]")
        lines.append("Роли:")
        for role, mk in self.data["roles"].items():
            m = self.data["models"][mk]
            lines.append(f"  {role:10s} -> {m['id']}  ({m['provider']})")
        return "\n".join(lines)
