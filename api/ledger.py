"""GA1 Q15: The Ledger Agent.

Plain-English question  ->  structured query (LLM via AI Pipe, with a keyword fallback)
                        ->  exact computation over the ledger snapshot in ledger_data.py
"""
import calendar
import collections
import datetime as dt
import json
import os
import re

from ledger_data import RATES, RAW_ROWS  # snapshot of the API: /rates and /export

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
REGIONS = ["Central", "East", "North", "South", "West"]
PRODUCTS = ["Air Fryer", "Blender", "Grinder", "Juicer", "Kettle", "Mixer", "Rice Cooker", "Toaster"]
STATUSES = ["paid", "refunded", "void"]


def _ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _build_current():
    latest = {}
    for r in RAW_ROWS:  # an id can appear more than once: the latest updated_at wins
        cur = latest.get(r["id"])
        if cur is None or _ts(r["updated_at"]) > _ts(cur["updated_at"]):
            latest[r["id"]] = r
    out = []
    for r in latest.values():
        d = dict(r)
        d["usd"] = r["amount"] * RATES[r["currency"]]
        d["date"] = _ts(r["created_at"]).astimezone(IST).date()  # business date in Asia/Kolkata
        out.append(d)
    return out


ORDERS = _build_current()
CUSTOMERS = sorted({r["customer"] for r in ORDERS})
MIN_DATE = min(r["date"] for r in ORDERS)
MAX_DATE = max(r["date"] for r in ORDERS)

# --------------------------------------------------------------------------- query engine
METRICS = {
    "revenue_usd": "sum of USD amount of PAID orders (revenue / sales / income / gross sales)",
    "refunded_usd": "sum of USD amount of REFUNDED orders (refund value / money refunded)",
    "net_usd": "paid USD minus refunded USD",
    "order_count": "number of orders (use the status filter to say which: paid, refunded, void)",
    "units": "sum of qty (units / items / quantity sold); paid orders unless statuses given",
    "distinct_customers": "number of different customers",
    "avg_order_value_usd": "average USD amount per order (paid orders unless statuses given)",
    "avg_units_per_order": "average qty per order",
    "refund_rate_pct": "refunded orders as a percentage of (paid + refunded) orders",
}
DEFAULT_STATUS = {
    "revenue_usd": ["paid"], "refunded_usd": ["refunded"], "net_usd": None,
    "order_count": None, "units": ["paid"], "distinct_customers": ["paid"],
    "avg_order_value_usd": ["paid"], "avg_units_per_order": ["paid"], "refund_rate_pct": None,
}
MONEY = {"revenue_usd", "refunded_usd", "net_usd", "avg_order_value_usd"}


def _metric(rows, metric):
    if metric == "revenue_usd":
        return sum(r["usd"] for r in rows if r["status"] == "paid")
    if metric == "refunded_usd":
        return sum(r["usd"] for r in rows if r["status"] == "refunded")
    if metric == "net_usd":
        return sum(r["usd"] for r in rows if r["status"] == "paid") - \
            sum(r["usd"] for r in rows if r["status"] == "refunded")
    if metric == "order_count":
        return len(rows)
    if metric == "units":
        return sum(r["qty"] for r in rows)
    if metric == "distinct_customers":
        return len({r["customer"] for r in rows})
    if metric == "avg_order_value_usd":
        return sum(r["usd"] for r in rows) / len(rows) if rows else 0
    if metric == "avg_units_per_order":
        return sum(r["qty"] for r in rows) / len(rows) if rows else 0
    if metric == "refund_rate_pct":
        p = sum(1 for r in rows if r["status"] == "paid")
        f = sum(1 for r in rows if r["status"] == "refunded")
        return 100.0 * f / (p + f) if (p + f) else 0
    raise ValueError("unknown metric " + str(metric))


def _as_list(v):
    if v is None or v == "" or v == []:
        return None
    return v if isinstance(v, list) else [v]


def _norm(values, allowed):
    if not values:
        return None
    out = []
    for v in values:
        for a in allowed:
            if str(v).strip().lower() == a.lower():
                out.append(a)
    return out or None


def _date(s):
    return dt.date.fromisoformat(str(s)[:10]) if s else None


