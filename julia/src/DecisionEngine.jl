module DecisionEngine

using JuMP
using HiGHS
using WaterModels

export build_result, build_results

function build_result(payload)
    model = Model(HiGHS.Optimizer)
    @variable(model, 0 <= x <= 1)
    @objective(model, Max, x)
    optimize!(model)

    installed_links = payload["installed_links"]
    route_requirements = payload["route_requirements"]
    adjacency = _build_adjacency(installed_links)

    all_components = Any[]
    install_cost = 0.0
    fallback_cost = 0.0
    fallback_component_count = 0
    bom = Dict{String, Any}()

    for (_, link) in pairs(installed_links)
        for component in link["installed_components"]
            push!(all_components, component)
            install_cost += _to_float(component["cost"])
            if _to_bool(component["is_fallback"])
                fallback_cost += _to_float(component["cost"])
                fallback_component_count += 1
            end
            component_id = _to_string(component["component_id"])
            if !haskey(bom, component_id)
                bom[component_id] = Dict(
                    "component_id" => component_id,
                    "category" => _to_string(component["category"]),
                    "qty" => 0,
                    "total_cost" => 0.0,
                )
            end
            bom[component_id]["qty"] += 1
            bom[component_id]["total_cost"] += _to_float(component["cost"])
        end
    end

    route_metrics = Any[]
    mandatory_unserved = String[]
    for route in route_requirements
        metric = _evaluate_route(adjacency, installed_links, payload, route)
        push!(route_metrics, metric)
        if _to_bool(route["mandatory"]) && !_to_bool(metric["feasible"])
            push!(mandatory_unserved, _to_string(route["route_id"]))
        end
    end

    feasible = isempty(mandatory_unserved)
    route_count = max(length(route_metrics), 1)
    quality_score_raw = sum(_to_float(route["quality_score_base"]) for route in route_metrics) / route_count
    flow_out_score = sum(_to_float(route["flow_score"]) for route in route_metrics) / route_count
    resilience_score = min(100.0, _alternate_path_count(route_requirements, adjacency) * 10.0 + _served_route_count(route_metrics) * 3.0)
    cleaning_score = max(0.0, 100.0 - _average_cleaning(route_metrics) * 10.0)
    operability_score = sum(_to_float(route["operability_score"]) for route in route_metrics) / route_count

    return Dict(
        "engine" => "watermodels_jl",
        "feasible" => feasible,
        "mandatory_unserved" => mandatory_unserved,
        "install_cost" => round(install_cost; digits = 3),
        "fallback_cost" => round(fallback_cost; digits = 3),
        "quality_score_raw" => round(quality_score_raw; digits = 3),
        "flow_out_score" => round(flow_out_score; digits = 3),
        "resilience_score" => round(resilience_score; digits = 3),
        "cleaning_score" => round(cleaning_score; digits = 3),
        "operability_score" => round(operability_score; digits = 3),
        "maintenance_score" => round(max(0.0, 100.0 - length(all_components) * 1.5); digits = 3),
        "alternate_path_count_critical" => Int(round(_alternate_path_count(route_requirements, adjacency))),
        "fallback_component_count" => fallback_component_count,
        "bom_summary" => Dict(
            "components" => collect(values(bom)),
            "total_components" => sum(item["qty"] for item in values(bom)),
        ),
        "route_metrics" => route_metrics,
    )
end

function build_results(payloads)
    return [build_result(payload) for payload in payloads]
end

function _build_adjacency(installed_links)
    adjacency = Dict{String, Vector{Tuple{String, String}}}()
    for (_, link) in pairs(installed_links)
        from_node = _to_string(link["from_node"])
        to_node = _to_string(link["to_node"])
        link_id = _to_string(link["link_id"])
        push!(get!(adjacency, from_node, Tuple{String, String}[]), (to_node, link_id))
        if haskey(link, "bidirectional") && _to_bool(link["bidirectional"])
            push!(get!(adjacency, to_node, Tuple{String, String}[]), (from_node, link_id))
        end
    end
    return adjacency
end

