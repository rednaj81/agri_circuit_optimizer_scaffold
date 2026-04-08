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
        props: dict[str, Any] = field(default_factory=dict)
        children: Any = None

        def __post_init__(self) -> None:
            for key, value in self.props.items():
                setattr(self, key, value)

        def __getattr__(self, item: str) -> Any:
            try:
                return self.props[item]
            except KeyError as exc:  # pragma: no cover
                raise AttributeError(item) from exc

    class Dash:  # type: ignore[override]
        def __init__(self, name: str, external_stylesheets: list[str] | None = None):
            self.name = name
            self.external_stylesheets = external_stylesheets or []
            self.layout: Any = None
            self.callbacks: list[dict[str, Any]] = []
            self.callback_map: dict[str, dict[str, Any]] = {}

        def callback(self, *args: Any, **kwargs: Any):
            def decorator(func: Any) -> Any:
                self.callbacks.append({"args": args, "kwargs": kwargs, "func_name": func.__name__})
                outputs: list[Output] = []
                inputs: list[Input] = []
                for item in args:
                    if isinstance(item, Output):
                        outputs.append(item)
                    elif isinstance(item, Input):
                        inputs.append(item)
                    elif isinstance(item, (list, tuple)):
                        for nested in item:
                            if isinstance(nested, Output):
                                outputs.append(nested)
                            elif isinstance(nested, Input):
                                inputs.append(nested)
                if outputs:
                    callback_key = ".." + "...".join(
                        f"{output.component_id}.{output.component_property}" for output in outputs
                    ) + ".."
                    if callback_key in self.callback_map:
                        callback_key = f"{callback_key}@{len(self.callback_map)}"
                    self.callback_map[callback_key] = {
                        "inputs": [{"id": item.component_id, "property": item.component_property} for item in inputs],
                        "callback": func,
                    }
                return func

            return decorator

        def run(self, **kwargs: Any) -> None:
            raise RuntimeError("Dash is not installed in this environment.")

    def _factory(component_type: str):
        component_cls = type(component_type, (Component,), {})

        def creator(*children: Any, **props: Any) -> Component:
            explicit_children = props.pop("children", None)
            if explicit_children is not None and children:
                merged_children: Any = [*children, explicit_children]
            elif explicit_children is not None:
                merged_children = explicit_children
            elif len(children) == 1:
                merged_children = children[0]
            else:
                merged_children = list(children)
            return component_cls(props=props, children=merged_children)

        return creator

    html = SimpleNamespace(
        A=_factory("A"),
        Div=_factory("Div"),
        Details=_factory("Details"),
        H1=_factory("H1"),
        H2=_factory("H2"),
        H3=_factory("H3"),
        H4=_factory("H4"),
        Label=_factory("Label"),
        Li=_factory("Li"),
        P=_factory("P"),
        Button=_factory("Button"),
        Pre=_factory("Pre"),
        Span=_factory("Span"),
        Summary=_factory("Summary"),
        Ul=_factory("Ul"),
    )
    dcc = SimpleNamespace(
        Tabs=_factory("Tabs"),
        Tab=_factory("Tab"),
        Graph=_factory("Graph"),
        Store=_factory("Store"),
        Location=_factory("Location"),
        Download=_factory("Download"),
        Dropdown=_factory("Dropdown"),
        Checklist=_factory("Checklist"),
        Input=_factory("Input"),
        Textarea=_factory("Textarea"),
        Slider=_factory("Slider"),
        send_string=lambda content, filename: {"content": content, "filename": filename},
    )
    dag = SimpleNamespace(AgGrid=_factory("AgGrid"))
    cyto = SimpleNamespace(Cytoscape=_factory("Cytoscape"))

    class Input:  # type: ignore[override]
        def __init__(self, component_id: str, component_property: str, **kwargs: Any):
            self.component_id = component_id
            self.component_property = component_property
            self.kwargs = kwargs

    class Output(Input):  # type: ignore[override]
        pass

    class State(Input):  # type: ignore[override]
        pass
