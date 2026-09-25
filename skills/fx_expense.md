# Skill: fx_expense

Convert an expense paid in a foreign currency to INR, so the Finance worker can file it as a claim.

## Metadata

| Field | Value |
|-------|-------|
| Name | `fx_expense` |
| Categories | `finance` |
| Source | `skills/fx_expense.py` |

## Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `convert_expense_currency` | Convert an amount to INR at the ECB reference rate for the expense date | `amount`; `currency`: ISO code, e.g. `EUR`; `expense_date`: `YYYY-MM-DD`, empty for the latest rate |

Rates come from the [Frankfurter API](https://frankfurter.dev) (European Central Bank reference rates, about
30 currencies). It needs no API key, so the skill has no config keys. On a weekend or holiday the API returns the
previous business day's rate, and the tool says so.

## Configuration

None. The pod needs outbound HTTPS to `api.frankfurter.dev`.

## Try it

Log in as an employee and ask:

```
I paid EUR 84 for a taxi in Frankfurt on 2026-09-12. Please file it as a travel expense.
```

The Finance worker calls `convert_expense_currency`, then `submit_expense_claim` with the INR amount, and puts
the original amount and rate in the claim description.

## Installation

The skill file is deployed to the pod PVC at `/shared/.frontdeskai/skills/fx_expense.py`.
It auto-loads on pod startup. After updating the file, restart the pod:

```bash
kubectl cp skills/fx_expense.py \
  $(kubectl get pod -l app=frontdeskai -o jsonpath='{.items[0].metadata.name}'):/shared/.frontdeskai/skills/fx_expense.py
kubectl rollout restart deployment/frontdeskai
```
