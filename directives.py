def get_constraints(interpretations):
    """
    Convert validated directive interpretations into
    deterministic constraints for the optimizer.
    """

    constraints = {
        "solar_reductions": [],
        "no_charge_hours": [],
        "no_discharge_hours": [],
        "minimum_reserves": [],
        "max_grid_limits": []
    }

    for item in interpretations:

        if not item["applies"]:
            continue

        directive_type = item["directive_type"]
        adjustment = item["structured_adjustment"]

        if directive_type == "solar_reduction":
            constraints["solar_reductions"].append({
                "hours": adjustment["hours"],
                "factor": adjustment["factor"]
            })

        elif directive_type == "minimum_battery_reserve":
            constraints["minimum_reserves"].append({
                "hours": adjustment["hours"],
                "minimum_energy_kwh": adjustment["minimum_energy_kwh"]
            })

        elif directive_type == "no_charge_window":
            constraints["no_charge_hours"].extend(
                adjustment["hours"]
            )

        elif directive_type == "no_discharge_window":
            constraints["no_discharge_hours"].extend(
                adjustment["hours"]
            )

        elif directive_type == "max_grid_window":
            constraints["max_grid_limits"].append({
                "hours": adjustment["hours"],
                "max_grid_kwh": adjustment["max_grid_kwh"]
            })

    # Remove duplicate hours and keep them sorted
    constraints["no_charge_hours"] = sorted(
        set(constraints["no_charge_hours"])
    )

    constraints["no_discharge_hours"] = sorted(
        set(constraints["no_discharge_hours"])
    )

    return constraints


def is_no_charge_hour(hour, constraints):
    """
    Check whether battery charging is prohibited
    during this hour.
    """
    return hour in constraints["no_charge_hours"]


def is_no_discharge_hour(hour, constraints):
    """
    Check whether battery discharging is prohibited
    during this hour.
    """
    return hour in constraints["no_discharge_hours"]


def get_minimum_reserve(hour, constraints):
    """
    Return the minimum battery energy required
    during this hour.
    """

    reserve = 0

    for item in constraints["minimum_reserves"]:

        if hour in item["hours"]:
            reserve = max(
                reserve,
                item["minimum_energy_kwh"]
            )

    return reserve


def get_max_grid(hour, constraints):
    """
    Return the maximum allowed grid usage
    during this hour.

    If there is no grid limit, return None.
    """

    max_grid = None

    for item in constraints["max_grid_limits"]:

        if hour in item["hours"]:

            if max_grid is None:
                max_grid = item["max_grid_kwh"]

            else:
                max_grid = min(
                    max_grid,
                    item["max_grid_kwh"]
                )

    return max_grid


def get_solar_factor(hour, constraints):
    """
    Return the usable solar factor for this hour.

    Default factor = 1.0
    """

    factor = 1.0

    for item in constraints["solar_reductions"]:

        if hour in item["hours"]:
            factor *= item["factor"]

    return factor


if __name__ == "__main__":

    # Test data
    test_interpretations = [

        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {
                "hours": [14, 15]
            },
            "explanation": "Do not charge during 14:00-16:00."
        },

        {
            "note_index": 1,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {
                "hours": [18, 19, 20],
                "minimum_energy_kwh": 120
            },
            "explanation": "Keep at least 120 kWh."
        },

        {
            "note_index": 2,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {
                "hours": [19, 20]
            },
            "explanation": "Do not discharge."
        },

        {
            "note_index": 3,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {
                "hours": [20, 21],
                "max_grid_kwh": 30
            },
            "explanation": "Grid usage cannot exceed 30 kWh."
        },

        {
            "note_index": 4,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {
                "hours": [13, 14],
                "factor": 0.2
            },
            "explanation": "Solar availability is reduced."
        },

        {
            "note_index": 5,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "No operational change."
        }
    ]

    # Convert directives into constraints
    result = get_constraints(test_interpretations)

    print("Constraints:")
    print(result)

    print()

    # Test helper functions
    print(
        "Hour 14 no charge:",
        is_no_charge_hour(14, result)
    )

    print(
        "Hour 19 no discharge:",
        is_no_discharge_hour(19, result)
    )

    print(
        "Hour 19 minimum reserve:",
        get_minimum_reserve(19, result)
    )

    print(
        "Hour 20 max grid:",
        get_max_grid(20, result)
    )

    print(
        "Hour 13 solar factor:",
        get_solar_factor(13, result)
    )