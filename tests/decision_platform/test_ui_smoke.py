from __future__ import annotations

from decision_platform.ui_dash.app import build_app


def test_dash_app_builds_layout_and_callback() -> None:
    app = build_app("data/decision_platform/maquete_v2")

    assert hasattr(app, "layout")
    assert app.layout is not None
    assert len(getattr(app, "callbacks", [])) >= 1
