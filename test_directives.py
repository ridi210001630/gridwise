from directives import (
    get_constraints,
    is_no_charge_hour,
    is_no_discharge_hour,
    get_minimum_reserve,
    get_max_grid,
    get_solar_factor
)


# -----------------------------
# Test interpretations
# -----------------------------

interpretations = [
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {
            "hours": [14, 15]
        },
        "explanation": "No charging during these hours."
    },

    {
        "note_index": 1,
        "applies": True,
        "directive_type": "minimum_battery_reserve",
        "structured_adjustment": {
            "hours": [18, 19, 20],
            "minimum_energy_kwh": 120
        },
        "explanation": "Keep minimum battery reserve."
    },

    {
        "note_index": 2,
        "applies": True,
        "directive_type": "no_discharge_window",
        "structured_adjustment": {
            "hours": [19, 20]
        },
        "explanation": "No battery discharge."
    },

    {
        "note_index": 3,
        "applies": True,
        "directive_type": "max_grid_window",
        "structured_adjustment": {
            "hours": [20, 21],
            "max_grid_kwh": 30
        },
        "explanation": "Limit grid usage."
    },

    {
        "note_index": 4,
        "applies": True,
        "directive_type": "solar_reduction",
        "structured_adjustment": {
            "hours": [13, 14],
            "factor": 0.2
        },
        "explanation": "Reduce usable solar."
    }
]


# -----------------------------
# Convert into constraints
# -----------------------------

constraints = get_constraints(interpretations)

print("=== DIRECTIVE TEST ===")
print()


# -----------------------------
# Test 1: No Charge
# -----------------------------

print("Test 1: No Charge")

for hour in [13, 14, 15, 16]:
    result = is_no_charge_hour(hour, constraints)
    print(f"Hour {hour}: {result}")

print()


# -----------------------------
# Test 2: No Discharge
# -----------------------------

print("Test 2: No Discharge")

for hour in [18, 19, 20, 21]:
    result = is_no_discharge_hour(hour, constraints)
    print(f"Hour {hour}: {result}")

print()


# -----------------------------
# Test 3: Minimum Battery Reserve
# -----------------------------

print("Test 3: Minimum Battery Reserve")

for hour in [17, 18, 19, 20, 21]:
    result = get_minimum_reserve(hour, constraints)
    print(f"Hour {hour}: {result} kWh")

print()


# -----------------------------
# Test 4: Maximum Grid
# -----------------------------

print("Test 4: Maximum Grid")

for hour in [19, 20, 21, 22]:
    result = get_max_grid(hour, constraints)
    print(f"Hour {hour}: {result}")

print()


# -----------------------------
# Test 5: Solar Factor
# -----------------------------

print("Test 5: Solar Factor")

for hour in [12, 13, 14, 15]:
    result = get_solar_factor(hour, constraints)
    print(f"Hour {hour}: {result}")

print()


print("=== ALL TESTS COMPLETED ===")