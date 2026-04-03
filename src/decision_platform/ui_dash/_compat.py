from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


try:  # pragma: no cover
    from dash import Dash, Input, Output, State, dcc, html
    import dash_ag_grid as dag
    import dash_cytoscape as cyto

    DASH_AVAILABLE = True
except Exception:  # pragma: no cover
    DASH_AVAILABLE = False

    @dataclass
    class Component:
        component_type: str
        props: dict[str, Any] = field(default_factory=dict)
        children: Any = None

    class Dash:  # type: ignore[override]
        def __init__(self, name: str, external_stylesheets: list[str] | None = None):
            self.name = name
            self.external_stylesheets = external_stylesheets or []
            self.layout: Any = None
            self.callbacks: list[dict[str, Any]] = []

        def callback(self, *args: Any, **kwargs: Any):
            def decorator(func: Any) -> Any:
                self.callbacks.append({"args": args, "kwargs": kwargs, "func_name": func.__name__})
                return func

            return decorator

        def run(self, **kwargs: Any) -> None:
            raise RuntimeError("Dash is not installed in this environment.")

    def _factory(component_type: str):
        def creator(*children: Any, **props: Any) -> Component:
            return Component(component_type=component_type, props=props, children=list(children))

        return creator

    html = SimpleNamespace(
        Div=_factory("Div"),
        H1=_factory("H1"),
        H2=_factory("H2"),
        H3=_factory("H3"),
        P=_factory("P"),
        Button=_factory("Button"),
        Pre=_factory("Pre"),
    )
    dcc = SimpleNamespace(
        Tabs=_factory("Tabs"),
        Tab=_factory("Tab"),
        Graph=_factory("Graph"),
        Store=_factory("Store"),
        Dropdown=_factory("Dropdown"),
        Checklist=_factory("Checklist"),
        Input=_factory("Input"),
        Slider=_factory("Slider"),
    )
    dag = SimpleNamespace(AgGrid=_factory("AgGrid"))
    cyto = SimpleNamespace(Cytoscape=_factory("Cytoscape"))

    class Input:  # type: ignore[override]
        def __init__(self, component_id: str, component_property: str):
            self.component_id = component_id
            self.component_property = component_property

    class Output(Input):  # type: ignore[override]
        pass

    class State(Input):  # type: ignore[override]
        pass
