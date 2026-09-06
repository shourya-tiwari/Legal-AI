"""
app.guard.require_role -- the per-key RBAC dependency factory
(docs/v2/ARCHITECTURE.md security item 5). Route-level enforcement (a real
403 through the FastAPI stack) is covered in test_v2_routes.py and
test_review_queue.py; this is a direct unit test of the check itself.
"""
from fastapi import HTTPException
import pytest

from app.auth import OrgContext
from app.guard import require_role


def test_require_role_allows_a_matching_role():
    check = require_role("admin", "editor")
    org = OrgContext(id=1, name="acme", role="editor")
    assert check(org=org) is org


def test_require_role_rejects_a_non_matching_role():
    check = require_role("admin")
    org = OrgContext(id=1, name="acme", role="viewer")
    with pytest.raises(HTTPException) as exc:
        check(org=org)
    assert exc.value.status_code == 403


def test_org_context_defaults_to_admin_role_and_no_key():
    org = OrgContext(id=1, name="acme")
    assert org.role == "admin"
    assert org.api_key_id is None