def run_query(q):
    metric = q.get("metric", "revenue_usd")
    statuses = _norm(_as_list(q.get("statuses")), STATUSES)
    if statuses is None:
        statuses = DEFAULT_STATUS.get(metric)
    if metric in ("revenue_usd", "refunded_usd", "net_usd", "refund_rate_pct"):
        statuses = None  # these metrics pick their own statuses
    regions = _norm(_as_list(q.get("regions")), REGIONS)
    products = _norm(_as_list(q.get("products")), PRODUCTS)
    customers = _as_list(q.get("customers"))
    currencies = _as_list(q.get("currencies"))
    d0, d1 = _date(q.get("date_from")), _date(q.get("date_to"))

    rows = [r for r in ORDERS
            if (statuses is None or r["status"] in statuses)
            and (regions is None or r["region"] in regions)
            and (products is None or r["product"] in products)
            and (customers is None or r["customer"] in customers)
            and (currencies is None or r["currency"] in currencies)
            and (d0 is None or r["date"] >= d0)
            and (d1 is None or r["date"] <= d1)]

    group_by = q.get("group_by")
    if not group_by:
        return _fmt(metric, _metric(rows, metric))

    keyf = {"region": lambda r: r["region"], "product": lambda r: r["product"],
            "customer": lambda r: r["customer"], "currency": lambda r: r["currency"],
            "month": lambda r: r["date"].strftime("%Y-%m"),
            "date": lambda r: r["date"].isoformat()}[group_by]
    groups = collections.defaultdict(list)
    for r in rows:
        groups[keyf(r)].append(r)
    scored = sorted(((_metric(g, metric), k) for k, g in groups.items()),
                    key=lambda t: (-t[0], t[1]) if q.get("order", "desc") == "desc" else (t[0], t[1]))
    if not scored:
        return None
    n = int(q.get("top_n") or 1)
    want = q.get("return", "key")
    picked = scored[:n]
    if want == "value":
        vals = [_fmt(metric, v) for v, _ in picked]
        return vals[0] if n == 1 else vals
    if want == "both":
        return [{"name": k, "value": _fmt(metric, v)} for v, k in picked] if n > 1 else \
            {"name": picked[0][1], "value": _fmt(metric, picked[0][0])}
    keys = [_fmt_key(group_by, k) for _, k in picked]
    return keys[0] if n == 1 else keys


def _fmt(metric, v):
    if metric in MONEY:
        return round(v + 1e-9, 2)
    if metric in ("order_count", "units", "distinct_customers"):
        return int(v)
    return round(v, 2)


def _fmt_key(group_by, k):
    if group_by == "month":
        y, m = k.split("-")
        return calendar.month_name[int(m)] + " " + y
    return k


# --------------------------------------------------------------------------- question -> query
SYSTEM_PROMPT = """You translate a business question about an order ledger into a JSON query. Do NOT compute the answer.
Data: orders of Acme Appliances with fields customer (ids like C1036), region, product, qty, amount, currency, status, business date.
Regions: %s. Products (exact spelling): %s. Statuses: paid, refunded, void.
Data covers %s to %s (business dates, Asia/Kolkata). If a year is not given, assume 2026.

Return ONLY a JSON object with these keys:
- "metric": one of %s
- "statuses": list of statuses to filter on, or null for the metric's default
- "regions", "products", "customers", "currencies": list or null
- "date_from", "date_to": inclusive dates "YYYY-MM-DD", or null. A month means its first to last day. Q1 = Jan 1 to Mar 31, Q2 = Apr 1 to Jun 30, H1 = Jan 1 to Jun 30.
- "group_by": null, or one of "region","product","customer","month","currency" when the question asks WHICH region/product/customer/month (e.g. "best-selling product", "top customer").
- "order": "desc" for highest/most/top/best, "asc" for lowest/least/worst.
- "top_n": how many to return (default 1)
- "return": "key" to return the name(s) (e.g. which product), "value" to return the metric of the top group (e.g. "how much did the top customer spend").

Metric meanings: %s
Revenue always means paid orders only. "How many orders" without a status means orders of any status unless the question says paid/completed/refunded/cancelled(void).
Units sold / quantity sold means units of paid orders.
"How many different/unique/distinct customers ..." -> metric distinct_customers with group_by null (it asks for a count, not a name).
"at least one" is NOT a ranking word. Only use group_by when the question asks WHICH/WHO/top/best/highest/lowest among regions/products/customers/months."""


