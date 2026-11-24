from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
import requests


class SupabaseError(RuntimeError):
    def __init__(self, resource: str, status: int | None = None, code: str | None = None):
        super().__init__(f"Supabase request failed for {resource}")
        self.resource = resource
        self.status = status
        self.code = code


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

    def _request(self, method: str, url: str, resource: str, *, timeout: int = 20, **kwargs):
        try:
            response = self.session.request(method, url, timeout=timeout, allow_redirects=False, **kwargs)
        except requests.RequestException as exc:
            raise SupabaseError(resource) from exc
        if not 200 <= response.status_code < 300:
            try:
                body = response.json()
                code = body.get("code") if isinstance(body, dict) else None
            except ValueError:
                code = None
            code = code if isinstance(code, str) and code.isascii() and code.isalnum() and len(code) <= 16 else None
            raise SupabaseError(resource, response.status_code, code)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise SupabaseError(resource, response.status_code) from exc

    def verify_user(self) -> UserContext:
        data = self._request("GET", f"{self.url}/auth/v1/user", "auth", timeout=12)
        if not isinstance(data, dict) or not data.get("id"):
            raise SupabaseError("auth")
        return UserContext(token=self.token, user_id=str(data["id"]), email=data.get("email") or "")

    def _rest(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    def select(self, table: str, params: dict | None = None):
        return self._request("GET", self._rest(table), table, params=params or {})

    def insert(self, table: str, row: dict):
        headers = {"Prefer": "return=representation"}
        return self._request("POST", self._rest(table), table, json=row, headers=headers)

    def upsert(self, table: str, row: dict, on_conflict: str):
        headers = {"Prefer": "resolution=merge-duplicates,return=representation"}
        return self._request(
            "POST", self._rest(table), table,
            params={"on_conflict": on_conflict}, json=row, headers=headers,
        )

    def update(self, table: str, values: dict, params: dict):
        headers = {"Prefer": "return=representation"}
        return self._request("PATCH", self._rest(table), table, params=params, json=values, headers=headers)

    def delete(self, table: str, params: dict):
        self._request("DELETE", self._rest(table), table, params=params)
        return True


def now_iso():
    return datetime.now(timezone.utc).isoformat()