function _evaluate_route(adjacency, installed_links, payload, route)
    source = _to_string(route["source"])
    sink = _to_string(route["sink"])
    paths = _limited_simple_paths(adjacency, source, sink; max_paths = 12, cutoff = 10)
    if isempty(paths)
        return _route_failure(route, "no_path")
    end

    family_rules = payload["family_rules"]
    successful_paths = Any[]
    failed_paths = Any[]
    for path in paths
        link_ids = path["link_ids"]
        links = [installed_links[link_id] for link_id in link_ids]
        evaluated = _evaluate_path(route, payload, family_rules, path["nodes"], link_ids, links)
        if _to_bool(evaluated["feasible"])
            push!(successful_paths, evaluated)
        else
            push!(failed_paths, evaluated)
        end
    end

    if !isempty(successful_paths)
        return successful_paths[argmax([_route_success_rank(metric) for metric in successful_paths])]
    end
    if !isempty(failed_paths)
        return failed_paths[argmax([_route_failure_rank(metric) for metric in failed_paths])]
    end
    return _route_failure(route, "hydraulic_or_meter_infeasible")
end

function _evaluate_path(route, payload, family_rules, nodes, link_ids, links)
    component_entries = _component_entries_for_links(links)
    pump_entries = [entry for entry in component_entries if _to_string(entry["component"]["category"]) == "pump"]
    meter_entries = [entry for entry in component_entries if _to_string(entry["component"]["category"]) == "meter"]
    fallback_entries = Any[]
    used_fallback_pump = false
    used_fallback_meter = false
    required_flow = _to_float(route["q_min_delivered_lpm"])
    fallback_pump = get(payload["fallback_components"], "pump", nothing)
    fallback_meter = get(payload["fallback_components"], "meter", nothing)

    if isempty(pump_entries)
        if fallback_pump === nothing
            return _route_failure(route, "no_pump_available"; nodes = nodes, link_ids = link_ids, component_entries = component_entries)
        end
        fallback_entry = _make_fallback_entry(fallback_pump, "__fallback_pump__")
        push!(fallback_entries, fallback_entry)
        pump_entries = [fallback_entry]
        used_fallback_pump = true
    end

    active_pump_limit = max(1, Int(family_rules["max_active_pumps_per_route"]))
    active_pump_count = min(length(pump_entries), active_pump_limit)
    passive_reverse_pump_count = max(0, length(pump_entries) - active_pump_count)
    if passive_reverse_pump_count > 0 && !_to_bool(family_rules["allow_idle_pumps_on_path"])
        return _route_failure(
            route,
            "idle_pumps_not_allowed";
            nodes = nodes,
            link_ids = link_ids,
            component_entries = vcat(component_entries, fallback_entries),
            active_pump_count = active_pump_count,
            passive_reverse_pump_count = passive_reverse_pump_count,
            series_pump_count = length(pump_entries),
            fallback_component_count = _fallback_count(vcat(component_entries, fallback_entries)),
            used_fallback_pump = used_fallback_pump,
        )
    end

    selected_meter_entry = nothing
    compatible_meters = [
        entry for entry in meter_entries
        if _to_float(entry["component"]["hard_min_lpm"]) <= required_flow <= _to_float(entry["component"]["hard_max_lpm"])
    ]
    if _to_bool(route["measurement_required"])
        if !isempty(compatible_meters)
            selected_meter_entry = compatible_meters[argmin([
                (
                    abs(_to_float(entry["component"]["confidence_min_lpm"]) - required_flow),
                    -_to_float(entry["component"]["quality_base_score"]),
                )
                for entry in compatible_meters
            ])]
        elseif fallback_meter !== nothing
            selected_meter_entry = _make_fallback_entry(fallback_meter, "__fallback_meter__")
            push!(fallback_entries, selected_meter_entry)
            used_fallback_meter = true
        else
            return _route_failure(
                route,
                "measurement_required_without_compatible_meter";
                nodes = nodes,
                link_ids = link_ids,
                component_entries = component_entries,
                active_pump_count = active_pump_count,
                passive_reverse_pump_count = passive_reverse_pump_count,
                series_pump_count = length(pump_entries),
                fallback_component_count = _fallback_count(vcat(component_entries, fallback_entries)),
                used_fallback_pump = used_fallback_pump,
            )
        end
    end

    max_reading_meters = max(0, Int(get(family_rules, "max_reading_meters_per_route", 1)))
    if length(meter_entries) > max_reading_meters && !_to_bool(family_rules["allow_idle_meters_on_path"])
        return _route_failure(
            route,
            "idle_meters_not_allowed";
            nodes = nodes,
            link_ids = link_ids,
            component_entries = vcat(component_entries, fallback_entries),
            active_pump_count = active_pump_count,
            passive_reverse_pump_count = passive_reverse_pump_count,
            series_pump_count = length(pump_entries),
            selected_meter_id = selected_meter_entry === nothing ? nothing : _to_string(selected_meter_entry["component"]["component_id"]),
            fallback_component_count = _fallback_count(vcat(component_entries, fallback_entries)),
            used_fallback_pump = used_fallback_pump,
            used_fallback_meter = used_fallback_meter,
        )
    end

    path_entries = vcat(component_entries, fallback_entries)
    hydraulics = _evaluate_hydraulics(route, path_entries, selected_meter_entry)
    if _to_float(hydraulics["route_effective_q_max_lpm"]) < required_flow
        return _route_failure(
            route,
            "insufficient_effective_capacity";
            nodes = nodes,
            link_ids = link_ids,
            component_entries = path_entries,
            active_pump_count = active_pump_count,
            passive_reverse_pump_count = passive_reverse_pump_count,
            series_pump_count = length(pump_entries),
            selected_meter_id = selected_meter_entry === nothing ? nothing : _to_string(selected_meter_entry["component"]["component_id"]),
            fallback_component_count = _fallback_count(path_entries),
            used_fallback_pump = used_fallback_pump,
            used_fallback_meter = used_fallback_meter,
            hydraulics = hydraulics,
        )
    end

    route_quality = _sum_quality(path_entries)
    switch_count = _switch_count(path_entries)
    operability_score = max(
        0.0,
        100.0 - switch_count * 6 - passive_reverse_pump_count * 8 - _to_float(hydraulics["total_loss_pct"]) * 0.6,
    )
    flow_score = min(100.0, _to_float(hydraulics["delivered_flow_lpm"]) / max(required_flow, 1.0) * 100.0)

    return Dict(
        "route_id" => _to_string(route["route_id"]),
        "source" => _to_string(route["source"]),
        "sink" => _to_string(route["sink"]),
        "mandatory" => _to_bool(route["mandatory"]),
        "route_group" => _to_string(route["route_group"]),
        "feasible" => true,
        "reason" => "ok",
        "failure_reason" => nothing,
        "path_nodes" => nodes,
        "path_link_ids" => link_ids,
        "active_path_nodes" => nodes,
        "active_path_edge_ids" => link_ids,
        "active_path_arc_ids" => link_ids,
        "active_pump_count" => active_pump_count,
        "passive_reverse_pump_count" => passive_reverse_pump_count,
        "series_pump_count" => length(pump_entries),
        "selected_meter_id" => selected_meter_entry === nothing ? nothing : _to_string(selected_meter_entry["component"]["component_id"]),
        "flow_within_meter_confidence" => _flow_within_meter_confidence(selected_meter_entry, required_flow),
        "cleaning_volume_l" => round(_cleaning_volume(path_entries); digits = 3),
        "component_switch_count" => switch_count,
        "fallback_component_count" => _fallback_count(path_entries),
        "used_fallback_pump" => used_fallback_pump,
        "used_fallback_meter" => used_fallback_meter,
        "delivered_flow_lpm" => round(_to_float(hydraulics["delivered_flow_lpm"]); digits = 3),
        "required_flow_lpm" => required_flow,
        "quality_score_base" => round(route_quality; digits = 3),
        "quality_score" => round(route_quality; digits = 3),
        "operability_score" => round(operability_score; digits = 3),
        "flow_score" => round(flow_score; digits = 3),
        "component_ids_on_path" => [_to_string(entry["component"]["component_id"]) for entry in path_entries],
        "total_loss_pct" => round(_to_float(hydraulics["total_loss_pct"]); digits = 3),
        "total_loss_lpm_equiv" => round(_to_float(hydraulics["total_loss_lpm_equiv"]); digits = 3),
        "route_effective_q_max_lpm" => round(_to_float(hydraulics["route_effective_q_max_lpm"]); digits = 3),
        "hydraulic_slack_lpm" => round(_to_float(hydraulics["hydraulic_slack_lpm"]); digits = 3),
        "gargalo_principal" => hydraulics["gargalo_principal"],
        "bottleneck_component_id" => hydraulics["bottleneck_component_id"],
        "bottleneck_component_category" => hydraulics["bottleneck_component_category"],
        "critical_component_id" => hydraulics["bottleneck_component_id"],
        "critical_consequence" => hydraulics["critical_consequence"],
        "hydraulic_trace" => hydraulics["hydraulic_trace"],
    )
