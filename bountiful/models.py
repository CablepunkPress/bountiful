"""Message envelopes for the Bountiful protocol.

Two message types: 'follow' and 'letter'. Each is a JSON object
sent as the body of a signed HTTP POST to a site's inbox endpoint.
These functions build envelopes for sending and validate them on
receipt. The shapes defined here are the protocol — if two
implementations agree on these, they can talk to each other.
"""

from datetime import datetime, timezone


def build_follow(from_domain: str, to_domain: str) -> dict:
    """Build a follow envelope."""
    return {
        "type": "follow",
        "from": from_domain,
        "to": to_domain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_letter(
    from_domain: str,
    to_domain: str,
    body: str,
    subject: str | None = None,
) -> dict:
    """Build a letter envelope."""
    envelope = {
        "type": "letter",
        "from": from_domain,
        "to": to_domain,
        "body": body,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if subject is not None:
        envelope["subject"] = subject
    return envelope


def validate_envelope(data: dict) -> tuple[bool, str]:
    """Check that an envelope has the required fields.

    Returns (valid, error_message). If valid is True,
    error_message is empty.
    """
    if not isinstance(data, dict):
        return False, "envelope must be a JSON object"

    msg_type = data.get("type")
    if msg_type not in ("follow", "letter"):
        return False, "type must be 'follow' or 'letter'"

    for field in ("from", "to", "timestamp"):
        if not data.get(field):
            return False, f"missing required field: {field}"

    if msg_type == "letter":
        if not data.get("body"):
            return False, "letter must have a body"

    return True, ""