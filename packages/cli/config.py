import os
import json
from typing import Optional, Dict, Any

CONFIG_DIR = os.path.expanduser("~/.ziref")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class CliConfig:
    @staticmethod
    def get_api_url() -> str:
        return os.environ.get("ZIREF_API_URL", "http://localhost:8000")

    @classmethod
    def load(cls) -> Dict[str, Any]:
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def save(cls, data: Dict[str, Any]) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        current = cls.load()
        current.update(data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)

    @classmethod
    def get_token(cls) -> Optional[str]:
        # Environment variable overrides config file
        env_token = os.environ.get("ZIREF_TOKEN")
        if env_token:
            return env_token
        return cls.load().get("token")

    @classmethod
    def clear(cls) -> None:
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
            except Exception:
                pass

cli_config = CliConfig()
