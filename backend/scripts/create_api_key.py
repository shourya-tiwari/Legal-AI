"""
Bootstrap an organization and issue it an API key.

Usage (from backend/, with the venv active):
    python scripts/create_api_key.py "Acme Legal" "acme-prod-key" [role]

`role` is one of admin (default) | editor | viewer -- per-key RBAC
(docs/v2/ARCHITECTURE.md security item 5, app/guard.py::require_role).
admin can override a document's sensitivity tier and resolve review-queue
items; editor can resolve but not override; viewer can do neither.

Prints the raw key exactly once — only its hash is stored, so save it now.
Only needed once AUTH_REQUIRED=true; with the default (false) every caller
resolves to the shared "default" org (role=admin) and no key is required.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import VALID_ROLES, create_api_key
from app.db import SessionLocal, init_db
from app.db_models import Organization


def main(org_name: str, key_name: str, role: str = "admin") -> None:
    if role not in VALID_ROLES:
        print(f"role must be one of {VALID_ROLES}, got {role!r}")
        sys.exit(1)

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

        raw_key = create_api_key(db, org, key_name, role=role)
        print(f"API key for '{org_name}' / '{key_name}' (role={role}):\n{raw_key}")
        print("\nSave this now -- it cannot be shown again.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:])