end

function _evaluate_hydraulics(route, component_entries, selected_meter_entry)
    required_flow = _to_float(route["q_min_delivered_lpm"])
    total_loss_pct = 0.0
    capacity_terms = Any[]
    hydraulic_trace = Any[]

    for entry in component_entries
        component = entry["component"]
        loss_pct = _to_float(component["forward_loss_pct_when_on"])
        hard_max = _to_float(component["hard_max_lpm"])
        effective_capacity = max(0.0, hard_max * max(0.05, 1.0 - loss_pct / 100.0))
        total_loss_pct += loss_pct
        trace_item = Dict(
            "link_id" => entry["link_id"],
            "component_id" => _to_string(component["component_id"]),
            "category" => _to_string(component["category"]),
            "loss_pct" => round(loss_pct; digits = 3),
            "hard_max_lpm" => round(hard_max; digits = 3),
            "effective_capacity_lpm" => round(effective_capacity; digits = 3),
            "is_fallback" => _to_bool(component["is_fallback"]),
            "is_bottleneck" => false,
            "consequence" => "path_hydraulic_limit",
        )
        push!(hydraulic_trace, trace_item)
        if hard_max > 0
            push!(capacity_terms, (effective_capacity, component, entry["link_id"]))
        end
    end

    if isempty(capacity_terms)
        return Dict(
            "total_loss_pct" => total_loss_pct,
            "total_loss_lpm_equiv" => required_flow,
            "route_effective_q_max_lpm" => 0.0,
            "hydraulic_slack_lpm" => -required_flow,
            "delivered_flow_lpm" => 0.0,
            "gargalo_principal" => "no_capacity_terms",
            "bottleneck_component_id" => nothing,
            "bottleneck_component_category" => nothing,
            "critical_consequence" => "no_capacity_terms",
            "hydraulic_trace" => hydraulic_trace,
        )
    end

    bottleneck = capacity_terms[argmin([term[1] for term in capacity_terms])]
    bottleneck_capacity, bottleneck_component, bottleneck_link_id = bottleneck
    total_loss_lpm_equiv = required_flow * total_loss_pct / 100.0
    route_effective_q_max_lpm = max(0.0, bottleneck_capacity)
    delivered_flow_lpm = route_effective_q_max_lpm
    hydraulic_slack_lpm = delivered_flow_lpm - required_flow

    for trace_item in hydraulic_trace
        if trace_item["component_id"] == _to_string(bottleneck_component["component_id"]) && trace_item["link_id"] == bottleneck_link_id
            trace_item["is_bottleneck"] = true
            trace_item["consequence"] = "limits_effective_capacity"
        end
    end

    critical_consequence = if selected_meter_entry !== nothing && !_flow_within_meter_confidence(selected_meter_entry, required_flow)
        "meter_outside_confidence_band"
    elseif hydraulic_slack_lpm < 0
        "route_below_required_flow"
    else
        "limits_effective_capacity"
    end

    return Dict(
        "total_loss_pct" => total_loss_pct,
        "total_loss_lpm_equiv" => total_loss_lpm_equiv,
        "route_effective_q_max_lpm" => route_effective_q_max_lpm,
        "hydraulic_slack_lpm" => hydraulic_slack_lpm,
        "delivered_flow_lpm" => delivered_flow_lpm,
        "gargalo_principal" => string(_to_string(bottleneck_component["category"]), ":", _to_string(bottleneck_component["component_id"])),
        "bottleneck_component_id" => _to_string(bottleneck_component["component_id"]),
        "bottleneck_component_category" => _to_string(bottleneck_component["category"]),
        "critical_consequence" => critical_consequence,
        "hydraulic_trace" => hydraulic_trace,
    )
