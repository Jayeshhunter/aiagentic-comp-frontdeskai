"""Finance worker eval: does it look up the caller's claims instead of promising to?

Runs the REAL finance_worker against the REAL model. Point APP_DIR at a patched copy
of /app to compare prompt variants. See README.md for how to run it in the pod.
"""
import os, sys
sys.path.insert(0, os.environ.get("APP_DIR", "/app"))
import agents
from auth import current_user_email
current_user_email.set("rajesh.kumar@unigps.in")

# The Part 1 tour sends the finance question straight after a tech ticket.
AFTER_TICKET = [{"role": "user", "content": "My laptop screen is flickering when it runs on battery"},
                {"role": "assistant", "content": "[TECH] A P2 hardware ticket (TECH-1006) has been created "
                                                 "for your flickering screen issue."}]

# (request, the tool that must be called)
CASES = [
    ("When will my travel expense be reimbursed?", "list_my_expense_claims"),
    ("What's the status of my expense claims?", "list_my_expense_claims"),
    ("Has my cab claim been paid?", "list_my_expense_claims"),
    ("What is the status of EXP-2026-0001?", "get_expense_status"),
]
RUNS = int(os.environ.get("RUNS", "2"))

def once(request, history):
    state = {"request": request, "employee_name": "Rajesh Kumar",
             "employee_id": "rajesh.kumar", "category": "finance", "confidence": 9,
             "conversation_history": history, "fewshot_context": "",
             "rag_context": "", "audit": []}
    state.update(agents.rag_retrieval(state))
    out = agents.finance_worker(state)
    return out.get("tool_calls_made") or [], (out.get("response") or "")

total = passed = 0
for hlabel, hist in (("clean history", []), ("after a tech ticket", AFTER_TICKET)):
    print("\n--- %s ---" % hlabel)
    for request, want in CASES:
        hits = 0
        for _ in range(RUNS):
            try:
                tools, resp = once(request, hist)
            except Exception as e:
                print("   ERR", type(e).__name__, str(e)[:100]); total += 1; continue
            ok = any(want in str(t) for t in tools)
            hits += ok; passed += ok; total += 1
            if not ok:
                print("   miss:", tools, "|", resp[:120].replace("\n", " "))
        print("  [%s] %-48s %d/%d (want %s)" %
              ("PASS" if hits == RUNS else "FAIL", request[:48], hits, RUNS, want))
print("\nSCORE: %d/%d" % (passed, total))
