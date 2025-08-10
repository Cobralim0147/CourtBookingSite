
import os
import json

class ConfigLoader:
    """Loads configuration from config.yaml or config.json if available; otherwise uses defaults."""
    def __init__(self, yaml_path: str = "config.yaml", json_path: str = "config.json"):
        self.yaml_path = yaml_path
        self.json_path = json_path
        self.config = self._load()

    def _load(self) -> dict:
        # Try YAML first (without requiring PyYAML)
        if os.path.exists(self.yaml_path):
            try:
                # Minimal, safe YAML reader for this controlled config: treat as JSON if possible
                # If your YAML contains features beyond JSON, install pyyaml and replace this block.
                import yaml  # type: ignore
                with open(self.yaml_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[warn] Failed to parse {self.yaml_path}: {e}. Falling back to JSON/defaults.")

        # Then JSON
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[warn] Failed to parse {self.json_path}: {e}. Falling back to defaults.")

        # Defaults per spec
        return {
            "venue": {
                "name": "Cobra's ZooKeeping Sport Center",
                "timezone": "system",
                "booking_window_days": 30,
                "hold_timeout_minutes": 5,
                "time_format_24h": True
            },
            "accounts": {
                "users": [
                    {"username": "user1", "password": "pass1", "balance_usd": 100},
                    {"username": "user2", "password": "pass2", "balance_usd": 100},
                ],
                "admins": [
                    {"username": "admin", "password": "adminpass"}
                ]
            },
            "rates_usd_per_hour": {
                "badminton": 10,
                "pickleball": 40,
                "handball": 20,
                "skating": 60
            },
            "courts": {
                "badminton": ["B01", "B02", "B03", "B04"],
                "pickleball": ["PB01", "PB02", "PB03", "PB04"],
                "handball": ["H01", "H02", "H03", "H04"],
                "skating": ["SK01", "SK02", "SK03", "SK04"]
            }
        }
