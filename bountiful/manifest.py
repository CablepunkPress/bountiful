"""Manifest endpoint — serves /.well-known/bountiful.json.

This is how other sites discover your site. The manifest is generated
from the database (public key) and the site's configuration (domain,
inbox URL).
"""

import json

from flask import Blueprint, Response

from bountiful.db import Database


def create_manifest(db: Database, domain: str) -> Blueprint:
    """Create the manifest blueprint for a specific site.

    The domain parameter is the site's identity. 
    Prototype is http://localhost:5000; 
    First production site planned is https://stephenoravec.com.
    """

    manifest = Blueprint("manifest", __name__)

    @manifest.route("/.well-known/bountiful.json")
    def serve_manifest():
        keypair = db.get_keypair()
        if keypair is None:
            return Response(
                json.dumps({"error": "site not initialized"}),
                status=500,
                content_type="application/json",
            )

        # Build inbox URL from domain
        if domain.startswith("http"):
            inbox_url = f"{domain}/bountiful/inbox"
            feed_url = f"{domain}/feed.json"
        else:
            inbox_url = f"https://{domain}/bountiful/inbox"
            feed_url = f"https://{domain}/feed.json"

        data = {
            "domain": domain,
            "inbox_url": inbox_url,
            "feed_url": feed_url,
            "public_key": keypair["public_key"],
            "software_version": "0.1.0",
        }

        return Response(
            json.dumps(data, indent=2),
            status=200,
            content_type="application/json",
        )

    return manifest