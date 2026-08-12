import os
import json
import sys
from datetime import datetime

# Ensure project root is in sys.path when running from src/llm
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from main import app

def run_evaluation(cases_path: str = "evals/cases.json"):
    if not os.path.exists(cases_path):
        print(f"Error: Evaluation file '{cases_path}' not found.")
        sys.exit(1)

    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    client = TestClient(app)

    print("==================================================")
    print("      LLM TASK EXECUTION EVALUATION RUNNER       ")
    print(f" Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f" Total Evaluation Cases: {len(cases)}")
    print("==================================================\n")

    passed_count = 0
    total_count = len(cases)

    for idx, case in enumerate(cases, 1):
        task_id = case.get("task_id", f"eval-{idx}")
        prompt = case.get("prompt")
        context = case.get("context")
        expected_status = case.get("expected_status")
        expected_keywords = case.get("expected_keywords", [])

        payload = {
            "task_id": task_id,
            "prompt": prompt,
            "context": context,
            "temperature": case.get("temperature", 0.0)
        }

        try:
            response = client.post("/task/execute", json=payload)
            if response.status_code != 200:
                print(f"[{idx}/{total_count}] ❌ FAIL - Task ID: {task_id} (HTTP Status {response.status_code})")
                continue

            data = response.json()
            actual_status = data.get("status")
            result_str = str(data.get("result", "")).lower()

            status_match = (actual_status == expected_status)

            keywords_match = True
            for kw in expected_keywords:
                if kw.lower() not in result_str:
                    keywords_match = False
                    break

            if status_match and keywords_match:
                passed_count += 1
                print(f"[{idx}/{total_count}] [PASS] - Task ID: {task_id} (Status: {actual_status})")
            else:
                reasons = []
                if not status_match:
                    reasons.append(f"Status mismatch (Expected '{expected_status}', got '{actual_status}')")
                if not keywords_match:
                    reasons.append(f"Missing expected keywords: {expected_keywords}")
                print(f"[{idx}/{total_count}] [FAIL] - Task ID: {task_id} | Reason: {', '.join(reasons)}")

        except Exception as e:
            print(f"[{idx}/{total_count}] [ERROR] - Task ID: {task_id} | Exception: {e}")

    match_score = (passed_count / total_count) * 100.0 if total_count > 0 else 0.0

    print("\n==================================================")
    print("              EVALUATION SUMMARY                  ")
    print(f" Passed Cases : {passed_count} / {total_count}")
    print(f" Match Score  : {match_score:.2f}%")
    print("==================================================")

    return match_score

if __name__ == "__main__":
    run_evaluation()
