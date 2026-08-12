# FastAPI Application with Supabase Auth Integration & LLM Pipeline (Assignment A17)

A production-ready FastAPI web application integrated with Supabase for user authentication and an OpenAI-compatible **LLM Task Execution & Response Pipeline**.

---

## 1. Project & LLM Pipeline Overview

The LLM Task Execution & Response Pipeline processes structured input tasks, performs LLM inference via an OpenAI-compatible API provider (e.g., OpenRouter, OpenAI, or Ollama), and returns validated, structured JSON outputs.

### Key Pipeline Features:
- **Externalized Versioned Prompt**: Prompt instructions versioned in [`prompts/task-execution-v1.md`](./prompts/task-execution-v1.md).
- **Pydantic Validation & Repair Loop**: Cleans raw response markdown code blocks and validates with Pydantic (`model_validate_json`). Automatically executes 1 repair retry on schema validation failure.
- **Quarantine Logging**: Quarantines persistent validation failures to [`logs/quarantine.jsonl`](./logs/quarantine.jsonl) and returns `HTTP 422 Unprocessable Entity`.
- **Production Hardening**:
  - 30-second explicit client timeout (`HTTP 504 Gateway Timeout` on expiration).
  - Exponential backoff & jitter retries strictly for timeouts, HTTP 429, and 5xx errors (never on 400/401/403).
  - Structured telemetry logging (model, prompt version, input/output token counts, latency ms, repair status).
  - Feature Kill Switch via `LLM_ENABLED=false` (`HTTP 503 Service Unavailable`).

---

## 2. Job Card Summary (Assignment A17)

- **Purpose**: Process structured task inputs, perform LLM inference, and return validated structured JSON responses adhering strictly to the schema while handling uncertainties via fallback logic.
- **Input JSON Schema**:
  ```json
  {
    "task_id": "string (unique identifier for the task)",
    "prompt": "string (the primary instruction or user query)",
    "context": "optional string or object (additional context data)",
    "temperature": "optional float (sampling temperature, default 0.0)"
  }
  ```
- **Output JSON Schema**:
  ```json
  {
    "task_id": "string (matches input task_id)",
    "status": "string ('success' | 'fallback' | 'error')",
    "result": "string or object (the generated output response)",
    "confidence": "float (confidence score between 0.0 and 1.0)",
    "error_message": "nullable string (present only if status is fallback or error)"
  }
  ```
- **Strict Rules ("Must Never")**:
  - **MUST NEVER** return unparsed raw text outside JSON.
  - **MUST NEVER** expose sensitive credentials, API keys, or internal system paths.
  - **MUST NEVER** execute arbitrary unvalidated shell commands.
  - **MUST NEVER** retry indefinitely on client authentication errors (HTTP 401/403).
- **Fallback Behavior**: Uncertainties, missing context, or unparseable model responses set `"status": "fallback"`, `"confidence": 0.0`, and populate `"error_message"`.

---

## 3. Provider & Model Configuration

- **API Provider**: OpenRouter / OpenAI-compatible API (`https://openrouter.ai/api/v1`)
- **LLM Model**: `openrouter/free` (configurable via `LLM_MODEL`)
- **Prompt Version**: `v1` ([`prompts/task-execution-v1.md`](./prompts/task-execution-v1.md))
- **Environment Variables**:
  ```env
  LLM_BASE_URL=https://openrouter.ai/api/v1
  LLM_API_KEY=sk-or-v1-...
  LLM_MODEL=openrouter/free
  LLM_ENABLED=true
  LLM_STUB=false
  PROMPT_FILE_PATH=prompts/task-execution-v1.md
  ```
  > **Security Note**: `.env` is listed in `.gitignore` and is absent from git repository history.

---

## 4. Endpoint Usage & `curl` Examples

### LLM Task Execution (`POST /task/execute`)

```bash
curl -i -X POST http://localhost:8000/task/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo-task-101",
    "prompt": "Summarize the key benefit of FastAPI.",
    "context": "FastAPI is a modern, fast Python web framework based on standard Python type hints.",
    "temperature": 0.0
  }'
```

**Example Response (`200 OK`):**
```json
{
  "task_id": "demo-task-101",
  "status": "success",
  "result": "FastAPI is a modern, high-performance Python web framework that enables rapid API development using standard Python type hints.",
  "confidence": 0.95,
  "error_message": null
}
```

---

## 5. Evaluation Benchmark & Results

The evaluation runner ([`src/llm/eval.py`](./src/llm/eval.py)) executes 8 hand-labeled benchmark cases ([`evals/cases.json`](./evals/cases.json)) covering summarization, structured extraction, code explanation, ambiguous queries, and sentiment classification.

- **Evaluation Date**: `2026-08-12`
- **Prompt Version**: `v1` ([`prompts/task-execution-v1.md`](./prompts/task-execution-v1.md))
- **Total Cases Tested**: 8
- **Passed Cases**: 8 / 8
- **Match Score Percentage**: **100.00%**

To execute the evaluation runner:
```bash
python src/llm/eval.py
```

---

## 6. Token Cost Estimate per 10,000 Requests

- **Average Input Tokens per Request**: ~1,000 tokens
- **Average Output Tokens per Request**: ~250 tokens
- **Total Volume for 10,000 Requests**:
  - Input Tokens: 10,000 * 1,000 = 10,000,000 (10M tokens)
  - Output Tokens: 10,000 * 250 = 2,500,000 (2.5M tokens)
- **Cost Calculation** (Standard Tier Pricing: ~$0.15 / 1M input tokens, ~$0.60 / 1M output tokens):
  - Input Token Cost: 10M * $0.15 / 1M = **$1.50 USD**
  - Output Token Cost: 2.5M * $0.60 / 1M = **$1.50 USD**
  - **Total Estimated Cost per 10,000 Requests**: **~$3.00 USD** (or **$0.00** on OpenRouter free tier).

---

## 7. Endpoint Reference Table

| Path | Method | Auth Required | Expected Status Codes | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | No | `200 OK` | Root greeting endpoint |
| `/health` | `GET` | No | `200 OK` | Health check endpoint |
| `/public/info` | `GET` | No | `200 OK` | Unprotected public information route |
| `/auth/signup` | `POST` | No | `201 Created`, `400 Bad Request` | Register a new user in Supabase |
| `/auth/login` | `POST` | No | `200 OK`, `400 Bad Request`, `401 Unauthorized` | Log in and receive JWT access token |
| `/auth/logout` | `POST` | Yes (`Bearer`) | `204 No Content`, `401 Unauthorized` | Invalidate user session & log out |
| `/task/execute` | `POST` | No | `200 OK`, `422 Unprocessable`, `503 Unavailable`, `504 Timeout` | Execute LLM task execution pipeline |
| `/protected/profile` | `GET` | Yes (`Bearer`) | `200 OK`, `401 Unauthorized` | Retrieve authenticated user metadata |
| `/protected/dashboard` | `GET` | Yes (`Bearer`) | `200 OK`, `401 Unauthorized` | Retrieve authenticated user dashboard greeting |
