from __future__ import annotations

__all__ = ["run_decision_pipeline"]


def run_decision_pipeline(*args, **kwargs):
    from .run_pipeline import run_decision_pipeline as _run_decision_pipeline

    return _run_decision_pipeline(*args, **kwargs)
