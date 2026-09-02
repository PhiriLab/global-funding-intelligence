"""The event_name CHECK constraint and the RLS insert policy must allow the same
events. Telemetry v2 added session_start/page_view to the live RLS policy but not
to the CHECK constraint, so those inserts were rejected silently and every session
lost its entry events. This test pins the two lists to each other in the schema.
"""
import re
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "db" / "supabase_evaluation.sql").read_text(encoding="utf-8")


def _event_lists():
    # CHECK: event_name text not null check (event_name in ( ... ))
    check = re.search(r"event_name text not null check \(event_name in \((.*?)\)\)", SQL, re.S).group(1)
    # RLS: with check ( event_name in ( ... ) and ...
    rls = re.search(r"with check \(\s*event_name in \((.*?)\)", SQL, re.S).group(1)
    names = lambda s: set(re.findall(r"'([a-z_]+)'", s))
    return names(check), names(rls)


def test_check_constraint_and_rls_policy_allow_identical_events():
    check, rls = _event_lists()
    assert check == rls, f"CHECK and RLS event lists diverge: only-in-check={check - rls} only-in-rls={rls - check}"


def test_v2_entry_events_are_allowed():
    check, rls = _event_lists()
    for event in ("session_start", "page_view"):
        assert event in check and event in rls
