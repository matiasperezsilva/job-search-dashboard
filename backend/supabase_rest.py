from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import requests


@dataclass
class UserContext:
    token: str
    user_id: str
    email: str = ""


class SupabaseRest:
    def __init__(self, token: str):
        self.url = os.environ["SUPABASE_URL"].rstrip("/")
        self.key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": self.key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def verify_user(self) -> UserContext:
        r = self.session.get(f"{self.url}/auth/v1/user", timeout=12)
        r.raise_for_status()
        data = r.json()
        return UserContext(token=self.token, user_id=str(data["id"]), email=data.get("email") or "")

    def _rest(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    def select(self, table: str, params: dict | None = None):
        r = self.session.get(self._rest(table), params=params or {}, timeout=20)
        r.raise_for_status()
        return r.json()

    def upsert(self, table: str, row: dict, on_conflict: str):
        headers = {"Prefer": "resolution=merge-duplicates,return=representation"}
        r = self.session.post(
            self._rest(table), params={"on_conflict": on_conflict}, json=row, headers=headers, timeout=20
        )
        r.raise_for_status()
        return r.json()

    def update(self, table: str, values: dict, params: dict):
        headers = {"Prefer": "return=representation"}
        r = self.session.patch(self._rest(table), params=params, json=values, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()

    def delete(self, table: str, params: dict):
        r = self.session.delete(self._rest(table), params=params, timeout=20)
        r.raise_for_status()
        return True


def now_iso():
    return datetime.now(timezone.utc).isoformat()
