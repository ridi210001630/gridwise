# GridWise LLM

GridWise is an HTTP API service for smart campus energy scheduling. It
interprets natural-language operator notes with an LLM, validates the
structured directives with deterministic guardrails, applies those
directives to an energy optimization model, and validates the final
schedule before returning it.

## Architecture

``` text
Operator Notes + Energy Data
            |
            v
     Gemini LLM Interpreter
            |
            v
 Deterministic Guardrail Validator
            |
            v
       Directive Handler
            |
            v
 Mathematical Energy Optimizer
            |
            v
      Final Plan Validator
            |
            v
          HTTP API
```

## LLM and Provider

-   Provider: Google Gemini
-   Model: `gemini-3.1-flash-lite`
-   Python SDK: `google-genai`
-   Environment variable: `GEMINI_API_KEY`

The LLM is used for the actual interpretation of operator notes. It
converts each natural-language note into exactly one supported
structured directive. Deterministic validation is then applied before
the directive can affect the optimizer.

Do not commit API keys, `.env` files, or other secrets.

## Supported Directives

GridWise supports exactly these directive types:

1.  `solar_reduction`

    ``` json
    {
      "hours": [13, 14],
      "factor": 0.2
    }
    ```

2.  `minimum_battery_reserve`

    ``` json
    {
      "hours": [18, 19, 20],
      "minimum_energy_kwh": 120
    }
    ```

3.  `no_charge_window`

    ``` json
    {
      "hours": [14, 15]
    }
    ```

4.  `no_discharge_window`

    ``` json
    {
      "hours": [19, 20]
    }
    ```

5.  `max_grid_window`

    ``` json
    {
      "hours": [20, 21],
      "max_grid_kwh": 230
    }
    ```

6.  `no_op`

For `no_op`, the structured adjustment is `null` and `applies` is
`false`.

Time windows are start-inclusive and end-exclusive. For example, 2 PM to
4 PM becomes `[14, 15]`.

For `solar_reduction`, `factor` is the remaining usable solar fraction.
For example, if solar output drops to 20%, the factor is `0.2`.

## Guardrails

The deterministic validator checks that:

-   Every operator note produces exactly one interpretation.
-   `note_index` matches the original note order.
-   Only the six supported directive types are accepted.
-   `hours` contains unique ascending integers from 0 to 23.
-   `solar_reduction.factor` is finite and between 0 and 1.
-   Battery reserve is finite, non-negative, and does not exceed battery
    capacity.
-   `max_grid_kwh` is finite and non-negative.
-   Unsupported or unexpected structured fields are rejected.
-   Energy, tariff, demand, and battery parameters are not invented by
    the interpreter.

The final validator checks the optimized schedule for:

-   24 hourly entries.
-   Battery capacity and minimum-energy limits.
-   Hourly charge/discharge limits.
-   Charge/discharge/no-op action consistency.
-   Effective solar availability.
-   No-charge and no-discharge windows.
-   Active minimum battery reserves.
-   Maximum grid limits.
-   Hourly energy balance.
-   Final battery energy equal to initial battery energy.
-   Reported totals matching the hourly plan.

## Optimization

The mathematical optimizer uses PuLP to minimize total grid electricity
cost while respecting the energy and battery constraints.

The schedule contains, for every hour:

-   `hour`
-   `grid_kwh`
-   `solar_used_kwh`
-   `battery_kwh`
-   `battery_action`
-   `battery_energy_after_kwh`

The API also reports:

-   `total_grid_kwh`
-   `total_cost_bdt`
-   `peak_grid_kwh`

## API

### Health Check

``` http
GET /health
```

Example:

``` bash
curl http://localhost:8000/health
```

Response:

``` json
{
  "status": "ok"
}
```

### Optimize Energy

``` http
POST /optimize-energy
Content-Type: application/json
```

The request contains:

-   `scenario_id`
-   `operator_notes` (1 to 3 notes)
-   `hours` (exactly 24 hourly entries)
-   `battery`

Example:

``` bash
curl -X POST http://localhost:8000/optimize-energy \
  -H "Content-Type: application/json" \
  --data @test_request.json
```

The response contains:

-   `scenario_id`
-   `directive_interpretation`
-   `hourly_plan`
-   `total_grid_kwh`
-   `total_cost_bdt`
-   `peak_grid_kwh`
-   `plan_summary`

## Local Setup

Create and activate a Python virtual environment if needed, then install
dependencies:

``` bash
pip install -r requirements.txt
```

Set the Gemini API key in the shell:

``` bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

Start the API:

``` bash
python app.py
```

The service listens on:

``` text
http://localhost:8000
```

## Docker

Build the image:

``` bash
docker build -t gridwise .
```

Run the container:

``` bash
docker run -d \
  --name gridwise \
  -p 8000:8000 \
  --env GEMINI_API_KEY="$GEMINI_API_KEY" \
  gridwise
```

Check the container:

``` bash
docker ps
```

Check the API:

``` bash
curl http://localhost:8000/health
```

Stop and remove the container when needed:

``` bash
docker rm -f gridwise
```

## Testing

The repository includes tests for:

-   Directive handling: `test_directives.py`
-   Mathematical optimization: `test_optimizer.py`
-   LLM interpretation validation: `test_validator.py`
-   End-to-end integration: `integration_test.py`
-   Pipeline execution: `pipeline.py`

A sample request is provided in:

``` text
test_request.json
```

## Error Handling

The API validates malformed JSON, missing required fields, invalid
operator-note structure, invalid hour counts, invalid battery objects,
invalid LLM interpretations, and final optimization results.

Invalid client input returns an HTTP 400 response. Unexpected internal
optimization failures return an HTTP 500 response.

## Known Limitations

-   The service requires access to the configured Gemini model through
    `GEMINI_API_KEY`.
-   LLM response latency depends on the external model service.
-   The Flask development server is intended for the challenge/demo
    environment; a production deployment should use a production WSGI
    server.
-   The optimizer assumes the challenge's hourly energy model and
    battery constraints.

## Project Files

``` text
gridwise/
├── app.py
├── llm_interpreter.py
├── validator.py
├── directives.py
├── optimizer.py
├── final_validator.py
├── pipeline.py
├── integration_test.py
├── test_directives.py
├── test_optimizer.py
├── test_validator.py
├── test_request.json
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```
