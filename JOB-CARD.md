# Job Card: LLM Task Execution & Response Pipeline (Assignment A17)

## 1. Job Purpose
The purpose of this job is to process structured input tasks, perform LLM inference via an OpenAI-compatible API provider (e.g., OpenRouter, OpenAI, or Ollama), and return validated, structured JSON outputs adhering strictly to the required schema while implementing fallback behaviors for uncertainties or failure states.

## 2. Input JSON Format
The system accepts structured JSON inputs containing task prompt details, optional parameters, and context:

```json
{
  "task_id": "string (unique identifier for the task)",
  "prompt": "string (the primary instruction or user query)",
  "context": "optional string or object (additional context or source data)",
  "temperature": "optional float (sampling temperature, default 0.0)"
}
```

## 3. Output JSON Schema
All outputs produced by the system must strictly conform to the following JSON structure:

```json
{
  "task_id": "string (matches input task_id)",
  "status": "string ('success' | 'fallback' | 'error')",
  "result": "string or object (the generated output response)",
  "confidence": "float (confidence score between 0.0 and 1.0)",
  "error_message": "nullable string (present only if status is 'error' or 'fallback')"
}
```

## 4. Strict Rules ("Must Never")
To maintain safety, reliability, and architectural integrity, the system **MUST NEVER**:
- **MUST NEVER** return unparsed raw text when structured JSON output is requested.
- **MUST NEVER** expose sensitive credentials, API keys, or internal system paths in logs, outputs, or error responses.
- **MUST NEVER** execute arbitrary unvalidated shell commands or code returned by the LLM.
- **MUST NEVER** retry indefinitely on client authentication errors (HTTP 401/403).
- **MUST NEVER** mutate global environment variables dynamically at runtime.

## 5. Fallback Behavior
When encountering uncertainties, model timeouts, missing fields, or API failures:
- If the model returns ambiguous or invalid JSON, the system attempts 1 automatic retry with a strict formatting constraint.
- If the retry fails or if the API returns a terminal error (e.g., rate limit, network timeout, or invalid API key), the system immediately triggers the **fallback state**.
- The fallback response sets `"status": "fallback"`, assigns a safe default result or message, records the error detail in `"error_message"`, and sets `"confidence": 0.0` without crashing the application.
