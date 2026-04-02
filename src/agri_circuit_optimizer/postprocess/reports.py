from __future__ import annotations

from typing import Any, Dict


def build_bom_report(solution: Dict[str, Any]) -> Dict[str, Any]:
    bom = sorted(solution.get("bom", []), key=lambda item: item["component_id"])
    return {"bom": bom, "total_material_cost": solution.get("summary", {}).get("total_material_cost", 0.0)}


def build_route_report(solution: Dict[str, Any]) -> Dict[str, Any]:
    routes = sorted(solution.get("routes", []), key=lambda item: item["route_id"])
    return {"routes": routes}


def build_hydraulic_report(solution: Dict[str, Any]) -> Dict[str, Any]:
    hydraulics = sorted(solution.get("hydraulics", []), key=lambda item: item["route_id"])
    return {"hydraulics": hydraulics}
