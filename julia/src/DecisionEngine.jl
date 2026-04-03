module DecisionEngine

export build_result

function build_result(payload)
    return Dict("status" => "ok", "payload" => payload)
end

end
