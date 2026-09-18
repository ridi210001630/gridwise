from optimizer import optimize_energy
from directives import get_constraints


# ==========================================
# Test scenario
# ==========================================

test_data = {
    "scenario_id": "DIRECTIVE-TEST-001",

    "operator_notes": [],

    "hours": [],

    "battery": {
        "capacity_kwh": 500,
        "initial_energy_kwh": 200,
        "minimum_energy_kwh": 50,
        "max_charge_kwh_per_hour": 100,
        "max_discharge_kwh_per_hour": 100
    }
}


# ==========================================
# Create 24 hours
# ==========================================

for h in range(24):

    test_data["hours"].append({
        "hour": h,
        "demand_kwh": 180,
        "solar_kwh": 50,
        "tariff_bdt_per_kwh": 8
    })


# ==========================================
# Directives from Person 2
# ==========================================

interpretations = [

    {
        "note_index": 0,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {
            "hours": [14, 15]
        },
        "explanation": "No charging."
    },

    {
        "note_index": 1,
        "applies": True,
        "directive_type": "minimum_battery_reserve",
        "structured_adjustment": {
            "hours": [18, 19, 20],
            "minimum_energy_kwh": 120
        },
        "explanation": "Maintain reserve."
    },

    {
        "note_index": 2,
        "applies": True,
        "directive_type": "no_discharge_window",
        "structured_adjustment": {
            "hours": [19, 20]
        },
        "explanation": "No discharge."
    },

    {
        "note_index": 3,
        "applies": True,
        "directive_type": "max_grid_window",
        "structured_adjustment": {
            "hours": [20, 21],
            "max_grid_kwh": 230
        },
        "explanation": "Limit grid."
    },

    {
        "note_index": 4,
        "applies": True,
        "directive_type": "solar_reduction",
        "structured_adjustment": {
            "hours": [13, 14],
            "factor": 0.2
        },
        "explanation": "Reduce solar."
    }
]


# ==========================================
# Convert directives to constraints
# ==========================================

constraints = get_constraints(
    interpretations
)


print("===================================")
print("   DIRECTIVE OPTIMIZER TEST")
print("===================================")

print("\nConstraints:")
print(constraints)


# ==========================================
# Run optimizer WITH constraints
# ==========================================

result = optimize_energy(
    test_data,
    constraints
)


# ==========================================
# Display result
# ==========================================

print("\nOptimization successful!")

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


# ==========================================
# Show important directive hours
# ==========================================

print("\nImportant Hours:")
print("-----------------------------------")

for h in [13, 14, 15, 18, 19, 20, 21]:

    item = result["hourly_plan"][h]

    print(item)


print("-----------------------------------")
print("Directive optimizer test completed.")