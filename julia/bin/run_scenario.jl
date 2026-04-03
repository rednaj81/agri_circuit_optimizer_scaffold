using JSON3

function safeget(dict, key, default)
    return haskey(dict, key) ? dict[key] : default
end

function build_result(payload)
    installed_links = payload["installed_links"]
    install_cost = 0.0
    fallback_cost = 0.0
    fallback_component_count = 0
    bom = Dict{String, Any}()

    for (_, link) in pairs(installed_links)
        for component in link["installed_components"]
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

    return Dict(
        "engine" => "julia_cli",
        "feasible" => true,
        "mandatory_unserved" => [],
        "install_cost" => install_cost,
        "fallback_cost" => fallback_cost,
        "quality_score_raw" => 50.0,
        "flow_out_score" => 50.0,
        "resilience_score" => 50.0,
        "cleaning_score" => 50.0,
        "operability_score" => 50.0,
        "maintenance_score" => 50.0,
        "alternate_path_count_critical" => 0,
        "fallback_component_count" => fallback_component_count,
        "bom_summary" => Dict(
            "components" => collect(values(bom)),
            "total_components" => sum(item["qty"] for item in values(bom)),
        ),
        "route_metrics" => [],
    )
end

function main()
    if length(ARGS) < 2
        error("usage: julia run_scenario.jl <input_json> <output_json>")
    end
    input_path = ARGS[1]
    output_path = ARGS[2]
    payload = JSON3.read(read(input_path, String))
    result = build_result(payload)
    open(output_path, "w") do io
        JSON3.write(io, result)
    end
end

main()
