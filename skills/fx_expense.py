import json
import urllib.error
import urllib.parse
import urllib.request

from langchain_core.tools import tool

SKILL_META = {
    "name": "fx_expense",
    "description": "Convert a foreign-currency expense to INR at the ECB rate for the expense date (Frankfurter API, no key)",
    "categories": ["finance"],
    "config_keys": [],
}

_API = "https://api.frankfurter.dev/v1"


@tool
def convert_expense_currency(amount: float, currency: str, expense_date: str = "") -> str:
    """Convert an expense paid in a foreign currency to INR, at the rate for the day it was paid.
    Expense claims are recorded in INR, so call this BEFORE submit_expense_claim whenever the
    employee paid in another currency (EUR, USD, GBP, SGD, JPY, ...), then submit the INR amount
    and put the original amount and rate in the claim description.
    amount: the amount in the foreign currency. currency: 3-letter ISO code, e.g. 'EUR'.
    expense_date: YYYY-MM-DD; leave empty for today's rate."""
    currency = currency.strip().upper()
    if amount <= 0:
        return "Amount must be positive."
    if currency == "INR":
        return f"The amount is already in INR: INR {amount:,.2f}. No conversion needed."

    day = expense_date.strip() or "latest"
    query = urllib.parse.urlencode({"base": currency, "symbols": "INR"})
    # Cloudflare in front of the API returns 403 to Python's default User-Agent.
    req = urllib.request.Request(f"{_API}/{day}?{query}",
                                 headers={"User-Agent": "FrontDeskAI/1.0 (fx_expense skill)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404, 422):
            return (f"No ECB rate for {currency} on {day}. Check the currency code and the date "
                    "(YYYY-MM-DD, not in the future). ECB publishes about 30 major currencies.")
        return f"Exchange-rate service error: HTTP {e.code}"
    except Exception as e:
        return f"Exchange-rate service unreachable: {e}"

    rate = data.get("rates", {}).get("INR")
    if rate is None:
        return f"No INR rate returned for {currency}."
    inr = round(amount * rate, 2)
    note = ""
    if expense_date and data.get("date") != expense_date:
        note = f"\n  Note:       no rate is published on {expense_date} (weekend or holiday); used {data['date']}"
    return (
        f"{currency} {amount:,.2f} = INR {inr:,.2f}\n"
        f"  Rate:       1 {currency} = {rate} INR (ECB reference rate, {data.get('date')})"
        f"{note}\n"
        f"  Claim text: {currency} {amount:,.2f} @ {rate} ({data.get('date')})"
    )
