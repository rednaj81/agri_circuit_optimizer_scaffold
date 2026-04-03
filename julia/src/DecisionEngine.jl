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
    all_components = Any[]
    install_cost = 0.0
    fallback_cost = 0.0
    fallback_component_count = 0
    bom = Dict{String, Any}()

    for (_, link) in pairs(installed_links)
        for component in link["installed_components"]
            push!(all_components, component)
            install_cost += Float64(component["cost"])
            if Bool(component["is_fallback"])
                fallback_cost += Float64(component["cost"])
                fallback_component_count += 1
            end
            component_id = String(component["component_id"])
            if !haskey(bom, component_id)
                bom[component_id] = Dict(
                    "component_id" => component_id,
                    "category" => String(component["category"]),
                    "qty" => 0,
                    "total_cost" => 0.0,
                )
            end
            bom[component_id]["qty"] += 1
            bom[component_id]["total_cost"] += Float64(component["cost"])
        end
    end

    pumps = [component for component in all_components if String(component["category"]) == "pump"]
    meters = [component for component in all_components if String(component["category"]) == "meter"]
    path_quality = sum(Float64(component["quality_base_score"]) for component in all_components)
    route_metrics = Any[]
    mandatory_unserved = String[]

    for route in route_requirements
        required_flow = Float64(route["q_min_delivered_lpm"])
        selected_meter = nothing
        for meter in meters
            if Float64(meter["hard_min_lpm"]) <= required_flow <= Float64(meter["hard_max_lpm"])
                selected_meter = meter
                break
            end
        end
        feasible = !isempty(pumps) && (!Bool(route["measurement_required"]) || selected_meter !== nothing)
        if Bool(route["mandatory"]) && !feasible
            push!(mandatory_unserved, String(route["route_id"]))
        end
        push!(
            route_metrics,
            Dict(
                "route_id" => String(route["route_id"]),
                "source" => String(route["source"]),
                "sink" => String(route["sink"]),
                "mandatory" => Bool(route["mandatory"]),
                "route_group" => String(route["route_group"]),
                "feasible" => feasible,
                "reason" => feasible ? "ok" : "native_julia_incomplete",
                "path_nodes" => String[],
                "path_link_ids" => String[],
                "active_pump_count" => isempty(pumps) ? 0 : 1,
                "passive_reverse_pump_count" => max(0, length(pumps) - 1),
                "series_pump_count" => length(pumps),
                "selected_meter_id" => selected_meter === nothing ? nothing : String(selected_meter["component_id"]),
                "flow_within_meter_confidence" => selected_meter === nothing ? false :
                    Float64(selected_meter["confidence_min_lpm"]) <= required_flow <= Float64(selected_meter["confidence_max_lpm"]),
                "cleaning_volume_l" => sum(Float64(component["cleaning_hold_up_l"]) for component in all_components),
                "component_switch_count" => sum(String(component["category"]) in ("valve", "pump", "meter") for component in all_components),
                "fallback_component_count" => fallback_component_count,
                "used_fallback_pump" => any(Bool(component["is_fallback"]) for component in pumps),
                "used_fallback_meter" => selected_meter === nothing ? false : Bool(selected_meter["is_fallback"]),
                "delivered_flow_lpm" => isempty(pumps) ? 0.0 : minimum([required_flow, maximum(Float64(component["hard_max_lpm"]) for component in pumps)]),
                "required_flow_lpm" => required_flow,
                "quality_score_base" => path_quality,
                "quality_score" => path_quality,
                "operability_score" => max(0.0, 100.0 - length(all_components) * 2),
                "flow_score" => feasible ? 100.0 : 0.0,
                "component_ids_on_path" => [String(component["component_id"]) for component in all_components],
            ),
        )
    end

    feasible = isempty(mandatory_unserved)
    quality_score_raw = isempty(route_metrics) ? 0.0 : sum(Float64(route["quality_score_base"]) for route in route_metrics) / length(route_metrics)
    flow_out_score = isempty(route_metrics) ? 0.0 : sum(Float64(route["flow_score"]) for route in route_metrics) / length(route_metrics)
    operability_score = isempty(route_metrics) ? 0.0 : sum(Float64(route["operability_score"]) for route in route_metrics) / length(route_metrics)

    return Dict(
        "engine" => "watermodels_jl",
        "feasible" => feasible,
        "mandatory_unserved" => mandatory_unserved,
        "install_cost" => install_cost,
        "fallback_cost" => fallback_cost,
        "quality_score_raw" => quality_score_raw,
        "flow_out_score" => flow_out_score,
        "resilience_score" => feasible ? 75.0 : 10.0,
        "cleaning_score" => max(0.0, 100.0 - sum(Float64(component["cleaning_hold_up_l"]) for component in all_components) * 10),
        "operability_score" => operability_score,
        "maintenance_score" => max(0.0, 100.0 - length(all_components) * 1.5),
        "alternate_path_count_critical" => 0,
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

end
