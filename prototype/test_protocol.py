"""Test the Bountiful protocol between Site A and Site B."""

from bountiful.client import discover, follow, send_letter
from bountiful.db import Database

SITE_A = "http://localhost:5000"
SITE_B = "http://localhost:5001"

db_a = Database("prototype/site_a.db")
db_b = Database("prototype/site_b.db")


def main():
    print("=" * 50)
    print("BOUNTIFUL PROTOCOL TEST")
    print("=" * 50)

    # Step 1 — discover
    print("\n--- Step 1: Discovery ---")

    manifest_b = discover(SITE_B)
    if manifest_b:
        print(f"Site A discovered Site B:")
        print(f"  domain: {manifest_b['domain']}")
        print(f"  inbox:  {manifest_b['inbox_url']}")
        print(f"  key:    {manifest_b['public_key'][:20]}...")
    else:
        print("FAILED: Could not discover Site B")
        return

    # Step 2 — Site A follows Site B
    print("\n--- Step 2: Site A follows Site B ---")

    result = follow(db_a, SITE_A, SITE_B)
    print(f"  {result['message']}")
    if not result["ok"]:
        return

    # Step 3 — verify the follow landed
    print("\n--- Step 3: Verify follow ---")

    print(f"  Site A following: {db_a.list_following()}")
    print(f"  Site B followers: {db_b.list_followers()}")

    # Step 4 — Site A sends a letter to Site B
    print("\n--- Step 4: Site A sends a letter ---")

    result = send_letter(
        db_a,
        SITE_A,
        SITE_B,
        subject="Hello from the other side",
        body="This is the first letter sent via the Bountiful protocol.",
    )
    print(f"  {result['message']}")
    if not result["ok"]:
        return

    # Step 5 — verify the letter landed
    print("\n--- Step 5: Verify letter ---")

    outbound = db_a.list_letters(direction="outbound")
    inbound = db_b.list_letters(direction="inbound")
    print(f"  Site A outbound: {len(outbound)} letter(s)")
    print(f"  Site B inbound:  {len(inbound)} letter(s)")
    if inbound:
        letter = inbound[0]
        print(f"    from:    {letter['from_domain']}")
        print(f"    subject: {letter['subject']}")
        print(f"    body:    {letter['body']}")

    # Step 6 — Site B follows Site A and replies
    print("\n--- Step 6: Site B follows Site A and replies ---")

    result = follow(db_b, SITE_B, SITE_A)
    print(f"  follow: {result['message']}")

    result = send_letter(
        db_b,
        SITE_B,
        SITE_A,
        subject="Re: Hello from the other side",
        body="Letter received. The Bountiful protocol works.",
    )
    print(f"  reply:  {result['message']}")

    # Verify the reply landed
    inbound_a = db_a.list_letters(direction="inbound")
    if inbound_a:
        letter = inbound_a[0]
        print(f"    from:    {letter['from_domain']}")
        print(f"    subject: {letter['subject']}")
        print(f"    body:    {letter['body']}")

    # Step 7 — final state
    print("\n--- Step 7: Final state ---")

    print(f"  Site A following:  {[f['domain'] for f in db_a.list_following()]}")
    print(f"  Site A followers:  {[f['domain'] for f in db_a.list_followers()]}")
    print(f"  Site A letters:    {len(db_a.list_letters())}")
    print(f"  Site B following:  {[f['domain'] for f in db_b.list_following()]}")
    print(f"  Site B followers:  {[f['domain'] for f in db_b.list_followers()]}")
    print(f"  Site B letters:    {len(db_b.list_letters())}")

    print("\n" + "=" * 50)
    print("PROTOCOL TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()