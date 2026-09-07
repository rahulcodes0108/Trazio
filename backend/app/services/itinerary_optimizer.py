"""Constraint-aware itinerary optimization using OR-Tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.services.destination_scorer import DestinationScore


@dataclass(frozen=True)
class OptimizedStop:
    """A destination selected by the itinerary optimizer."""

    destination_score: DestinationScore
    sequence: int
    travel_minutes_from_previous: int
    visit_minutes: int
    entry_fee: float


@dataclass(frozen=True)
class OptimizationResult:
    """Result returned by the itinerary optimizer."""

    stops: list[OptimizedStop]
    total_travel_minutes: int
    total_visit_minutes: int
    total_duration_minutes: int
    total_cost: float


def optimize_itinerary(
    candidates: Sequence[DestinationScore],
    travel_minutes: Sequence[Sequence[int]],
    visit_durations: Sequence[int],
    entry_fees: Sequence[float],
    available_minutes: int,
    budget_amount: float | None = None,
    max_stops: int = 8,
) -> OptimizationResult:
    """
    Select and order destinations subject to itinerary constraints.

    Matrix convention:

        index 0 = trip starting location
        index 1..N = candidate destinations

    The route starts at node 0.

    The final destination does not require a return trip to
    the starting location.
    """

    candidate_count = len(candidates)

    # ---------------------------------------------------------
    # Basic validation
    # ---------------------------------------------------------

    if candidate_count == 0:
        return OptimizationResult(
            stops=[],
            total_travel_minutes=0,
            total_visit_minutes=0,
            total_duration_minutes=0,
            total_cost=0.0,
        )

    if len(visit_durations) != candidate_count:
        raise ValueError(
            "visit_durations length must match candidates"
        )

    if len(entry_fees) != candidate_count:
        raise ValueError(
            "entry_fees length must match candidates"
        )

    expected_matrix_size = candidate_count + 1

    if len(travel_minutes) != expected_matrix_size:
        raise ValueError(
            "travel_minutes must include the starting location"
        )

    if any(
        len(row) != expected_matrix_size
        for row in travel_minutes
    ):
        raise ValueError(
            "travel_minutes must be a square matrix"
        )

    if available_minutes <= 0:
        return OptimizationResult(
            stops=[],
            total_travel_minutes=0,
            total_visit_minutes=0,
            total_duration_minutes=0,
            total_cost=0.0,
        )

    max_stops = max(
        1,
        min(max_stops, candidate_count),
    )

    # ---------------------------------------------------------
    # OR-Tools routing model
    # ---------------------------------------------------------

    manager = pywrapcp.RoutingIndexManager(
        expected_matrix_size,
        1,
        0,
    )

    routing = pywrapcp.RoutingModel(manager)

    # ---------------------------------------------------------
    # Time constraint
    # ---------------------------------------------------------

    def time_callback(
        from_index: int,
        to_index: int,
    ) -> int:
        """Return travel + visit time for an arc."""

        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        # Returning to the depot is free because TRAZIO
        # itineraries do not require a return to the start.
        if to_node == 0:
            return 0

        travel = int(
            travel_minutes[from_node][to_node]
        )

        visit = int(
            visit_durations[to_node - 1]
        )

        return max(
            0,
            travel + visit,
        )

    time_callback_index = routing.RegisterTransitCallback(
        time_callback
    )

    routing.SetArcCostEvaluatorOfAllVehicles(
        time_callback_index
    )

    routing.AddDimension(
        time_callback_index,
        0,
        int(available_minutes),
        True,
        "Time",
    )

    time_dimension = routing.GetDimensionOrDie(
        "Time"
    )

    time_dimension.CumulVar(
        routing.Start(0)
    ).SetValue(0)

    # ---------------------------------------------------------
    # Budget constraint
    # ---------------------------------------------------------

    if budget_amount is not None:
        budget_cents = max(
            0,
            int(round(float(budget_amount) * 100)),
        )

        def budget_callback(
            from_index: int,
            to_index: int,
        ) -> int:
            """Return destination entry fee in cents."""

            to_node = manager.IndexToNode(to_index)

            if to_node == 0:
                return 0

            fee = entry_fees[to_node - 1]

            return max(
                0,
                int(round(float(fee) * 100)),
            )

        budget_callback_index = routing.RegisterTransitCallback(
            budget_callback
        )

        routing.AddDimension(
            budget_callback_index,
            0,
            budget_cents,
            True,
            "Budget",
        )

        budget_dimension = routing.GetDimensionOrDie(
            "Budget"
        )

        budget_dimension.CumulVar(
            routing.Start(0)
        ).SetValue(0)

    # ---------------------------------------------------------
    # Optional destinations
    # ---------------------------------------------------------

    # Every destination is optional.
    #
    # The penalty represents the value lost when a destination
    # is skipped. Higher-scoring destinations therefore have
    # larger skip penalties and are preferred by the optimizer.

    max_score = max(
        1.0,
        max(
            item.total_score
            for item in candidates
        ),
    )

    for candidate_index, candidate in enumerate(
        candidates,
        start=1,
    ):
        routing_index = manager.NodeToIndex(
            candidate_index
        )

        score_ratio = (
            candidate.total_score / max_score
        )

        penalty = int(
            round(
                1000 + (score_ratio * 9000)
            )
        )

        routing.AddDisjunction(
            [routing_index],
            penalty,
        )

    # ---------------------------------------------------------
    # Maximum number of stops
    # ---------------------------------------------------------

    active_variables = []

    for node in range(
        1,
        expected_matrix_size,
    ):
        routing_index = manager.NodeToIndex(node)

        active_variables.append(
            routing.ActiveVar(routing_index)
        )

    solver = routing.solver()

    solver.Add(
        sum(active_variables) <= max_stops
    )

    # ---------------------------------------------------------
    # Search parameters
    # ---------------------------------------------------------

    search_parameters = (
        pywrapcp.DefaultRoutingSearchParameters()
    )

    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy
        .PATH_CHEAPEST_ARC
    )

    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic
        .GUIDED_LOCAL_SEARCH
    )

    search_parameters.time_limit.FromSeconds(5)

    assignment = routing.SolveWithParameters(
        search_parameters
    )

    if assignment is None:
        return OptimizationResult(
            stops=[],
            total_travel_minutes=0,
            total_visit_minutes=0,
            total_duration_minutes=0,
            total_cost=0.0,
        )

    # ---------------------------------------------------------
    # Extract optimized route
    # ---------------------------------------------------------

    index = routing.Start(0)

    selected_nodes: list[int] = []
    travel_from_previous: list[int] = []

    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)

        next_index = assignment.Value(
            routing.NextVar(index)
        )

        if node != 0:
            selected_nodes.append(node)

        if not routing.IsEnd(next_index):
            next_node = manager.IndexToNode(
                next_index
            )

            if node == 0:
                travel = int(
                    travel_minutes[0][next_node]
                )
            else:
                travel = int(
                    travel_minutes[node][next_node]
                )

            if next_node != 0:
                travel_from_previous.append(
                    max(0, travel)
                )

        index = next_index

    # ---------------------------------------------------------
    # Build optimized stops
    # ---------------------------------------------------------

    stops: list[OptimizedStop] = []

    total_travel = 0
    total_visit = 0
    total_cost = 0.0

    for sequence, node in enumerate(
        selected_nodes,
        start=1,
    ):
        candidate_index = node - 1

        visit_minutes = max(
            0,
            int(
                visit_durations[candidate_index]
            ),
        )

        entry_fee = max(
            0.0,
            float(
                entry_fees[candidate_index]
            ),
        )

        if sequence <= len(
            travel_from_previous
        ):
            travel_minutes_value = (
                travel_from_previous[sequence - 1]
            )
        else:
            travel_minutes_value = 0

        stops.append(
            OptimizedStop(
                destination_score=(
                    candidates[candidate_index]
                ),
                sequence=sequence,
                travel_minutes_from_previous=(
                    travel_minutes_value
                ),
                visit_minutes=visit_minutes,
                entry_fee=entry_fee,
            )
        )

        total_travel += travel_minutes_value
        total_visit += visit_minutes
        total_cost += entry_fee

    return OptimizationResult(
        stops=stops,
        total_travel_minutes=total_travel,
        total_visit_minutes=total_visit,
        total_duration_minutes=(
            total_travel + total_visit
        ),
        total_cost=round(
            total_cost,
            2,
        ),
    )
