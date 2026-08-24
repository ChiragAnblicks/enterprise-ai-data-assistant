# API Reference

Two equivalent bases, same three routes:

- **PHP REST layer** (what the React app calls): `http://localhost:8080`
- **FastAPI service directly** (for testing/debugging): `http://127.0.0.1:8000`
  — also has interactive Swagger docs at `http://127.0.0.1:8000/docs`.

The PHP layer (`backend-php/index.php`) is a pure proxy: it forwards the
method, path, and JSON body to FastAPI via `fastapi_client.php` and returns
FastAPI's response body and status code unchanged. There is no
authentication on either layer — this is a local development project, not
a deployed service.

All responses are `application/json`. All request bodies are JSON.

## GET /health

Liveness check for the PHP layer, plus a check that it can reach FastAPI.

**Request:** no body.

**Response `200`** (FastAPI reachable) or **`502`** (it isn't):

```json
{
  "php": "ok",
  "fastapi_reachable": true,
  "fastapi_base_url": "http://127.0.0.1:8000",
  "fastapi_response": { "status": "ok" }
}
```

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

## POST /ask

English question → generated SQL → executed against MySQL (read-only,
row-capped) → structured plain-English explanation of the SQL that ran.

**Request:**

```json
{ "question": "What were total sales by region last year?" }
```

**Response `200`:**

```json
{
  "question": "What were total sales by region last year?",
  "sql": "SELECT r.region_name, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100)), 2) AS revenue FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN regions r ON c.region_id = r.region_id JOIN order_items oi ON oi.order_id = o.order_id WHERE o.order_status <> 'Cancelled' AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH) GROUP BY r.region_name ORDER BY revenue DESC LIMIT 200",
  "columns": ["region_name", "revenue"],
  "rows": [
    { "region_name": "West", "revenue": 152340.50 },
    { "region_name": "East", "revenue": 98120.00 }
  ],
  "row_count": 2,
  "explanation": {
    "summary": "This returns total revenue for each sales region over the last 12 months, highest first.",
    "tables_used": ["orders", "customers", "regions", "order_items"],
    "filters": ["Excludes cancelled orders", "Only orders from the last 12 months"],
    "grouping": ["Grouped by region name"],
    "sorting": "Sorted by revenue, highest first",
    "row_limit": 200,
    "caveats": ["Freight charges are not included in this revenue figure"]
  },
  "explanation_error": null
}
```

`rows` is an array of objects keyed by column name (not an array of
arrays) — index into each row with the names in `columns`.

`explanation` is best-effort: if the LLM's explanation step fails,
`explanation` is `null` and `explanation_error` holds the reason, while
`sql`/`columns`/`rows` are still returned normally (a failed explanation
never hides a working answer).

**Error responses:**

| Status | Meaning | Example `detail` |
|---|---|---|
| `400` | Empty question | `"question must not be empty."` |
| `422` | Model refused, or its SQL failed the guard | `"Generated SQL failed the safety guard: ..."` |
| `502` | Database error, or PHP couldn't reach FastAPI at all | `"Database error: ..."` |

Error body shape (from both PHP and FastAPI):

```json
{ "detail": "human-readable reason" }
```

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8080/ask -Method Post `
  -ContentType "application/json" `
  -Body (@{ question = "How many orders are still Processing?" } | ConvertTo-Json)
```

## POST /ask-docs

Answers a question using only the policy documents in `docs/samples/`
(`ReturnPolicy.txt`, `SalesPolicy.pdf`, `WarrantyTerms.docx`), retrieved
from the Chroma vector store built by `ai-service/ingest_docs.py`.

**Request:**

```json
{ "question": "How many days do I have to return a product?" }
```

**Response `200`:**

```json
{
  "question": "How many days do I have to return a product?",
  "answer": "Per the Returns and Refunds Policy, you have 30 days from the delivery date to return a product for a full refund.",
  "sources": ["ReturnPolicy.txt"]
}
```

If the question isn't covered by any ingested document, `answer` is
literally `"I couldn't find that in the policy documents provided."` and
`sources` is `[]` — this is a normal `200` response, not an error.

Each call is independent — there is no server-side conversation history;
the React UI keeps the message thread client-side only.

**Error responses:**

| Status | Meaning | Example `detail` |
|---|---|---|
| `400` | Empty question | `"question must not be empty."` |
| `503` | Vector store not built yet, or the RAG pipeline errored | `"Document Q&A unavailable: ..."` — run `python ingest_docs.py` in `ai-service\` |

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8080/ask-docs -Method Post `
  -ContentType "application/json" `
  -Body (@{ question = "What is the warranty period for electronics?" } | ConvertTo-Json)
```

## Unmatched routes

Any method/path the PHP router doesn't recognize returns `404`:

```json
{ "detail": "No route for GET /nope" }
```
