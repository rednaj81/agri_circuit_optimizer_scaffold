from __future__ import annotations

import pytest

from decision_platform.audit import audit_julia_engine_implementation


pytestmark = [pytest.mark.fast]


def test_engine_audit_makes_watermodels_scope_explicit() -> None:
    audit = audit_julia_engine_implementation()

    assert audit["watermodels_imported"] is True
    assert audit["jump_imported"] is True
    assert audit["highs_imported"] is True
    assert audit["what_uses_watermodels_in_practice"]
    assert audit["simplifications_still_present"]
    assert "route_metrics" in audit["metrics_emitted_by_julia_engine"]
