# Bountiful

A protocol and personal software environment for the independent web.

Bountiful lets personal websites discover each other, establish follow relationships, and exchange private signed letters — no platform, no algorithm, no middleman. 

The protocol is the foundation. The software is the environment: a locally hosted Flask application for publishing, reading, messaging, and managing your digital life on your own damn machine.

Keep your data local, publish (and republish your corpo-platform exports) to your website, follow and message other sites on the protocol. Your Web identity is your Web domain.

Some assembly required. Messaging requires the recipient to run a cloud relay.

## Protocol

Two websites running Bountiful can:

- **Discover** each other via a manifest at `/.well-known/bountiful.json`
- **Follow** each other by sending a signed request to the other site's inbox
- **Send letters** — private, signed messages between sites with an established follow relationship

Every message is signed with Ed25519. The receiving site fetches the sender's public key from their manifest and verifies the signature before accepting anything. You can't message a site you don't follow.

### How it works

A Bountiful site publishes a manifest at `/.well-known/bountiful.json` advertising its domain, inbox URL, and public key. Another site fetches that manifest to discover how to reach it.

Follows and letters are JSON envelopes signed by the sender and POSTed to the recipient's inbox. The inbox verifies the signature, checks the relationship, and stores the result in a local SQLite database that never leaves the machine.

Two config files serve two purposes:

- `bountiful.config.json` — user-editable site settings
- `.well-known/bountiful.json` — software-generated capability manifest

All Bountiful routes are namespaced under `/bountiful/` to avoid collisions with existing site routes.

### Localhost prototype

The prototype runs two Flask servers simulating independent websites and executes a seven-step protocol test: discover, follow, send letter, verify, follow back, reply, verify final state.

Requires Python 3.12 or later.

```bash
git clone https://github.com/CablepunkPress/bountiful.git
cd bountiful
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Start both sites in separate terminals (activate the venv in each):

```bash
# Terminal 1
python prototype/site_a.py

# Terminal 2
python prototype/site_b.py
```

Run the protocol test in a third terminal:

```bash
python prototype/test_protocol.py
```

Expected output:
```
==================================================
BOUNTIFUL PROTOCOL TEST
==================================================

--- Step 1: Discovery ---
Site A discovered Site B:
  domain: http://localhost:5001
  inbox:  http://localhost:5001/bountiful/inbox
  key:    TDxDpY31rmtxO9jM+Ndk...

--- Step 2: Site A follows Site B ---
  followed

--- Step 3: Verify follow ---
  Site A following: [{'domain': 'http://localhost:5001', 'followed_at': '2026-06-30T04:24:42.666769+00:00'}]
  Site B followers: [{'domain': 'http://localhost:5000', 'followed_at': '2026-06-30T04:24:42.648904+00:00'}]

--- Step 4: Site A sends a letter ---
  delivered

--- Step 5: Verify letter ---
  Site A outbound: 1 letter(s)
  Site B inbound:  1 letter(s)
    from:    http://localhost:5000
    subject: Hello from the other side
    body:    This is a test of the Bountiful protocol messenger system.

--- Step 6: Site B follows Site A and replies ---
  follow: followed
  reply:  delivered
    from:    http://localhost:5001
    subject: Re: Hello from the other side
    body:    Letter received. The Bountiful protocol works.

--- Step 7: Final state ---
  Site A following:  ['http://localhost:5001']
  Site A followers:  ['http://localhost:5001']
  Site A letters:    2
  Site B following:  ['http://localhost:5000']
  Site B followers:  ['http://localhost:5000']
  Site B letters:    2

==================================================
PROTOCOL TEST COMPLETE
==================================================
```
To reset, stop both servers, delete the databases, and restart:

```bash
rm prototype/site_*.db
```

### Production transport

Static hosting (GitHub Pages, Azure Static Web Apps) cannot accept POST requests. Production deployment requires a relay server that accepts signed envelopes, stores them, and releases them when the site owner authenticates via signed challenge. The relay never holds the private key and cannot read the mail.

Any server that can accept HTTP POST and persist data works. This project's reference implementation uses Cloud Run and Firestore on Google Cloud Platform.

### Cryptographic roadmap

The prototype signs with Ed25519. Migration to ML-DSA post-quantum cryptography planned before production use.

## Software

Bountiful is a Flask application organized as blueprints. Local-first by default: `localhost:5000` in a browser, SQLite on disk, and your files on your machine. The same codebase deploys to Cloud Run with Firestore when cloud features are needed. The difference is in the configuration, not the code.

Technology stack: Flask, Jinja2 templates, CSS, and JavaScript as glue. AI agent capabilities are provided by [Basic Bot](https://github.com/StephenOravec/basic-bot), imported as a dependency.

### Components

**Publisher** — Blog engine. Markdown authoring, image handling, static HTML output, JSON Feed 1.1. Existing implementation at [StephenOravec/stephenoravec.com/publisher](https://github.com/StephenOravec/stephenoravec.com/tree/main/publisher) to be migrated into Bountiful.

**Reader** — RSS, Atom, and JSON Feed reader. Reverse chronological, dark mode, no algorithm. Collected articles sync to a local database for offline reading and to Firestore for agent access. Not yet built.

**Messenger** — The protocol implementation above. Localhost prototype working. Cloud relay and post-quantum cryptography upgrade pending.

**Stream** — Feed of posts from followed Bountiful sites. Not yet built.

**Darkroom** — Image processor for Publisher. Normalizes source images (retro screenshots, camera photos, legacy content) to standard dimensions. A limited renderer exists in the Publisher codebase. Largely not yet built.

**Chronicler** — Viewer and republishing tool for imported social media archives (Twitter, WordPress, Facebook, Instagram). Database and tweet viewer exist in a private repository to be migrated into Bountiful.

**Operator** — AI agent dashboard. Chat interface, model selector, session management. Dashboard and chat interface currently operational at [oravec.io](https://oravec.io). Basic Bot is the underlying AI engine, currently in a private repository at [StephenOravec/basic-bot](https://github.com/StephenOravec/basic-bot) and planned for open-source release.

## Project structure
```
bountiful/
├── bountiful/
│   ├── __init__.py
│   ├── crypto.py          # Ed25519 signing and verification
│   ├── db.py              # SQLite storage layer
│   ├── models.py          # Protocol envelope definitions
│   ├── manifest.py        # Flask blueprint for /.well-known/bountiful.json
│   ├── inbox.py           # Flask blueprint for POST /bountiful/inbox
│   └── client.py          # Outbound functions: discover, follow, send_letter
├── prototype/
│   ├── site_a.py          # Flask app on port 5000
│   ├── site_b.py          # Flask app on port 5001
│   └── test_protocol.py   # Seven-step protocol test
├── pyproject.toml
├── LICENSE
└── README.md
```
## License

MIT