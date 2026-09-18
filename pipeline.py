from llm_interpreter import interpret_notes
from validator import validate_interpretations
from directives import get_constraints
from optimizer import optimize_energy


def run_pipeline(operator_notes):

    print("===================================")
    print("       GRIDWISE FULL PIPELINE")
    print("===================================")

    # ---------------------------------
    # STEP 1: LLM Interpretation
    # ---------------------------------

    print("\n[1] Interpreting operator notes...")

    interpretations = interpret_notes(operator_notes)

    print("LLM interpretation completed.")

    for item in interpretations:
        print(item)

    # ---------------------------------
    # STEP 2: Validation
    # ---------------------------------

    print("\n[2] Validating interpretations...")

    battery_for_validation = {
        "capacity_kwh": 500
    }

    validation_result = validate_interpretations(
        interpretations,
        operator_notes,
        battery_for_validation
    )

    print("Validation result:")
    print(validation_result)

    if isinstance(validation_result, tuple):
        is_valid = validation_result[0]
        errors = validation_result[1]
    else:
        is_valid = validation_result
        errors = []

    if not is_valid:

        print("\n❌ Validation failed.")

        for error in errors:
            print("Error:", error)

        return None

    print("✅ Validation passed.")

    # ---------------------------------
    # STEP 3: Convert Directives
    # ---------------------------------

    print("\n[3] Converting directives into constraints...")

    constraints = get_constraints(interpretations)

    print("Constraints:")
    print(constraints)

    # ---------------------------------
    # STEP 4: Prepare Test Energy Data
    # ---------------------------------

    print("\n[4] Preparing energy data...")

    test_data = {
        "scenario_id": "PIPELINE-TEST-001",

        "operator_notes": operator_notes,

        "hours": [
            {
                "hour": h,
                "demand_kwh": 180,
                "solar_kwh": 50,
                "tariff_bdt_per_kwh": 8
            }
            for h in range(24)
        ],

        "battery": {
            "capacity_kwh": 500,
            "initial_energy_kwh": 200,
            "minimum_energy_kwh": 50,
            "max_charge_kwh_per_hour": 100,
            "max_discharge_kwh_per_hour": 100
        }
    }

    print("Energy data prepared.")

    # ---------------------------------
    # STEP 5: Run Optimizer
    # ---------------------------------

    print("\n[5] Running optimizer...")

    result = optimize_energy(
        test_data,
        constraints
    )

    print("✅ Optimization completed.")

    # ---------------------------------
    # STEP 6: Display Result
    # ---------------------------------

    print("\n===================================")
    print("       OPTIMIZATION RESULT")
    print("===================================")

    print(
        "Total Grid:",
        result["total_grid_kwh"],
        "kWh"
    )

    print(
        "Total Cost:",
        result["total_cost_bdt"],
        "BDT"
    )

    print(
        "Peak Grid:",
        result["peak_grid_kwh"],
        "kWh"
    )

    print("\nImportant Hours:")

    important_hours = [13, 14, 15, 18, 19, 20, 21]

    for hour_data in result["hourly_plan"]:

        if hour_data["hour"] in important_hours:
            print(hour_data)

    print("\n===================================")
    print("       PIPELINE COMPLETED")
    print("===================================")

    return result


# ---------------------------------
# TEST
# ---------------------------------

if __name__ == "__main__":

    notes = [
        "Do not charge the battery between 2 PM and 4 PM.",
        "Keep at least 120 kWh in reserve from 6 PM until 9 PM.",
        "Do not discharge the battery between 7 PM and 9 PM.",

        # 230 instead of 30 for a feasible integration test
        "Grid usage cannot exceed 230 kWh from 8 PM to 10 PM.",

        "Solar output will drop to about 20% from 1 PM to 3 PM.",
        "The cafeteria menu changes tomorrow."
    ]

    result = run_pipeline(notes)

    if result is not None:
        print("\nPipeline successful.")