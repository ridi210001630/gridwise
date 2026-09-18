import math


ALLOWED_DIRECTIVES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def is_valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_hours(hours):
    if not isinstance(hours, list):
        return False, "hours must be a list"

    if len(hours) == 0:
        return False, "hours cannot be empty"

    # Every hour must be an integer from 0 to 23
    if any(
        not isinstance(h, int)
        or isinstance(h, bool)
        or h < 0
        or h > 23
        for h in hours
    ):
        return False, "hours must be unique integers from 0 to 23"

    # Must be unique
    if len(hours) != len(set(hours)):
        return False, "hours must be unique"

    # Must be ascending
    if hours != sorted(hours):
        return False, "hours must be in ascending order"

    return True, ""


def validate_directive(item, note_index, battery):
    """
    Validate one directive interpretation.
    """

    # -------------------------------------------------
    # 1. Directive must be an object
    # -------------------------------------------------

    if not isinstance(item, dict):
        return False, "directive must be an object"

    # -------------------------------------------------
    # 2. Required fields
    # -------------------------------------------------

    required_fields = {
        "note_index",
        "applies",
        "directive_type",
        "structured_adjustment",
        "explanation",
    }

    if not required_fields.issubset(item.keys()):
        return False, "missing required field"

    # -------------------------------------------------
    # 3. Note mapping
    # -------------------------------------------------

    if item["note_index"] != note_index:
        return False, "note_index does not match"

    # -------------------------------------------------
    # 4. Directive type
    # -------------------------------------------------

    directive_type = item["directive_type"]

    if directive_type not in ALLOWED_DIRECTIVES:
        return False, f"unsupported directive_type: {directive_type}"

    # -------------------------------------------------
    # 5. Explanation
    # -------------------------------------------------

    if not isinstance(item["explanation"], str):
        return False, "explanation must be a string"

    # -------------------------------------------------
    # 6. no_op
    # -------------------------------------------------

    if directive_type == "no_op":

        if item["applies"] is not False:
            return False, "no_op must have applies=false"

        if item["structured_adjustment"] is not None:
            return False, "no_op must have structured_adjustment=null"

        return True, ""

    # -------------------------------------------------
    # 7. Other directives must apply
    # -------------------------------------------------

    if item["applies"] is not True:
        return False, "applicable directive must have applies=true"

    adjustment = item["structured_adjustment"]

    if not isinstance(adjustment, dict):
        return False, "structured_adjustment must be an object"

    # -------------------------------------------------
    # 8. Reject unexpected fields
    # -------------------------------------------------

    allowed_adjustment_fields = {
        "hours"
    }

    if directive_type == "solar_reduction":
        allowed_adjustment_fields.add("factor")

    elif directive_type == "minimum_battery_reserve":
        allowed_adjustment_fields.add("minimum_energy_kwh")

    elif directive_type == "max_grid_window":
        allowed_adjustment_fields.add("max_grid_kwh")

    elif directive_type in {
        "no_charge_window",
        "no_discharge_window",
    }:
        pass

    extra_fields = (
        set(adjustment.keys())
        - allowed_adjustment_fields
    )

    if extra_fields:
        return False, (
            "structured_adjustment contains unexpected fields: "
            + ", ".join(sorted(extra_fields))
        )

    # -------------------------------------------------
    # 9. Validate hours
    # -------------------------------------------------

    if "hours" not in adjustment:
        return False, "structured_adjustment must contain hours"

    valid, message = validate_hours(
        adjustment["hours"]
    )

    if not valid:
        return False, message

    # -------------------------------------------------
    # 10. solar_reduction
    # -------------------------------------------------

    if directive_type == "solar_reduction":

        if "factor" not in adjustment:
            return False, "solar_reduction requires factor"

        factor = adjustment["factor"]

        if not is_valid_number(factor):
            return False, "factor must be a finite number"

        if factor < 0 or factor > 1:
            return False, "factor must be between 0 and 1"

    # -------------------------------------------------
    # 11. minimum_battery_reserve
    # -------------------------------------------------

    elif directive_type == "minimum_battery_reserve":

        if "minimum_energy_kwh" not in adjustment:
            return False, (
                "minimum_battery_reserve requires "
                "minimum_energy_kwh"
            )

        reserve = adjustment["minimum_energy_kwh"]

        if not is_valid_number(reserve):
            return False, (
                "minimum_energy_kwh must be a finite number"
            )

        if reserve < 0:
            return False, (
                "minimum_energy_kwh cannot be negative"
            )

        capacity = battery.get("capacity_kwh")

        if not is_valid_number(capacity):
            return False, "battery capacity is invalid"

        if reserve > capacity:
            return False, (
                "minimum reserve cannot exceed "
                "battery capacity"
            )

    # -------------------------------------------------
    # 12. max_grid_window
    # -------------------------------------------------

    elif directive_type == "max_grid_window":

        if "max_grid_kwh" not in adjustment:
            return False, (
                "max_grid_window requires max_grid_kwh"
            )

        max_grid = adjustment["max_grid_kwh"]

        if not is_valid_number(max_grid):
            return False, (
                "max_grid_kwh must be a finite number"
            )

        if max_grid < 0:
            return False, (
                "max_grid_kwh cannot be negative"
            )

    # -------------------------------------------------
    # 13. no_charge_window /
    #     no_discharge_window
    # -------------------------------------------------

    elif directive_type in {
        "no_charge_window",
        "no_discharge_window",
    }:
        pass

    return True, ""


def validate_interpretations(
    interpretations,
    operator_notes,
    battery
):
    """
    Validate all LLM interpretations.
    """

    errors = []

    # -------------------------------------------------
    # One interpretation per note
    # -------------------------------------------------

    if len(interpretations) != len(operator_notes):

        errors.append(
            f"Expected {len(operator_notes)} "
            f"interpretations, "
            f"got {len(interpretations)}"
        )

        return False, errors

    # -------------------------------------------------
    # Validate each interpretation
    # -------------------------------------------------

    for i, item in enumerate(interpretations):

        valid, message = validate_directive(
            item,
            i,
            battery
        )

        if not valid:

            errors.append(
                f"Note {i}: {message}"
            )

    # -------------------------------------------------
    # Final validation result
    # -------------------------------------------------

    if errors:
        return False, errors

    return True, []


# -------------------------------------------------
# Simple Test
# -------------------------------------------------

if __name__ == "__main__":

    operator_notes = [
        "Do not charge the battery between 2 PM and 4 PM.",
        "Keep at least 120 kWh in reserve from 6 PM until 9 PM.",
        "The cafeteria menu changes tomorrow."
    ]

    battery = {
        "capacity_kwh": 500,
        "initial_energy_kwh": 200,
        "minimum_energy_kwh": 50,
        "max_charge_kwh_per_hour": 100,
        "max_discharge_kwh_per_hour": 100
    }

    interpretations = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {
                "hours": [14, 15]
            },
            "explanation": (
                "Charging is not allowed during "
                "these hours."
            )
        },
        {
            "note_index": 1,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {
                "hours": [18, 19, 20],
                "minimum_energy_kwh": 120
            },
            "explanation": (
                "Battery must maintain at least "
                "120 kWh."
            )
        },
        {
            "note_index": 2,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": (
                "This note is unrelated to "
                "energy scheduling."
            )
        }
    ]

    valid, errors = validate_interpretations(
        interpretations,
        operator_notes,
        battery
    )

    print("VALID:", valid)

    if errors:
        print("ERRORS:")

        for error in errors:
            print("-", error)