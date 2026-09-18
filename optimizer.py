import pulp


def optimize_energy(data, constraints=None):
    """
    GridWise 24-hour mathematical optimizer.

    Objective:
        Minimize total grid electricity cost.

    constraints:
        Optional validated directive constraints
        from directives.py.
    """

    hours = range(24)

    if constraints is None:
        constraints = {
            "solar_reductions": [],
            "no_charge_hours": [],
            "no_discharge_hours": [],
            "minimum_reserves": [],
            "max_grid_limits": []
        }

    battery_data = data["battery"]

    # ---------------------------------
    # Create optimization problem
    # ---------------------------------

    problem = pulp.LpProblem(
        "GridWise_Energy_Optimization",
        pulp.LpMinimize
    )

    # ---------------------------------
    # Decision variables
    # ---------------------------------

    grid = {
        h: pulp.LpVariable(
            f"grid_{h}",
            lowBound=0
        )
        for h in hours
    }

    solar_used = {
        h: pulp.LpVariable(
            f"solar_used_{h}",
            lowBound=0
        )
        for h in hours
    }

    charge = {
        h: pulp.LpVariable(
            f"charge_{h}",
            lowBound=0
        )
        for h in hours
    }

    discharge = {
        h: pulp.LpVariable(
            f"discharge_{h}",
            lowBound=0
        )
        for h in hours
    }

    battery_energy = {
        h: pulp.LpVariable(
            f"battery_energy_{h}",
            lowBound=0,
            upBound=battery_data["capacity_kwh"]
        )
        for h in hours
    }

    # Binary variables
    is_charge = {
        h: pulp.LpVariable(
            f"is_charge_{h}",
            cat="Binary"
        )
        for h in hours
    }

    is_discharge = {
        h: pulp.LpVariable(
            f"is_discharge_{h}",
            cat="Binary"
        )
        for h in hours
    }

    is_idle = {
        h: pulp.LpVariable(
            f"is_idle_{h}",
            cat="Binary"
        )
        for h in hours
    }

    # ---------------------------------
    # Objective
    # ---------------------------------

    problem += pulp.lpSum(
        grid[h]
        * data["hours"][h]["tariff_bdt_per_kwh"]
        for h in hours
    )

    # ---------------------------------
    # Hourly constraints
    # ---------------------------------

    for h in hours:

        demand = data["hours"][h]["demand_kwh"]
        original_solar = data["hours"][h]["solar_kwh"]

        # =================================
        # 1. Calculate effective solar
        # =================================

        solar_factor = 1.0

        for item in constraints["solar_reductions"]:

            if h in item["hours"]:
                solar_factor *= item["factor"]

        effective_solar = (
            original_solar * solar_factor
        )

        # Solar used cannot exceed
        # effective available solar
        problem += (
            solar_used[h]
            <= effective_solar
        )

        # =================================
        # 2. Energy balance
        # =================================

        problem += (
            grid[h]
            + solar_used[h]
            + discharge[h]
            == demand + charge[h]
        )

        # =================================
        # 3. Battery action
        # =================================

        problem += (
            is_charge[h]
            + is_discharge[h]
            + is_idle[h]
            == 1
        )

        # =================================
        # 4. Normal charge limit
        # =================================

        problem += (
            charge[h]
            <= battery_data["max_charge_kwh_per_hour"]
            * is_charge[h]
        )

        # =================================
        # 5. Normal discharge limit
        # =================================

        problem += (
            discharge[h]
            <= battery_data["max_discharge_kwh_per_hour"]
            * is_discharge[h]
        )

        # =================================
        # 6. No-charge directive
        # =================================

        if h in constraints["no_charge_hours"]:

            problem += (
                charge[h] == 0
            )

        # =================================
        # 7. No-discharge directive
        # =================================

        if h in constraints["no_discharge_hours"]:

            problem += (
                discharge[h] == 0
            )

        # =================================
        # 8. Battery state transition
        # =================================

        if h == 0:

            previous_energy = (
                battery_data["initial_energy_kwh"]
            )

        else:

            previous_energy = battery_energy[h - 1]

        problem += (
            battery_energy[h]
            == previous_energy
            + charge[h]
            - discharge[h]
        )

        # =================================
        # 9. Base battery minimum
        # =================================

        minimum_energy = (
            battery_data["minimum_energy_kwh"]
        )

        # =================================
        # 10. Directive battery reserve
        # =================================

        for item in constraints["minimum_reserves"]:

            if h in item["hours"]:

                minimum_energy = max(
                    minimum_energy,
                    item["minimum_energy_kwh"]
                )

        problem += (
            battery_energy[h]
            >= minimum_energy
        )

        # =================================
        # 11. Maximum grid directive
        # =================================

        for item in constraints["max_grid_limits"]:

            if h in item["hours"]:

                problem += (
                    grid[h]
                    <= item["max_grid_kwh"]
                )

    # ---------------------------------
    # End-of-day battery neutrality
    # ---------------------------------

    problem += (
        battery_energy[23]
        == battery_data["initial_energy_kwh"]
    )

    # ---------------------------------
    # Solve
    # ---------------------------------

    status = problem.solve(
        pulp.PULP_CBC_CMD(msg=False)
    )

    # ---------------------------------
    # Check solution
    # ---------------------------------

    if pulp.LpStatus[status] != "Optimal":

        raise ValueError(
            "Optimization failed: "
            + pulp.LpStatus[status]
        )

    # ---------------------------------
    # Build hourly plan
    # ---------------------------------

    hourly_plan = []

    for h in hours:

        charge_value = pulp.value(
            charge[h]
        )

        discharge_value = pulp.value(
            discharge[h]
        )

        solar_value = pulp.value(
            solar_used[h]
        )

        grid_value = pulp.value(
            grid[h]
        )

        battery_value = pulp.value(
            battery_energy[h]
        )

        # Determine action
        if charge_value > 1e-6:

            action = "charge"
            battery_action_kwh = charge_value

        elif discharge_value > 1e-6:

            action = "discharge"
            battery_action_kwh = discharge_value

        else:

            action = "idle"
            battery_action_kwh = 0

        hourly_plan.append({
            "hour": h,
            "grid_kwh": round(
                grid_value,
                4
            ),
            "solar_used_kwh": round(
                solar_value,
                4
            ),
            "battery_action": action,
            "battery_kwh": round(
                battery_action_kwh,
                4
            ),
            "battery_energy_after_kwh": round(
                battery_value,
                4
            )
        })

    # ---------------------------------
    # Total grid
    # ---------------------------------

    total_grid = sum(
        item["grid_kwh"]
        for item in hourly_plan
    )

    # ---------------------------------
    # Total cost
    # ---------------------------------

    total_cost = sum(
        hourly_plan[h]["grid_kwh"]
        * data["hours"][h]["tariff_bdt_per_kwh"]
        for h in hours
    )

    # ---------------------------------
    # Peak grid
    # ---------------------------------

    peak_grid = max(
        item["grid_kwh"]
        for item in hourly_plan
    )

    # ---------------------------------
    # Return result
    # ---------------------------------

    return {
        "hourly_plan": hourly_plan,
        "total_grid_kwh": round(
            total_grid,
            4
        ),
        "total_cost_bdt": round(
            total_cost,
            4
        ),
        "peak_grid_kwh": round(
            peak_grid,
            4
        )
    }


# ==========================================
# Test
# ==========================================

if __name__ == "__main__":

    test_data = {

        "scenario_id": "TEST-001",

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

    # Create 24 hourly entries
    for h in range(24):

        test_data["hours"].append({
            "hour": h,
            "demand_kwh": 180,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 8
        })

    result = optimize_energy(test_data)

    print("===================================")
    print("     GRIDWISE OPTIMIZER TEST")
    print("===================================")

    print(
        "\nTotal Grid:",
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

    print("\nFirst 5 hours:")

    for item in result["hourly_plan"][:5]:

        print(item)

    print("\nOptimization successful!")