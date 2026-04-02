from __future__ import annotations

from typing import Iterable, List, Mapping


def prune_dominated_options(options: Iterable[Mapping]) -> List[Mapping]:
    """Conservative dominance pruning.

    Two options are only compared when they play the same structural role and
    consume the same functional category profile. This keeps pruning safe for
    the MVP, where component availability still matters globally.
    """

    candidates = list(options)
    survivors: List[Mapping] = []

    for option in candidates:
        dominated = False
        for other in candidates:
            if option is other:
                continue
            if option.get("dominance_key") != other.get("dominance_key"):
                continue

            other_cost = float(other.get("cost", 0.0))
            option_cost = float(option.get("cost", 0.0))
            other_qmin = float(other.get("q_min_lpm", 0.0))
            option_qmin = float(option.get("q_min_lpm", 0.0))
            other_qmax = float(other.get("q_max_lpm", 0.0))
            option_qmax = float(option.get("q_max_lpm", 0.0))
            other_loss = float(other.get("loss_lpm_equiv", 0.0))
            option_loss = float(option.get("loss_lpm_equiv", 0.0))

            weakly_better = (
                other_cost <= option_cost
                and other_qmin <= option_qmin
                and other_qmax >= option_qmax
                and other_loss <= option_loss
            )
            strictly_better = (
                other_cost < option_cost
                or other_qmin < option_qmin
                or other_qmax > option_qmax
                or other_loss < option_loss
            )

            if weakly_better and strictly_better:
                dominated = True
                break

        if not dominated:
            survivors.append(option)

    return survivors
