from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = yaml.safe_load((ROOT / "config" / "agent_registry.yaml").read_text(encoding="utf-8"))


def test_external_assets_default_to_quarantine():
    assert REGISTRY["policy"]["default_external_trust"] == "quarantined"
    assert REGISTRY["policy"]["require_security_scan"] is True


def test_review_roles_cannot_write_or_merge():
    for role_name in ("reviewer", "security_reviewer"):
        role = REGISTRY["roles"][role_name]
        assert role["write_access"] is False
        assert role["merge_access"] is False


def test_implementer_can_write_but_not_merge():
    role = REGISTRY["roles"]["implementer"]
    assert role["write_access"] is True
    assert role["merge_access"] is False


def test_all_autonomous_roles_are_bounded():
    for role in REGISTRY["roles"].values():
        assert isinstance(role["max_runs"], int)
        assert 1 <= role["max_runs"] <= 20


def test_learning_cannot_silently_become_rule():
    assert REGISTRY["learning"]["silent_self_promotion_to_rule"] is False
    assert set(REGISTRY["learning"]["minimum_fields"]) >= {
        "origin",
        "evidence",
        "confidence",
        "validation_status",
        "review_date",
    }
