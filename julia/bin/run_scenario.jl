using JSON3

include(joinpath(@__DIR__, "..", "src", "DecisionEngine.jl"))
using .DecisionEngine

function main()
    if length(ARGS) < 2
        error("usage: julia run_scenario.jl <input_json> <output_json>")
    end
    input_path = ARGS[1]
    output_path = ARGS[2]
    payload = JSON3.read(read(input_path, String))
    result = payload isa AbstractVector ? build_results(payload) : build_result(payload)
    open(output_path, "w") do io
        JSON3.write(io, result)
    end
end

main()
