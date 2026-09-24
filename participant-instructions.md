# FrontDesk AI — Participant Deployment Guide

FrontDesk AI cannot answer anything without an LLM. It talks to one **LiteLLM gateway**, an
OpenAI-compatible endpoint set by `LITELLM_BASE_URL` and `LITELLM_API_KEY`. You do not need an Ollama,
Groq or other vendor key.

| Option | Where the app runs | LLM | Your URL |
|---|---|---|---|
| **A. Your Kubernetes namespace** (the workshop path) | Your own namespace on the workshop cluster | Already set in your sandbox | `https://$APP_HOST` |
| **B. GitHub Codespace** (not part of this workshop) | A kind cluster inside the Codespace | You supply a gateway URL and key | Forwarded port 8000 |
| **C. Your own machine** (not part of this workshop) | kind, or plain Python | You supply a gateway URL and key | http://localhost:8000 |

---

## Option A: Your Kubernetes namespace (workshop)

You deploy from the **JupyterLab terminal** in your sandbox. It already has `kubectl` pointed at your
namespace, and it exports everything the script needs:

| Variable | What it is |
|---|---|
| `APP_NAMESPACE` | Your namespace, e.g. `agenticaiu5` |
| `APP_HOST` | Your app URL, e.g. `agenticai<cohort>u5-app.brainupgrade.in` |
| `LITELLM_BASE_URL`, `LITELLM_API_KEY` | The workshop LLM gateway and **your own** key |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Langfuse tracing |

**1. Clone and deploy.** You need no `.env` file, and there is no image to build.

```bash
cd ~/work
git clone https://github.com/brainupgrade-in/aiagentic-comp-frontdeskai.git
cd aiagentic-comp-frontdeskai
bash scripts/deploy-spark.sh
```

The first run takes a minute or two while the image is pulled. It ends with:

```
==> FrontDesk AI deployed.
    URL:    https://agenticai<cohort>u<N>-app.brainupgrade.in
```

**2. Open your app URL.** Your namespace already has an Ingress for your `-app` hostname, so the app is
live there once the script finishes:

```bash
echo "https://$APP_HOST"
```

Log in as `rajesh.kumar@unigps.in` with password `brainupgrade`. Demo data is already loaded: 10 employees,
leave balances, tickets, expense claims, meeting rooms and payslips.

**3. Take the tour:** [use-case-scenarios.md](use-case-scenarios.md), starting at Part 1.

### What the script does

1. Creates `frontdeskai-secret` with `SECRET_KEY` and `AUTH_PASSWORD`. It keeps the existing `SECRET_KEY`
   on a redeploy, because that key decrypts the skill settings stored in the database.
2. Creates `frontdeskai-langfuse` from the `LANGFUSE_*` values in your terminal. A value in the repo's
   `.env` wins, if you have one.
3. Applies the ConfigMap, Service, Deployment, PVC and Ingress from `scripts/manifests/spark/`.
4. The Deployment reads your LLM key from the `<namespace>-llm` Secret the platform created. The key is
   never copied, and its daily cap is yours.
5. Restarts the pod and waits until it is ready.

It uses the published multi-arch image `brainupgrade/frontdeskai:latest`. Run it again at any time: your
data is on the PVC and survives.

### What is different from a Codespace or laptop

- **No MCP Leave Service (Part 9 of the tour).** It needs its own `postgres` namespace. Leave questions
  are answered from the app's own database, and the `get_leave_balance_from_hr_system` tool reports that
  it cannot reach the HR server.
- **No Grafana install.** Traces go to the shared Tempo as service `frontdeskai-<your namespace>`: in
  Grafana, open *Explore → Tempo → service.name*.
- **Only the workshop models.** To switch models from admin chat (Part 7), use a model your key can reach:
  `qwen36-35b-a3b-lab` (default), `qwen3-next-80b-lab`, `gemma4-31b-lab`, `gemma4-26b-a4b-lab`,
  `gemma4-31b-turbo-lab`, always with provider `litellm`.
- **One pod.** Your namespace quota fits one app pod, so a redeploy stops the old pod before it starts the
  new one. The app is down for about 30 seconds.

### Day-to-day

```bash
kubectl get pods -l app=frontdeskai          # is it running?
kubectl logs -f deployment/frontdeskai       # follow the logs
bash scripts/deploy-spark.sh                 # redeploy (same command)
```

**Start again with fresh demo data.** This deletes your chat history, passwords and installed skills:

```bash
kubectl delete deployment/frontdeskai pvc/frontdeskai-pvc
bash scripts/deploy-spark.sh
```

### Troubleshooting

**Your app URL shows `503 Service Temporarily Unavailable`** — nothing is running behind it yet. Your
namespace has the Ingress from the start, but the app only exists after `bash scripts/deploy-spark.sh`
finishes. Also expected for about 30 seconds during every redeploy. If it stays, run
`kubectl get pods -l app=frontdeskai`.

**`ERROR: APP_HOST is not set`** — you are not in the sandbox's JupyterLab terminal. Open a new terminal
there.

**Pod stuck in `Pending` or the rollout times out** — run `kubectl describe pod -l app=frontdeskai`. The
namespace fits one app pod, so delete anything else you started in it.

