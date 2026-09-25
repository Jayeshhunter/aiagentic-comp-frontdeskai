"""Leave-source eval: does a balance question read the system that holds that person's leave?

An app employee (rajesh.kumar) keeps leave in this app; the HR system would provision
a default record and report a second, wrong balance. An HR-system employee (alice)
is not in the app, so the answer has to come from MCP. Needs the MCP Leave Service
running, as deploy-spark.sh sets up. See README.md for how to run it.
"""
import os, sys
sys.path.insert(0, os.environ.get("APP_DIR", "/app"))
import agents
from auth import current_user_email

# (email, name, the tool whose answer must be used)
CASES = [
    ("rajesh.kumar@unigps.in", "Rajesh Kumar", "get_leave_balance("),
    ("alice@unigps.in", "Alice Johnson", "get_leave_balance_from_hr_system("),
]
REQUESTS = ["What's my leave balance?", "How much casual leave do I have left?"]
RUNS = int(os.environ.get("RUNS", "2"))

def once(email, name, request):
    current_user_email.set(email)
    state = {"request": request, "employee_name": name,
             "employee_id": email.split("@")[0], "category": "hr", "confidence": 9,
             "conversation_history": [], "fewshot_context": "", "rag_context": "", "audit": []}
    # No policy retrieval: a balance comes from a tool, and skipping it keeps this
    # light enough to run next to the app inside its 1Gi pod.
    return agents.hr_worker(state).get("tool_calls_made") or []

total = passed = 0
for email, name, want in CASES:
    for request in REQUESTS:
        hits = 0
        for _ in range(RUNS):
            try:
                tools = once(email, name, request)
            except Exception as e:
                print("   ERR", type(e).__name__, str(e)[:100]); total += 1; continue
            # rajesh must not end on the HR system; alice must reach it
            last = tools[-1] if tools else ""
            ok = want in last
            hits += ok; passed += ok; total += 1
            if not ok:
                print("   miss:", tools)
        print("  [%s] %-14s %-40s %d/%d (want %s)" %
              ("PASS" if hits == RUNS else "FAIL", email.split("@")[0], request[:40], hits, RUNS, want.rstrip("(")))
print("\nSCORE: %d/%d" % (passed, total))