end

function _route_success_rank(metric)
    return (
        _to_float(metric["hydraulic_slack_lpm"]),
        -_to_float(metric["fallback_component_count"]),
        -_to_float(metric["total_loss_lpm_equiv"]),
        _to_float(metric["quality_score"]),
    )
end

function _route_failure_rank(metric)
    priority = Dict(
        "insufficient_effective_capacity" => 5.0,
        "measurement_required_without_compatible_meter" => 4.0,
        "idle_pumps_not_allowed" => 3.0,
        "idle_meters_not_allowed" => 2.0,
        "no_pump_available" => 1.0,
        "no_path" => 0.0,
        "hydraulic_or_meter_infeasible" => -1.0,
    )
    return (
        get(priority, _to_string(metric["reason"]), -5.0),
        _to_float(metric["delivered_flow_lpm"]),
        -_to_float(metric["fallback_component_count"]),
    )
end

function _route_failure(
    route,
    reason;
    nodes = String[],
    link_ids = String[],
    component_entries = Any[],
    active_pump_count = 0,
    passive_reverse_pump_count = 0,
    series_pump_count = 0,
    selected_meter_id = nothing,
    used_fallback_pump = false,
    used_fallback_meter = false,
    fallback_component_count = 0,
    hydraulics = nothing,
)
    if hydraulics === nothing
        hydraulics = Dict(
            "total_loss_pct" => 0.0,
            "total_loss_lpm_equiv" => 0.0,
            "route_effective_q_max_lpm" => 0.0,
            "hydraulic_slack_lpm" => -_to_float(route["q_min_delivered_lpm"]),
            "delivered_flow_lpm" => 0.0,
            "gargalo_principal" => nothing,
            "bottleneck_component_id" => nothing,
            "bottleneck_component_category" => nothing,
            "critical_consequence" => reason,
            "hydraulic_trace" => Any[],
        )
    end
    return Dict(
        "route_id" => _to_string(route["route_id"]),
        "source" => _to_string(route["source"]),
        "sink" => _to_string(route["sink"]),
        "mandatory" => _to_bool(route["mandatory"]),
        "route_group" => _to_string(route["route_group"]),
        "feasible" => false,
        "reason" => reason,
        "failure_reason" => reason,
        "path_nodes" => nodes,
        "path_link_ids" => link_ids,
        "active_path_nodes" => nodes,
        "active_path_edge_ids" => link_ids,
        "active_path_arc_ids" => link_ids,
        "active_pump_count" => active_pump_count,
        "passive_reverse_pump_count" => passive_reverse_pump_count,
        "series_pump_count" => series_pump_count,
        "selected_meter_id" => selected_meter_id,
        "flow_within_meter_confidence" => false,
        "cleaning_volume_l" => round(_cleaning_volume(component_entries); digits = 3),
        "component_switch_count" => _switch_count(component_entries),
        "fallback_component_count" => fallback_component_count,
        "used_fallback_pump" => used_fallback_pump,
        "used_fallback_meter" => used_fallback_meter,
        "delivered_flow_lpm" => round(_to_float(hydraulics["delivered_flow_lpm"]); digits = 3),
        "required_flow_lpm" => _to_float(route["q_min_delivered_lpm"]),
        "quality_score_base" => round(_sum_quality(component_entries); digits = 3),
        "quality_score" => round(_sum_quality(component_entries); digits = 3),
        "operability_score" => 0.0,
        "flow_score" => 0.0,
        "component_ids_on_path" => [_to_string(entry["component"]["component_id"]) for entry in component_entries],
        "total_loss_pct" => round(_to_float(hydraulics["total_loss_pct"]); digits = 3),
        "total_loss_lpm_equiv" => round(_to_float(hydraulics["total_loss_lpm_equiv"]); digits = 3),
        "route_effective_q_max_lpm" => round(_to_float(hydraulics["route_effective_q_max_lpm"]); digits = 3),
        "hydraulic_slack_lpm" => round(_to_float(hydraulics["hydraulic_slack_lpm"]); digits = 3),
        "gargalo_principal" => hydraulics["gargalo_principal"],
        "bottleneck_component_id" => hydraulics["bottleneck_component_id"],
        "bottleneck_component_category" => hydraulics["bottleneck_component_category"],
        "critical_component_id" => hydraulics["bottleneck_component_id"],
        "critical_consequence" => hydraulics["critical_consequence"],
        "hydraulic_trace" => hydraulics["hydraulic_trace"],
    )
