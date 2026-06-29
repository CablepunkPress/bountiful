"""Inbox endpoint — receives signed envelopes from other Bountiful sites.

A Flask blueprint that handles POST requests to /bountiful/inbox.
Every request must include a Bountiful-From header (the sender's domain)
and a Bountiful-Signature header (Ed25519 signature of the raw body).

The inbox verifies the signature by fetching the sender's
/.well-known/bountiful.json to get their public key. If valid,
it processes the envelope: 'follow' adds to followers,
'letter' stores the message (but only if the sender is a follower).
"""

import json

import requests
from flask import Blueprint, Response, request

from bountiful.crypto import verify
from bountiful.db import Database
from bountiful.models import validate_envelope


def create_inbox(db: Database) -> Blueprint:
    """Create the inbox blueprint wired to a specific database."""

    inbox = Blueprint("inbox", __name__)

    @inbox.route("/bountiful/inbox", methods=["POST"])
    def receive():
        # --- read headers ---
        from_domain = request.headers.get("Bountiful-From")
        signature = request.headers.get("Bountiful-Signature")

        if not from_domain or not signature:
            return Response(
                json.dumps({"error": "missing Bountiful-From or Bountiful-Signature header"}),
                status=400,
                content_type="application/json",
            )

        # --- fetch sender's public key ---
        public_key = _fetch_public_key(from_domain)
        if public_key is None:
            return Response(
                json.dumps({"error": f"could not fetch manifest for {from_domain}"}),
                status=400,
                content_type="application/json",
            )

        # --- verify signature ---
        raw_body = request.get_data()
        if not verify(raw_body, signature, public_key):
            return Response(
                json.dumps({"error": "invalid signature"}),
                status=403,
                content_type="application/json",
            )

        # --- validate envelope ---
        data = json.loads(raw_body)
        valid, error = validate_envelope(data)
        if not valid:
            return Response(
                json.dumps({"error": error}),
                status=400,
                content_type="application/json",
            )

        # --- check 'from' matches header ---
        if data["from"] != from_domain:
            return Response(
                json.dumps({"error": "'from' in body does not match Bountiful-From header"}),
                status=400,
                content_type="application/json",
            )

        # --- dispatch by type ---
        msg_type = data["type"]

        if msg_type == "follow":
            db.add_follower(from_domain)
            return Response(
                json.dumps({"status": "followed"}),
                status=200,
                content_type="application/json",
            )

        if msg_type == "letter":
            if not db.is_follower(from_domain):
                return Response(
                    json.dumps({"error": "must be a follower to send letters"}),
                    status=403,
                    content_type="application/json",
                )
            db.add_letter(
                direction="inbound",
                from_domain=data["from"],
                to_domain=data["to"],
                body=data["body"],
                timestamp=data["timestamp"],
                subject=data.get("subject"),
            )
            return Response(
                json.dumps({"status": "delivered"}),
                status=200,
                content_type="application/json",
            )

    return inbox


def _fetch_public_key(domain: str) -> str | None:
    """Fetch a domain's public key from its bountiful.json manifest.

    For the prototype, domains are localhost URLs like
    http://localhost:5000. In production these would be
    https://stephenoravec.com.
    """
    # Prototype: domain is already a full URL like http://localhost:5000
    # Production: would be https://{domain}
    if domain.startswith("http"):
        url = f"{domain}/.well-known/bountiful.json"
    else:
        url = f"https://{domain}/.well-known/bountiful.json"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        manifest = resp.json()
        return manifest.get("public_key")
    except Exception:
        return None