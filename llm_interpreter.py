from google import genai
from google.genai import types
import os
import json
import time


def interpret_notes(operator_notes):

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    notes_text = "\n".join(
        f"Note {i}: {note}"
        for i, note in enumerate(operator_notes)
    )

    prompt = f"""
You are an operator-note interpreter for a smart campus
energy scheduling system.

Interpret EVERY operator note and convert each note into
EXACTLY ONE supported directive.

Supported directives:

1. solar_reduction
   {{
     "hours": [integer hours],
     "factor": number between 0 and 1
   }}

2. minimum_battery_reserve
   {{
     "hours": [integer hours],
     "minimum_energy_kwh": number
   }}

3. no_charge_window
   {{
     "hours": [integer hours]
   }}

4. no_discharge_window
   {{
     "hours": [integer hours]
   }}

5. max_grid_window
   {{
     "hours": [integer hours],
     "max_grid_kwh": number
   }}

6. no_op
   structured_adjustment must be null.

Rules:

- Every note must produce exactly one result.
- Keep note_index exactly equal to the note number.
- note_index starts from 0.
- Hours must be integers from 0 to 23.
- Hours must be unique and ascending.
- Time windows are start-inclusive and end-exclusive.
- Example: 2 PM to 4 PM means [14, 15].
- Example: 6 PM to 9 PM means [18, 19, 20].
- For solar_reduction, factor means the remaining usable
  solar fraction.
- Example: solar output drops to 20% means factor = 0.2.
- If the note is unrelated to energy scheduling, use no_op.
- Do not invent values.
- Do not invent energy, tariff, demand, or battery parameters.

For no_op:
applies = false
directive_type = "no_op"
structured_adjustment = null

For every other directive:
applies = true.

Return ONLY valid JSON.

The JSON must be an array containing one object
for every operator note.

Each object must have:

note_index
applies
directive_type
structured_adjustment
explanation

Operator notes:

{notes_text}
"""

    # ---------------------------------
    # Gemini API call with retry
    # ---------------------------------

    response = None

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            break

        except Exception as e:

            print(
                f"Gemini request failed. "
                f"Retrying... ({attempt + 1}/3)"
            )

            if attempt == 2:
                raise e

            time.sleep(2)

    # ---------------------------------
    # Parse JSON response
    # ---------------------------------

    result = json.loads(response.text)

    return result


# ---------------------------------
# Test
# ---------------------------------

if __name__ == "__main__":

    notes = [
        "Do not charge the battery between 2 PM and 4 PM.",
        "Keep at least 120 kWh in reserve from 6 PM until 9 PM.",
        "Do not discharge the battery between 7 PM and 9 PM.",
        "Grid usage cannot exceed 30 kWh from 8 PM to 10 PM.",
        "Solar output will drop to about 20% from 1 PM to 3 PM.",
        "The cafeteria menu changes tomorrow."
    ]

    result = interpret_notes(notes)

    print("\n=== LLM INTERPRETATIONS ===")

    print(
        json.dumps(
            result,
            indent=2
        )
    )