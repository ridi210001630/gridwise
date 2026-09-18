from llm_interpreter import interpret_notes
from validator import validate_interpretations
from directives import get_constraints


def test_full_pipeline():

    print("===================================")
    print("      GRIDWISE INTEGRATION TEST")
    print("===================================")

    # ---------------------------------
    # 1. Operator notes
    # ---------------------------------

    notes = [
        "Do not charge the battery between 2 PM and 4 PM.",
        "Keep at least 120 kWh in reserve from 6 PM until 9 PM.",
        "Do not discharge the battery between 7 PM and 9 PM.",
        "Grid usage cannot exceed 30 kWh from 8 PM to 10 PM.",
        "Solar output will drop to about 20% from 1 PM to 3 PM.",
        "The cafeteria menu changes tomorrow."
    ]

    print("\n[1] Operator notes received")


    # ---------------------------------
    # 2. LLM interpretation
    # ---------------------------------

    interpretations = interpret_notes(notes)

    print("[2] LLM interpretation completed")


    # ---------------------------------
    # 3. Validation
    # ---------------------------------

    battery = {
        "capacity_kwh": 200
    }

    validation_result = validate_interpretations(
        interpretations,
        notes,
        battery
    )

    is_valid = validation_result[0]

    print("[3] Validation completed")

    if not is_valid:

        print("\n❌ VALIDATION FAILED")

        for error in validation_result[1]:
            print(" -", error)

        return False


    # ---------------------------------
    # 4. Convert directives
    # ---------------------------------

    constraints = get_constraints(
        interpretations
    )

    print("[4] Directive conversion completed")


    # ---------------------------------
    # 5. Basic checks
    # ---------------------------------

    expected_no_charge = [14, 15]
    expected_no_discharge = [19, 20]

    if constraints["no_charge_hours"] != expected_no_charge:
        print("❌ No-charge hours test failed")
        return False

    if constraints["no_discharge_hours"] != expected_no_discharge:
        print("❌ No-discharge hours test failed")
        return False

    if get_minimum_reserve_from_constraints(
        constraints,
        19
    ) != 120:
        print("❌ Minimum reserve test failed")
        return False

    if get_max_grid_from_constraints(
        constraints,
        20
    ) != 30:
        print("❌ Max grid test failed")
        return False

    if get_solar_factor_from_constraints(
        constraints,
        13
    ) != 0.2:
        print("❌ Solar factor test failed")
        return False


    # ---------------------------------
    # 6. Success
    # ---------------------------------

    print("\n===================================")
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("===================================")

    return True


def get_minimum_reserve_from_constraints(
    constraints,
    hour
):

    reserve = 0

    for item in constraints["minimum_reserves"]:

        if hour in item["hours"]:

            reserve = max(
                reserve,
                item["minimum_energy_kwh"]
            )

    return reserve


def get_max_grid_from_constraints(
    constraints,
    hour
):

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


def get_solar_factor_from_constraints(
    constraints,
    hour
):

    factor = 1.0

    for item in constraints["solar_reductions"]:

        if hour in item["hours"]:
            factor *= item["factor"]

    return factor


if __name__ == "__main__":

    test_full_pipeline()