def _llm_query(question):
    token = os.environ.get("AIPIPE_TOKEN")
    if not token:
        return None
    import httpx
    metric_doc = "; ".join(f"{k} = {v}" for k, v in METRICS.items())
    sys_prompt = SYSTEM_PROMPT % (", ".join(REGIONS), ", ".join(PRODUCTS), MIN_DATE, MAX_DATE,
                                  ", ".join(METRICS), metric_doc)
    r = httpx.post(
        "https://aipipe.org/openrouter/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": os.environ.get("LEDGER_MODEL", "openai/gpt-4.1-mini"), "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": sys_prompt},
                           {"role": "user", "content": question}]},
        timeout=11,
    )
    r.raise_for_status()
    q = json.loads(r.json()["choices"][0]["message"]["content"])
    if q.get("metric") not in METRICS:
        return None
    return q


MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def _explicit_days(t, year):
    """Dates like 2026-03-15, 15 March 2026, March 15, 2026, 15/03/2026."""
    out = []
    for y, m, d in re.findall(r"\b(20\d\d)-(\d\d)-(\d\d)\b", t):
        out.append(dt.date(int(y), int(m), int(d)))
    names = "|".join(sorted(MONTHS, key=len, reverse=True))
    for d, mon, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + names + r")\.?,?\s*(20\d\d)?\b", t):
        out.append(dt.date(int(y or year), MONTHS[mon], int(d)))
    for mon, d, y in re.findall(r"\b(" + names + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b,?\s*(20\d\d)?", t):
        if int(d) <= 31:
            out.append(dt.date(int(y or year), MONTHS[mon], int(d)))
    for d, m, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b", t):
        out.append(dt.date(int(y), int(m), int(d)))
    return out


def _rule_query(question):
    t = question.lower()
    q = {"metric": "revenue_usd"}
    if re.search(r"\bnet\b", t) and re.search(r"revenue|sales|income", t):
        q["metric"] = "net_usd"
    elif "refund" in t:
        q["metric"] = "refunded_usd" if re.search(r"amount|value|usd|\$|total|how much|sum", t) else "order_count"
        if q["metric"] == "order_count":
            q["statuses"] = ["refunded"]
        if "rate" in t or "percent" in t or "%" in t:
            q["metric"] = "refund_rate_pct"
    elif re.search(r"\bunits?\b|quantity|items sold|how many .* sold", t) and not re.search(r"\b(average|mean|avg)\b", t):
        q["metric"] = "units"
    elif re.search(r"(how many|count|number of|count of)( the)? (distinct |unique |different )?customers", t):
        q["metric"] = "distinct_customers"
    elif re.search(r"\b(average|mean|avg)\b.*\b(units?|qty|quantity|items)\b.*\b(per|in an?|each) (\w+ )?order\b", t):
        q["metric"] = "avg_units_per_order"
    elif re.search(r"\b(average|mean|avg)\b(\s+\w+)?\s+(order|ticket|basket|transaction|sale)\b|\baov\b|\b(average|mean|avg)\b.*\bper order\b|\b(average|mean|avg)\b.*\b(order|transaction) (value|size|amount)\b", t):
        q["metric"] = "avg_order_value_usd"
    elif re.search(r"how many (\w+ )?orders|number of (\w+ )?orders|order count|count of (\w+ )?orders", t):
        q["metric"] = "order_count"
        for s in STATUSES:
            if s in t:
                q["statuses"] = [s]
        if "cancel" in t:
            q["statuses"] = ["void"]
    q["regions"] = [r for r in REGIONS if re.search(r"\b" + r.lower() + r"\b", t)] or None
    q["products"] = [p for p in PRODUCTS if p.lower() in t or p.lower().replace(" ", "") in t] or None
    q["customers"] = [c for c in CUSTOMERS if c.lower() in t] or None
    year = int(m.group(1)) if (m := re.search(r"\b(20\d\d)\b", t)) else 2026
    mm = []
    for w in re.findall(r"[a-z]+", t):
        if w not in MONTHS:
            continue
        if w == "may" and not re.search(r"\bmay\s+20\d\d|\b(in|of|during|for) may\b", t):
            continue  # "may" is usually the verb
        mm.append(MONTHS[w])
    days = _explicit_days(t, year)
    if days:
        q["date_from"], q["date_to"] = min(days).isoformat(), max(days).isoformat()
        mm = []
    t = re.sub(r"\bfirst quarter\b", "q1", t)
    t = re.sub(r"\bsecond quarter\b", "q2", t)
    t = re.sub(r"\bthird quarter\b", "q3", t)
    t = re.sub(r"\bfourth quarter\b", "q4", t)
    if re.search(r"\b(first half|h1)\b", t):
        mm = [1, 6]
    if days:
        pass
    elif (m := re.search(r"\bq([1-4])\b", t)):
        a = (int(m.group(1)) - 1) * 3 + 1
        q["date_from"], q["date_to"] = f"{year}-{a:02d}-01", f"{year}-{a+2:02d}-{calendar.monthrange(year, a+2)[1]}"
    elif mm:
        a, b = min(mm), max(mm)
        q["date_from"], q["date_to"] = f"{year}-{a:02d}-01", f"{year}-{b:02d}-{calendar.monthrange(year, b)[1]}"
    tg = re.sub(r"\bat (least|most)\b", " ", t)  # "at least one order" is not a ranking
    asks_count = re.match(r"\s*(how many|how much|what (is|was) the (total|number|sum|average|count))", tg)
    m = re.search(r"\b(which|what|name the|identify the)\s+(\w+\s+)?(region|product|customer|month)", tg)
    rank = re.search(r"\b(top|best|biggest|largest|highest|most|lowest|least|worst|smallest|fewest)\b", tg)
    group = None
    if m:
        group = m.group(3)
    elif rank and not asks_count:
        for g in ("product", "region", "customer", "month"):
            if re.search(r"\b" + g, tg):
                group = g
                break
    elif rank and asks_count:
        # e.g. "How much did the top customer spend?" -> value of the top group
        for g in ("product", "region", "customer", "month"):
            if re.search(r"\b(top|best|biggest|largest|highest|lowest|worst|smallest)\s+(\w+\s+)?" + g, tg):
                group = g
                q["return"] = "value"
                break
    if group:
        q["group_by"] = group
        q["order"] = "asc" if re.search(r"\b(lowest|least|worst|fewest|smallest)\b", tg) else "desc"
        q.setdefault("return", "key")
        if (mt := re.search(r"\b(top|bottom|best|worst)\s+(\d+|two|three|four|five)\b", tg)):
            words = {"two": 2, "three": 3, "four": 4, "five": 5}
            q["top_n"] = int(words.get(mt.group(2), mt.group(2)))
        # what are we ranking by?
        if re.search(r"\bunits?\b|quantity|most sold|best[- ]selling|sold the most", tg) and q["metric"] == "revenue_usd":
            q["metric"] = "units"
        if re.search(r"\b(most|fewest|number of|count of) (\w+ )?orders\b", tg) and q["metric"] == "revenue_usd":
            q["metric"] = "order_count"
            q["statuses"] = ["paid"] if "paid" in tg else None
    if group == "customer" and q["metric"] == "distinct_customers":
        q["metric"] = "revenue_usd"
    if q["metric"] in ("order_count", "units", "distinct_customers", "avg_order_value_usd") and "paid" in tg:
        q["statuses"] = ["paid"]
    return q


def answer(question):
    q = None
    try:
        q = _llm_query(question)
    except Exception as e:  # LLM unavailable: fall back to keyword rules
        print("LLM error:", e)
    source = "llm" if q else "rules"
    if not q:
        q = _rule_query(question)
    # A "how many / how much" question wants a number, never a name
    if q.get("group_by") and q.get("return", "key") == "key" and \
            re.match(r"\s*(how many|how much)", question.lower()):
        q["group_by"] = None
    result = run_query(q)
    print(json.dumps({"question": question, "source": source, "query": q, "answer": result}, default=str))
    return result, q, source
