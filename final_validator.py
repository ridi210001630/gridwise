import math


def validate_final_plan(data, result, constraints):
    """
    Validate the final optimized energy schedule.

    Returns:
        (True, []) if valid
        (False, [errors]) if invalid
    """

    errors = []

    hours = data.get("hours", [])
    battery = data.get("battery", {})

    plan = result.get("hourly_plan", [])

    # ---------------------------------
    # Basic checks
    # ---------------------------------

    if len(hours) != 24:
        errors.append("Input must contain exactly 24 hours.")

    if len(plan) != 24:
        errors.append("Hourly plan must contain exactly 24 entries.")

    if errors:
        return False, errors

    # ---------------------------------
    # Battery parameters
    # ---------------------------------

    capacity = battery["capacity_kwh"]
    initial_energy = battery["initial_energy_kwh"]
    minimum_energy = battery["minimum_energy_kwh"]
    max_charge = battery["max_charge_kwh_per_hour"]
    max_discharge = battery["max_discharge_kwh_per_hour"]

    previous_energy = initial_energy

    total_grid = 0.0
    total_cost = 0.0
    peak_grid = 0.0

    # ---------------------------------
    # Validate each hour
    # ---------------------------------

    for i in range(24):

        input_hour = hours[i]
        plan_hour = plan[i]

        hour = plan_hour.get("hour")

        # Hour numbering
        if hour != i:
            errors.append(
                f"Hour {i}: incorrect hour number."
            )

        demand = input_hour["demand_kwh"]
        solar = input_hour["solar_kwh"]
        tariff = input_hour["tariff_bdt_per_kwh"]

        grid = plan_hour.get("grid_kwh")
        solar_used = plan_hour.get("solar_used_kwh")
        battery_kwh = plan_hour.get("battery_kwh")
        action = plan_hour.get("battery_action")
        energy_after = plan_hour.get(
            "battery_energy_after_kwh"
        )

        # ---------------------------------
        # Numeric checks
        # ---------------------------------

        values = [
            grid,
            solar_used,
            battery_kwh,
            energy_after
        ]

        if not all(
            isinstance(v, (int, float))
            and math.isfinite(v)
            for v in values
        ):
            errors.append(
                f"Hour {hour}: invalid numeric value."
            )
            continue

        # ---------------------------------
        # Non-negative checks
        # ---------------------------------

        if grid < 0:
            errors.append(
                f"Hour {hour}: grid energy cannot be negative."
            )

        if solar_used < 0:
            errors.append(
                f"Hour {hour}: solar used cannot be negative."
            )

        # ---------------------------------
        # Solar usage
        # ---------------------------------

        effective_solar = solar

        factor = get_solar_factor(
            constraints,
            hour
        )

        if factor is not None:
            effective_solar = solar * factor

        if solar_used > effective_solar + 1e-6:
            errors.append(
                f"Hour {hour}: solar usage exceeds available solar."
            )

        # ---------------------------------
        # Battery action
        # ---------------------------------

        if action not in [
            "charge",
            "discharge",
            "idle"
        ]:
            errors.append(
                f"Hour {hour}: invalid battery action."
            )

        # Charge/discharge amount
        if battery_kwh < 0:
            errors.append(
                f"Hour {hour}: battery amount cannot be negative."
            )

        if action == "charge":

            if battery_kwh > max_charge + 1e-6:
                errors.append(
                    f"Hour {hour}: charge exceeds hourly limit."
                )

        elif action == "discharge":

            if battery_kwh > max_discharge + 1e-6:
                errors.append(
                    f"Hour {hour}: discharge exceeds hourly limit."
                )

        elif action == "idle":

            if abs(battery_kwh) > 1e-6:
                errors.append(
                    f"Hour {hour}: idle action must have zero battery flow."
                )

        # ---------------------------------
        # Battery energy limits
        # ---------------------------------

        if energy_after < minimum_energy - 1e-6:
            errors.append(
                f"Hour {hour}: battery below minimum energy."
            )

        if energy_after > capacity + 1e-6:
            errors.append(
                f"Hour {hour}: battery exceeds capacity."
            )

        # ---------------------------------
        # Battery state transition
        # ---------------------------------

        if action == "charge":

            expected_energy = (
                previous_energy + battery_kwh
            )

        elif action == "discharge":

            expected_energy = (
                previous_energy - battery_kwh
            )

        else:

            expected_energy = previous_energy

        if abs(
            energy_after - expected_energy
        ) > 1e-6:

            errors.append(
                f"Hour {hour}: incorrect battery energy transition."
            )

        # ---------------------------------
        # Energy balance
        #
        # Grid + solar + discharge
        # = demand + charge
        # ---------------------------------

        if action == "discharge":
            discharge = battery_kwh
            charge = 0.0

        elif action == "charge":
            discharge = 0.0
            charge = battery_kwh

        else:
            discharge = 0.0
            charge = 0.0

        expected_grid = (
            demand
            + charge
            - solar_used
            - discharge
        )

        if abs(grid - expected_grid) > 1e-6:

            errors.append(
                f"Hour {hour}: energy balance violation."
            )

        # ---------------------------------
        # Directive checks
        # ---------------------------------

        if (
            hour in constraints.get(
                "no_charge_hours", []
            )
            and action == "charge"
        ):
            errors.append(
                f"Hour {hour}: charging is prohibited."
            )

        if (
            hour in constraints.get(
                "no_discharge_hours", []
            )
            and action == "discharge"
        ):
            errors.append(
                f"Hour {hour}: discharging is prohibited."
            )

        minimum_reserve = get_minimum_reserve(
            constraints,
            hour
        )

        if (
            minimum_reserve is not None
            and energy_after < minimum_reserve - 1e-6
        ):
            errors.append(
                f"Hour {hour}: minimum reserve violated."
            )

        max_grid_limit = get_max_grid(
            constraints,
            hour
        )

        if (
            max_grid_limit is not None
            and grid > max_grid_limit + 1e-6
        ):
            errors.append(
                f"Hour {hour}: maximum grid limit violated."
            )

        # ---------------------------------
        # Update totals
        # ---------------------------------

        total_grid += grid
        total_cost += grid * tariff

        peak_grid = max(
            peak_grid,
            grid
        )

        previous_energy = energy_after

    # ---------------------------------
    # Final battery neutrality
    # ---------------------------------

    if abs(
        previous_energy - initial_energy
    ) > 1e-6:

        errors.append(
            "Final battery energy must equal initial battery energy."
        )

    # ---------------------------------
    # Check reported totals
    # ---------------------------------

    reported_grid = result.get(
        "total_grid_kwh"
    )

    reported_cost = result.get(
        "total_cost_bdt"
    )

    reported_peak = result.get(
        "peak_grid_kwh"
    )

    if reported_grid is None:
        errors.append(
            "Missing total_grid_kwh."
        )

    elif abs(
        reported_grid - total_grid
    ) > 1e-6:
        errors.append(
            "Reported total_grid_kwh does not match hourly plan."
        )

    if reported_cost is None:
        errors.append(
            "Missing total_cost_bdt."
        )

    elif abs(
        reported_cost - total_cost
    ) > 1e-6:
        errors.append(
            "Reported total_cost_bdt does not match hourly plan."
        )

    if reported_peak is None:
        errors.append(
            "Missing peak_grid_kwh."
        )

    elif abs(
        reported_peak - peak_grid
    ) > 1e-6:
        errors.append(
            "Reported peak_grid_kwh does not match hourly plan."
        )

    # ---------------------------------
    # Final result
    # ---------------------------------

    if errors:
        return False, errors

    return True, []


# ---------------------------------
# Helper functions
# ---------------------------------

def get_solar_factor(constraints, hour):

    for item in constraints.get(
        "solar_reductions", []
    ):

        if hour in item["hours"]:
            return item["factor"]

    return None


def get_minimum_reserve(constraints, hour):

    for item in constraints.get(
        "minimum_reserves", []
    ):

        if hour in item["hours"]:
            return item["minimum_energy_kwh"]

    return None


def get_max_grid(constraints, hour):

    for item in constraints.get(
        "max_grid_limits", []
    ):

        if hour in item["hours"]:
            return item["max_grid_kwh"]

    return None


# ---------------------------------
# Simple test
# ---------------------------------

if __name__ == "__main__":

    print("Final validator module loaded successfully.")