end

function _component_entries_for_links(links)
    entries = Any[]
    for link in links
        link_id = _to_string(link["link_id"])
        for component in link["installed_components"]
            push!(entries, Dict("link_id" => link_id, "component" => component))
        end
    end
    return entries
end

function _make_fallback_entry(component, link_id)
    return Dict("link_id" => link_id, "component" => component)
end

function _fallback_count(component_entries)
    return sum(_to_bool(entry["component"]["is_fallback"]) for entry in component_entries)
end

function _flow_within_meter_confidence(selected_meter_entry, required_flow)
    if selected_meter_entry === nothing
        return false
    end
    component = selected_meter_entry["component"]
    return _to_float(component["confidence_min_lpm"]) <= required_flow <= _to_float(component["confidence_max_lpm"])
end

function _limited_simple_paths(adjacency, source, sink; max_paths = 12, cutoff = 10)
    if !haskey(adjacency, source)
        return Any[]
    end
    paths = Any[]
    visited = Set([source])
    node_path = [source]
    link_path = String[]

    function dfs(node)
        if length(paths) >= max_paths
            return
        end
        if length(node_path) - 1 > cutoff
            return
        end
        if node == sink
            push!(paths, Dict("nodes" => copy(node_path), "link_ids" => copy(link_path)))
            return
        end
        for (next_node, link_id) in get(adjacency, node, Tuple{String, String}[])
            if next_node in visited
                continue
            end
            push!(visited, next_node)
            push!(node_path, next_node)
            push!(link_path, link_id)
            dfs(next_node)
            delete!(visited, next_node)
            pop!(node_path)
            pop!(link_path)
            if length(paths) >= max_paths
                return
            end
        end
    end

    dfs(source)
    return paths
