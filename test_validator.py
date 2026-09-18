from validator import validate_directive


battery = {
    "capacity_kwh": 200
}


def run_test(test_name, directive, note_index=0):

    errors = validate_directive(
        directive,
        note_index,
        battery
    )

    print(f"\n--- {test_name} ---")

    if errors:
        print("REJECTED")
        for error in errors:
            print("  -", error)
    else:
        print("ACCEPTED")


run_test(
    "Invalid hour 25",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {
            "hours": [24, 25]
        },
        "explanation": "Invalid hours."
    }
)


run_test(
    "Hours not ascending",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {
            "hours": [15, 14]
        },
        "explanation": "Hours are not ascending."
    }
)


run_test(
    "Solar factor greater than 1",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "solar_reduction",
        "structured_adjustment": {
            "hours": [13, 14],
            "factor": 1.5
        },
        "explanation": "Invalid factor."
    }
)


run_test(
    "Reserve greater than battery capacity",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "minimum_battery_reserve",
        "structured_adjustment": {
            "hours": [18, 19],
            "minimum_energy_kwh": 250
        },
        "explanation": "Reserve is too high."
    }
)


run_test(
    "Negative grid limit",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "max_grid_window",
        "structured_adjustment": {
            "hours": [20, 21],
            "max_grid_kwh": -10
        },
        "explanation": "Invalid grid limit."
    }
)


run_test(
    "Unsupported directive type",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "increase_grid_power",
        "structured_adjustment": {
            "hours": [10]
        },
        "explanation": "Unsupported directive."
    }
)


run_test(
    "Invalid no_op",
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": "This should be invalid."
    }
)
