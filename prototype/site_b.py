"""Site B: 'cablepunk.press' on port 5001."""

from flask import Flask

from bountiful.crypto import generate_keypair
from bountiful.db import Database
from bountiful.inbox import create_inbox
from bountiful.manifest import create_manifest

DOMAIN = "http://localhost:5001"
DB_PATH = "prototype/site_b.db"

db = Database(DB_PATH)

if not db.has_keypair():
    public_key, private_key = generate_keypair()
    db.set_keypair(public_key, private_key)
    print(f"Generated keypair for {DOMAIN}")

app = Flask(__name__)
app.register_blueprint(create_manifest(db, DOMAIN))
app.register_blueprint(create_inbox(db))

if __name__ == "__main__":
    print(f"Site B ({DOMAIN}) starting...")
    app.run(port=5001)