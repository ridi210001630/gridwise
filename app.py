from flask import Flask, jsonify, request

from llm_interpreter import interpret_notes
from validator import validate_interpretations
from directives import get_constraints
from optimizer import optimize_energy
from final_validator import validate_final_plan


app = Flask(__name__)


# =================================================
# HEALTH CHECK
# =================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    }), 200


# =================================================
# OPTIMIZE ENERGY
# =================================================

@app.route("/optimize-energy", methods=["POST"])
def optimize_energy_api():

    # -------------------------------------------------
    # 1. Parse JSON safely
    # -------------------------------------------------

    try:
        data = request.get_json()

    except Exception:
        return jsonify({
            "error": "Request body must contain valid JSON."
        }), 400

    if data is None:
        return jsonify({
            "error": "Request body must contain valid JSON."
        }), 400

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    try:

        # -------------------------------------------------
        # 2. Required fields
        # -------------------------------------------------

        required_fields = [
            "scenario_id",
            "operator_notes",
            "hours",
            "battery"
        ]

        for field in required_fields:

            if field not in data:
                return jsonify({
                    "error": f"Missing required field: {field}"
                }), 400

        # -------------------------------------------------
        # 3. Validate operator_notes
        # -------------------------------------------------

        operator_notes = data["operator_notes"]

        if not isinstance(operator_notes, list):
            return jsonify({
                "error": "operator_notes must be a list."
            }), 400

        if not (1 <= len(operator_notes) <= 3):
            return jsonify({
                "error": (
                    "operator_notes must contain "
                    "1 to 3 notes."
                )
            }), 400

        # Every note must be a string
        for i, note in enumerate(operator_notes):

            if not isinstance(note, str):
                return jsonify({
                    "error": (
                        f"operator_notes[{i}] "
                        "must be a string."
                    )
                }), 400

            if not note.strip():
                return jsonify({
                    "error": (
                        f"operator_notes[{i}] "
                        "cannot be empty."
                    )
                }), 400

        # -------------------------------------------------
        # 4. Validate hours
        # -------------------------------------------------

        if not isinstance(data["hours"], list):
            return jsonify({
                "error": "hours must be a list."
            }), 400

        if len(data["hours"]) != 24:
            return jsonify({
                "error": (
                    "hours must contain exactly "
                    "24 entries."
                )
            }), 400

        # -------------------------------------------------
        # 5. Validate battery object
        # -------------------------------------------------

        if not isinstance(data["battery"], dict):
            return jsonify({
                "error": "battery must be an object."
            }), 400

        # -------------------------------------------------
        # 6. LLM interpretation
        # -------------------------------------------------

        interpretations = interpret_notes(
            operator_notes
        )

        # -------------------------------------------------
        # 7. Validate LLM output
        # -------------------------------------------------

        validation_result = validate_interpretations(
            interpretations,
            operator_notes,
            data["battery"]
        )

        if isinstance(validation_result, tuple):

            is_valid = validation_result[0]
            errors = validation_result[1]

        else:

            is_valid = validation_result
            errors = []

        if not is_valid:

            return jsonify({
                "error": "Invalid LLM interpretation.",
                "details": errors
            }), 400

        # -------------------------------------------------
        # 8. Convert directives into constraints
        # -------------------------------------------------

        constraints = get_constraints(
            interpretations
        )

        # -------------------------------------------------
        # 9. Run mathematical optimizer
        # -------------------------------------------------

        result = optimize_energy(
            data,
            constraints
        )

        # -------------------------------------------------
        # 10. Final validation
        # -------------------------------------------------

        final_validation = validate_final_plan(
            data,
            result,
            constraints
        )

        final_valid = final_validation[0]
        final_errors = final_validation[1]

        if not final_valid:

            print(
                "FINAL VALIDATION ERROR:",
                final_errors
            )

            return jsonify({
                "error": (
                    "Final optimized plan "
                    "failed validation."
                ),
                "details": final_errors
            }), 500

        # -------------------------------------------------
        # 11. Build final API response
        # -------------------------------------------------

        response = {
            "scenario_id": data["scenario_id"],

            "directive_interpretation": (
                interpretations
            ),

            "hourly_plan": (
                result["hourly_plan"]
            ),

            "total_grid_kwh": (
                result["total_grid_kwh"]
            ),

            "total_cost_bdt": (
                result["total_cost_bdt"]
            ),

            "peak_grid_kwh": (
                result["peak_grid_kwh"]
            ),

            "plan_summary": (
                "Energy schedule optimized "
                "successfully using the "
                "interpreted operator directives."
            )
        }

        return jsonify(response), 200

    # -------------------------------------------------
    # 12. Unexpected internal error
    # -------------------------------------------------

    except Exception as e:

        print(
            "API INTERNAL ERROR:",
            type(e).__name__,
            str(e)
        )

        return jsonify({
            "error": "Optimization failed."
        }), 500


# =================================================
# RUN SERVER
# =================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False
    )