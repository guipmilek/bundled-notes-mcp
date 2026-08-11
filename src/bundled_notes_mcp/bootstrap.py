from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx

from .auth import sign_in_with_password
from .config import DEFAULT_PROJECT_ID, DEFAULT_STORAGE_BUCKET, WEB_ORIGIN
from .errors import BundledNotesError


async def discover_public_config(http: httpx.AsyncClient) -> dict[str, str]:
    """Discover the public Firebase Web config from the current production assets."""
    response = await http.get(f"{WEB_ORIGIN}/", headers={"Referer": f"{WEB_ORIGIN}/"})
    if response.status_code >= 400:
        raise BundledNotesError("config_discovery_failed", "Could not load the Bundled Notes web application.")
    sources = [response.text]
    script_paths = re.findall(r'<script[^>]+src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', response.text)
    for script_path in script_paths[:12]:
        asset = await http.get(urljoin(f"{WEB_ORIGIN}/", script_path), headers={"Referer": f"{WEB_ORIGIN}/"})
        if asset.status_code < 400:
            sources.append(asset.text)
    joined = "\n".join(sources)

    def field(*names: str) -> str | None:
        for name in names:
            match = re.search(
                rf'(?:["\'`]?{re.escape(name)}["\'`]?)\s*:\s*["\'`]([^"\'`]+)["\'`]',
                joined,
            )
            if match:
                return match.group(1)
        return None

    api_key = field("apiKey", "VITE_APP_FIREBASE_API_KEY")
    if not api_key:
        raise BundledNotesError(
            "config_discovery_failed",
            "Could not find the public Firebase API key; pass --api-key explicitly.",
        )
    return {
        "api_key": api_key,
        "project_id": field("projectId", "VITE_APP_FIREBASE_PROJECT_ID") or DEFAULT_PROJECT_ID,
        "storage_bucket": field("storageBucket", "VITE_APP_FIREBASE_STORAGE_BUCKET") or DEFAULT_STORAGE_BUCKET,
    }


async def _authenticate(args: argparse.Namespace, email: str, password: str) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=30) as http:
        config = (
            {"api_key": args.api_key, "project_id": args.project_id, "storage_bucket": args.storage_bucket}
            if args.api_key
            else await discover_public_config(http)
        )
        token = await sign_in_with_password(config["api_key"], email, password, http)
        return token | config


def _persist(args: argparse.Namespace, result: dict[str, str]) -> None:
    if args.output:
        target = Path(args.output).expanduser().resolve()
        if target.exists() and not args.overwrite:
            raise SystemExit(f"Refusing to overwrite {target}; pass --overwrite explicitly.")
        target.write_text(
            "\n".join(
                [
                    f"BUNDLED_FIREBASE_API_KEY={result['api_key']}",
                    f"BUNDLED_FIREBASE_PROJECT_ID={result['project_id']}",
                    f"BUNDLED_FIREBASE_STORAGE_BUCKET={result['storage_bucket']}",
                    f"BUNDLED_FIREBASE_REFRESH_TOKEN={result['refresh_token']}",
                    f"BUNDLED_FIREBASE_UID={result['uid']}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        print(f"Authenticated. Secrets written to {target}; keep it out of version control.")
    else:
        print("Authenticated successfully. Re-run with --output .env to persist the refresh token securely.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactively obtain a Bundled Notes Firebase refresh token.")
    parser.add_argument(
        "--api-key", help="Public Firebase Web API key; discovered from the current web app when omitted"
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--storage-bucket", default=DEFAULT_STORAGE_BUCKET)
    parser.add_argument("--output", help="Write a gitignored env file; the token is never printed")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    email = input("Bundled Notes email: ").strip()
    password = getpass.getpass("Bundled Notes password: ")
    result = asyncio.run(_authenticate(args, email, password))
    _persist(args, result)


if __name__ == "__main__":
    main()
