#!/usr/bin/env python3
"""Refresh the 60-day Instagram and Threads tokens and store the new ones in GitHub Secrets.

Run by the "Meta token refresh" workflow twice a month. Needs IG_ACCESS_TOKEN, THREADS_ACCESS_TOKEN,
GH_SECRETS_TOKEN (fine-grained token for this repository with Secrets: read and write) and
GITHUB_REPOSITORY. Tokens are never printed. A token can only be refreshed once it is a day old.
"""
import base64
import os
import sys

import requests
from nacl import encoding, public

E = os.environ
REPO = E.get("GITHUB_REPOSITORY", "JungSuk-Kim/korea-plainly")


def gh(method, path, **kw):
    return requests.request(method, f"https://api.github.com/repos/{REPO}/actions/secrets{path}", timeout=30,
                            headers={"Authorization": f"Bearer {E['GH_SECRETS_TOKEN'].strip()}",
                                     "Accept": "application/vnd.github+json"}, **kw)


def save_secret(name, value):
    key = gh("GET", "/public-key")
    key.raise_for_status()
    k = key.json()
    box = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder()))
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    r = gh("PUT", f"/{name}", json={"encrypted_value": enc, "key_id": k["key_id"]})
    r.raise_for_status()


def main():
    if not E.get("GH_SECRETS_TOKEN"):
        print("::error::GH_SECRETS_TOKEN is not set")
        sys.exit(1)
    k = gh("GET", "/public-key")
    if not k.ok:
        print(f"::error::GH_SECRETS_TOKEN cannot read this repository's secrets key ({k.status_code})")
        sys.exit(1)
    failed = False
    for name, url, grant in (
            ("IG_ACCESS_TOKEN", "https://graph.instagram.com/refresh_access_token", "ig_refresh_token"),
            ("THREADS_ACCESS_TOKEN", "https://graph.threads.net/refresh_access_token", "th_refresh_token")):
        tok = E.get(name, "").strip()
        if not tok:
            print(f"::warning::{name} not set")
            continue
        r = requests.get(url, params={"grant_type": grant, "access_token": tok}, timeout=30)
        d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not r.ok or "access_token" not in d:
            print(f"::error::{name}: refresh failed: {(d.get('error') or {}).get('message', r.status_code)}")
            failed = True
            continue
        save_secret(name, d["access_token"])
        print(f"::notice::{name} refreshed, valid for about {int(d.get('expires_in', 0)) // 86400} days")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
