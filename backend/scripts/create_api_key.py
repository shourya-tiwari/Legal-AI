"""
Bootstrap an organization and issue it an API key.

Usage (from backend/, with the venv active):
    python scripts/create_api_key.py "Acme Legal" "acme-prod-key"

Prints the raw key exactly once — only its hash is stored, so save it now.
Only needed once AUTH_REQUIRED=true; with the default (false) every caller
resolves to the shared "default" org and no key is required.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import create_api_key
from app.db import SessionLocal, init_db
from app.db_models import Organization


def main(org_name: str, key_name: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(name=org_name).first()
        if org is None:
            org = Organization(name=org_name)
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization '{org_name}' (id={org.id})")

        raw_key = create_api_key(db, org, key_name)
        print(f"API key for '{org_name}' / '{key_name}':\n{raw_key}")
        print("\nSave this now -- it cannot be shown again.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
