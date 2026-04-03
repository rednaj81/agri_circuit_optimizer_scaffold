from __future__ import annotations

from typing import Any

import pandas as pd


RANKING_COLUMNS = {
    "cost_weight": ("install_cost", False),
    "quality_weight": ("quality_score_raw", True),
    "flow_weight": ("flow_out_score", True),
    "resilience_weight": ("resilience_score", True),
    "cleaning_weight": ("cleaning_score", True),
    "operability_weight": ("operability_score", True),
}


def apply_weight_profile(catalog_frame: pd.DataFrame, weight_profiles: pd.DataFrame, profile_id: str) -> list[dict[str, Any]]:
    profile = weight_profiles.loc[weight_profiles["profile_id"] == profile_id]
    if profile.empty:
        raise KeyError(f"Unknown weight profile: {profile_id}")
    return apply_dynamic_weights(catalog_frame, profile.iloc[0].to_dict())


def apply_dynamic_weights(catalog_frame: pd.DataFrame, weights: dict[str, Any]) -> list[dict[str, Any]]:
    frame = catalog_frame.copy()
    for weight_key, (metric_column, larger_is_better) in RANKING_COLUMNS.items():
        frame[f"{metric_column}_normalized"] = _normalize_metric(frame[metric_column], larger_is_better)
    total_weight = sum(float(weights.get(weight_key, 0.0)) for weight_key in RANKING_COLUMNS) or 1.0
    frame["score_final"] = 0.0
    for weight_key, (metric_column, _) in RANKING_COLUMNS.items():
        frame["score_final"] += frame[f"{metric_column}_normalized"] * (float(weights.get(weight_key, 0.0)) / total_weight)
    frame.loc[~frame["feasible"].astype(bool), "score_final"] = -1.0
    frame["rank"] = frame["score_final"].rank(method="dense", ascending=False).astype(int)
    return frame.sort_values(["score_final", "install_cost"], ascending=[False, True]).to_dict("records")


def _normalize_metric(series: pd.Series, larger_is_better: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if numeric.nunique() <= 1:
        return pd.Series([1.0] * len(numeric), index=numeric.index)
    scaled = (numeric - numeric.min()) / (numeric.max() - numeric.min())
    return scaled if larger_is_better else 1.0 - scaled
