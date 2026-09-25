"""Policy-over-history eval: when an earlier reply and the retrieved policy disagree, which wins?

Part 2 of the tour edits a policy in the Knowledge Base and asks again. The earlier
answer is still in the conversation, and the worker must answer from the policy it
just retrieved, not repeat itself. Here the history carries a stale answer that
contradicts the bundled hr-handbook.md, which is the same situation.

Runs the REAL hr_worker against the REAL model and the pod's own index, so the
Knowledge Base must hold the bundled handbook. See README.md for how to run it.
"""
import os, re, sys
sys.path.insert(0, os.environ.get("APP_DIR", "/app"))
import agents
from auth import current_user_email
current_user_email.set("rajesh.kumar@unigps.in")

# (request, stale earlier reply, figure the policy says, figure only the stale reply says)
CASES = [
    ("How many consecutive casual leave days can I take without manager approval?",
     "[HR] You can take up to 7 consecutive casual leave days without manager approval; "
     "8–10 days require manager approval.", "5", "7"),
    ("How much notice do I need to give for earned leave?",
     "[HR] For earned leave you must apply at least 3 days in advance.", "7", "3"),
]
RUNS = int(os.environ.get("RUNS", "3"))

def once(request, history):
    state = {"request": request, "employee_name": "Rajesh Kumar",
             "employee_id": "rajesh.kumar", "category": "hr", "confidence": 9,
             "conversation_history": history, "fewshot_context": "",
             "rag_context": "", "audit": []}
    state.update(agents.rag_retrieval(state))
    return agents.hr_worker(state).get("worker_output") or ""

total = passed = 0
for request, stale, want, stale_fig in CASES:
    # The stale answer twice, as in the tour: once in Part 1 or 2, once just before the edit.
    history = [{"role": "user", "content": request}, {"role": "assistant", "content": stale},
               {"role": "user", "content": "and sick?"},
               {"role": "assistant", "content": "[HR] You have 8 sick leave days remaining this year."},
               {"role": "user", "content": request}, {"role": "assistant", "content": stale}]
    hits = 0
    for _ in range(RUNS):
        try:
            resp = once(request, history)
        except Exception as e:
            print("   ERR", type(e).__name__, str(e)[:100]); total += 1; continue
        ok = bool(re.search(rf"\b{want}\b", resp)) and not re.search(rf"\b{stale_fig}\b", resp)
        hits += ok; passed += ok; total += 1
        if not ok:
            print("   miss:", resp[:160].replace("\n", " "))
    print("  [%s] %-48s %d/%d (want %s, not %s)" %
          ("PASS" if hits == RUNS else "FAIL", request[:48], hits, RUNS, want, stale_fig))
print("\nSCORE: %d/%d" % (passed, total))
