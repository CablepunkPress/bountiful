"""Site A: 'stephenoravec.com' on port 5000."""

from flask import Flask

from bountiful.crypto import generate_keypair
from bountiful.db import Database
from bountiful.inbox import create_inbox
from bountiful.manifest import create_manifest

DOMAIN = "http://localhost:5000"
DB_PATH = "prototype/site_a.db"

db = Database(DB_PATH)

if not db.has_keypair():
    public_key, private_key = generate_keypair()
    db.set_keypair(public_key, private_key)
    print(f"Generated keypair for {DOMAIN}")

app = Flask(__name__)
app.register_blueprint(create_manifest(db, DOMAIN))
app.register_blueprint(create_inbox(db))

if __name__ == "__main__":
    print(f"Site A ({DOMAIN}) starting...")
    app.run(port=5000)