**The page shows `524` after about 100 seconds** — the site's proxy gave up waiting, but the app may still
be working. Reload the chat after a minute. If the answer is not there, ask again.

**Every answer fails, or says the model is unavailable** — check the gateway from your terminal:

```bash
curl -s -H "Authorization: Bearer $LITELLM_API_KEY" "$LITELLM_BASE_URL/models"
kubectl logs deployment/frontdeskai | grep -i "llm call failed"
```

If you switched to another model in admin chat, switch back: `switch to qwen36-35b-a3b-lab on litellm`.

---

## Option B: GitHub Codespace (not part of this workshop)

> **Out of scope for this workshop.** Use Option A. This section is kept for use after the course.

The app runs in a kind cluster inside the Codespace. **You need a LiteLLM gateway that can be reached from
the internet.** The workshop gateway is internal to the workshop cluster, so a Codespace cannot reach it.

**1. Save the gateway as Codespaces secrets.** On GitHub, go to **Settings → Codespaces → Secrets → New
secret** and scope each secret to this repo:

- `LITELLM_BASE_URL`, ending in `/v1`
- `LITELLM_API_KEY`
- `LLM_MODEL` (optional; the default is `qwen36-35b-a3b-lab`)

**2. Launch.** On the repo page, choose **Code → Codespaces → Create codespace on main**. The devcontainer
installs kubectl, helm, kind and Docker-in-Docker, then creates the kind cluster `frontdeskai`. It copies
your secrets into `.env` and runs `scripts/quickstart.sh`, which builds the image, deploys the app and the
MCP Leave Service, and checks the demo data. Wait for the `FrontDesk AI is ready` banner.

**3. If you skipped the secrets,** put the two `LITELLM_` values in `.env` and run:

```bash
bash scripts/quickstart.sh
```

**4. Open port 8000** from the Ports tab, and log in as `rajesh.kumar@unigps.in` / `brainupgrade`.

The app's Python packages are not installed in the Codespace itself. They are built into the image, and
the app runs only in kind, so deploy it with the scripts rather than `python app/app.py`.

---

## Option C: Your own machine (not part of this workshop)

> **Out of scope for this workshop.** Use Option A.

The gateway must be reachable from your machine.

```bash
git clone https://github.com/brainupgrade-in/aiagentic-comp-frontdeskai.git
cd aiagentic-comp-frontdeskai
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64 \
  && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind
cp .env.example .env          # set LITELLM_BASE_URL and LITELLM_API_KEY
bash scripts/quickstart.sh    # creates the cluster if needed, then deploys everything
```

`quickstart.sh` calls `scripts/create-kind-cluster.sh`, which needs passwordless sudo to create and chown
`/shared`:

```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER
```

If you plan to install observability, raise the inotify limits first. Otherwise Promtail goes into
`CrashLoopBackOff` with `too many open files`. Add these to `/etc/sysctl.conf` to keep them:

```bash
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288
```

### Without Kubernetes

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
cp .env.example .env          # set LITELLM_BASE_URL and LITELLM_API_KEY
python app/app.py             # http://localhost:8000
```

---

## What quickstart.sh does (Options B and C)

Re-running it is safe: every step is idempotent.

1. Creates `.env` from `.env.example` if it is missing
2. Stops early with instructions if `LITELLM_BASE_URL` or `LITELLM_API_KEY` is missing from both `.env`
   and the environment
3. Creates the kind cluster `frontdeskai` if it does not exist
4. `scripts/deploy.sh` builds the image, loads it into kind, and applies the secret and manifests
5. `scripts/deploy-mcp.sh` deploys PostgreSQL and the MCP Leave Server and runs a smoke test (if this step
   fails, the rest still continues)
6. Waits for `/health`, checks the demo data row counts and prints the demo logins

Skip the MCP stack with `SKIP_MCP=true bash scripts/quickstart.sh`.

**Optional add-ons (kind only):** `bash scripts/install-observability.sh` installs Prometheus, Grafana,
Loki, Promtail and Tempo. Grafana is at **http://localhost:3000** (agenticai / agentgrow.io). For Langfuse,
put all three `LANGFUSE_*` values in `.env` and run `bash scripts/update-secret.sh`. Editing `.env` alone
changes nothing in the cluster.

### Troubleshooting (kind)

**`ImagePullBackOff` / `ErrImageNeverPull`** — rerun `bash scripts/deploy.sh` to rebuild the image and
load it into kind again.

**Not responding, or `401 Unauthorized` from the LLM** — check the gateway settings that reached the pod:

```bash
kubectl logs deployment/frontdeskai | grep -i "error\|unauthorized"
kubectl get secret frontdeskai-secret -o jsonpath='{.data.LITELLM_BASE_URL}' | base64 -d; echo
bash scripts/update-secret.sh    # after fixing .env
```

**kind cluster not found** — run `kind get clusters`. If it is missing, rerun `bash scripts/quickstart.sh`.
It recreates the cluster with the port mappings that `localhost` access depends on.

**Codespace enters recovery mode (Docker-in-Docker fails)** — the devcontainer base image must be
`mcr.microsoft.com/devcontainers/python:3.13-bookworm`, not `bullseye`. Delete the Codespace and create a
new one to pick up the fix.
