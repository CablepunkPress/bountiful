"""Client functions — discover, follow, and send letters to other sites.

These are the outbound actions a Bountiful site takes. Each function
fetches the target's manifest to find its inbox URL and public key,
builds a signed envelope, and POSTs it. The local database is updated
to reflect what was sent.
"""

import json

import requests

from bountiful.crypto import sign
from bountiful.db import Database
from bountiful.models import build_follow, build_letter


def discover(domain: str) -> dict | None:
    """Fetch a site's bountiful.json manifest.

    Returns the manifest as a dict, or None if the site
    isn't running Bountiful.
    """
    if domain.startswith("http"):
        url = f"{domain}/.well-known/bountiful.json"
    else:
        url = f"https://{domain}/.well-known/bountiful.json"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def follow(db: Database, my_domain: str, target_domain: str) -> dict:
    """Follow another Bountiful site.

    Discovers the target, sends a signed follow envelope to its
    inbox, and records the relationship locally.

    Returns a dict with 'ok' (bool) and 'message' (str).
    """
    manifest = discover(target_domain)
    if manifest is None:
        return {"ok": False, "message": f"could not reach {target_domain}"}

    inbox_url = manifest.get("inbox_url")
    if not inbox_url:
        return {"ok": False, "message": "manifest has no inbox_url"}

    keypair = db.get_keypair()
    if keypair is None:
        return {"ok": False, "message": "no keypair — run setup first"}

    envelope = build_follow(my_domain, target_domain)
    body = json.dumps(envelope).encode()
    signature = sign(body, keypair["private_key"])

    try:
        resp = requests.post(
            inbox_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Bountiful-From": my_domain,
                "Bountiful-Signature": signature,
            },
            timeout=10,
        )

        if resp.ok:
            db.add_following(target_domain)
            return {"ok": True, "message": "followed"}
        else:
            error = resp.json().get("error", resp.text)
            return {"ok": False, "message": error}

    except Exception as e:
        return {"ok": False, "message": str(e)}


def send_letter(
    db: Database,
    my_domain: str,
    target_domain: str,
    body: str,
    subject: str | None = None,
) -> dict:
    """Send a letter to another Bountiful site.

    The sender must already be following the target. Discovers
    the target's inbox, sends a signed letter envelope, and
    stores a copy locally as outbound.

    Returns a dict with 'ok' (bool) and 'message' (str).
    """
    if not db.is_following(target_domain):
        return {"ok": False, "message": f"not following {target_domain}"}

    manifest = discover(target_domain)
    if manifest is None:
        return {"ok": False, "message": f"could not reach {target_domain}"}

    inbox_url = manifest.get("inbox_url")
    if not inbox_url:
        return {"ok": False, "message": "manifest has no inbox_url"}

    keypair = db.get_keypair()
    if keypair is None:
        return {"ok": False, "message": "no keypair — run setup first"}

    envelope = build_letter(my_domain, target_domain, body, subject)
    raw = json.dumps(envelope).encode()
    signature = sign(raw, keypair["private_key"])

    try:
        resp = requests.post(
            inbox_url,
            data=raw,
            headers={
                "Content-Type": "application/json",
                "Bountiful-From": my_domain,
                "Bountiful-Signature": signature,
            },
            timeout=10,
        )

        if resp.ok:
            db.add_letter(
                direction="outbound",
                from_domain=my_domain,
                to_domain=target_domain,
                body=body,
                timestamp=envelope["timestamp"],
                subject=subject,
            )
            return {"ok": True, "message": "delivered"}
        else:
            error = resp.json().get("error", resp.text)
            return {"ok": False, "message": error}

    except Exception as e:
        return {"ok": False, "message": str(e)}