#!/usr/bin/env python3
"""Trigger a short headless historical crawl on VPS for smoke test."""
import json
import urllib.request

BASE = "http://127.0.0.1:5000/api/v1"
TARGET_ID = "6a140f86-0b0e-46aa-9898-c0094a7d0eb7"  # jaipurite_astro_talk


def post(path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    login = post(
        "/auth/login",
        "",
        {"email": "admin@patrol.dev", "password": "Patrol@2024!"},
    )
    token = login["access_token"]
    print("Login OK")
    # View historical crawl (was broken — should now run headless on VPS)
    res = post(f"/crawlers/start/{TARGET_ID}/view/historical", token)
    print("Start:", res)
    print("Check pm2 logs for crawl activity in ~30s")


if __name__ == "__main__":
    main()