end

function _served_route_count(route_metrics)
    return sum(_to_bool(route["feasible"]) for route in route_metrics)
end

function _average_cleaning(route_metrics)
    served = [_to_float(route["cleaning_volume_l"]) for route in route_metrics if _to_bool(route["feasible"])]
    return isempty(served) ? 0.0 : sum(served) / length(served)
end

function _cleaning_volume(component_entries)
    values = [_to_float(entry["component"]["cleaning_hold_up_l"]) for entry in component_entries]
    return isempty(values) ? 0.0 : sum(values)
end

function _sum_quality(component_entries)
    values = [_to_float(entry["component"]["quality_base_score"]) for entry in component_entries]
    return isempty(values) ? 0.0 : sum(values)
end

function _switch_count(component_entries)
    flags = [(_to_string(entry["component"]["category"]) in ("valve", "pump", "meter")) ? 1 : 0 for entry in component_entries]
    return isempty(flags) ? 0 : sum(flags)
end

function _alternate_path_count(route_requirements, adjacency)
    total = 0
    for route in route_requirements
        if !_to_bool(route["mandatory"])
            continue
        end
        paths = _limited_simple_paths(adjacency, _to_string(route["source"]), _to_string(route["sink"]); max_paths = 3, cutoff = 10)
        total += max(0, length(paths) - 1)
    end
    return total
end

_to_string(value) = String(value)
_to_bool(value) = Bool(value)
_to_float(value) = Float64(value)

end
