from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def force_cors(request: Request, call_next):
    # Always send CORS headers (even with no Origin header or on errors),
    # and expose them so browser-side graders can read them.
    try:
        response = await call_next(request)
    except Exception as e:
        from fastapi.responses import JSONResponse
        response = JSONResponse({"error": str(e)}, status_code=500)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


@app.middleware("http")
async def restore_original_path(request: Request, call_next):
    # vercel.json rewrites every URL to /api/index?__path=/<original path>.
    # Put the original path back so routes like /effective-config and /mcp match.
    from urllib.parse import parse_qsl, urlencode
    qs = parse_qsl(request.scope.get("query_string", b"").decode(), keep_blank_values=True)
    orig = None
    rest = []
    for k, v in qs:
        if k == "__path" and orig is None:
            orig = v
        else:
            rest.append((k, v))
    if orig is not None:
        if not orig.startswith("/"):
            orig = "/" + orig
        request.scope["path"] = orig
        request.scope["raw_path"] = orig.encode()
        request.scope["query_string"] = urlencode(rest, doseq=True).encode()
    return await call_next(request)

DATA = [
    {"region": "apac", "service": "support", "latency_ms": 176.58, "uptime_pct": 97.581, "timestamp": 20250301},
    {"region": "apac", "service": "checkout", "latency_ms": 187.92, "uptime_pct": 97.516, "timestamp": 20250302},
    {"region": "apac", "service": "support", "latency_ms": 155.31, "uptime_pct": 97.925, "timestamp": 20250303},
    {"region": "apac", "service": "catalog", "latency_ms": 138.83, "uptime_pct": 98.479, "timestamp": 20250304},
    {"region": "apac", "service": "support", "latency_ms": 213.6, "uptime_pct": 98.453, "timestamp": 20250305},
    {"region": "apac", "service": "support", "latency_ms": 167.61, "uptime_pct": 99.123, "timestamp": 20250306},
    {"region": "apac", "service": "analytics", "latency_ms": 137.87, "uptime_pct": 99.408, "timestamp": 20250307},
    {"region": "apac", "service": "checkout", "latency_ms": 175.53, "uptime_pct": 98.787, "timestamp": 20250308},
    {"region": "apac", "service": "recommendations", "latency_ms": 146.1, "uptime_pct": 98.338, "timestamp": 20250309},
    {"region": "apac", "service": "payments", "latency_ms": 179.35, "uptime_pct": 97.624, "timestamp": 20250310},
    {"region": "apac", "service": "analytics", "latency_ms": 211.22, "uptime_pct": 98.031, "timestamp": 20250311},
    {"region": "apac", "service": "recommendations", "latency_ms": 178.69, "uptime_pct": 97.449, "timestamp": 20250312},
    {"region": "emea", "service": "recommendations", "latency_ms": 240.44, "uptime_pct": 98.818, "timestamp": 20250301},
    {"region": "emea", "service": "checkout", "latency_ms": 219.38, "uptime_pct": 99.061, "timestamp": 20250302},
    {"region": "emea", "service": "checkout", "latency_ms": 160.77, "uptime_pct": 97.14, "timestamp": 20250303},
    {"region": "emea", "service": "recommendations", "latency_ms": 141.32, "uptime_pct": 98.664, "timestamp": 20250304},
    {"region": "emea", "service": "payments", "latency_ms": 195.82, "uptime_pct": 98.475, "timestamp": 20250305},
    {"region": "emea", "service": "support", "latency_ms": 154.89, "uptime_pct": 98.07, "timestamp": 20250306},
    {"region": "emea", "service": "catalog", "latency_ms": 174.46, "uptime_pct": 98.413, "timestamp": 20250307},
    {"region": "emea", "service": "catalog", "latency_ms": 214.21, "uptime_pct": 99.335, "timestamp": 20250308},
    {"region": "emea", "service": "catalog", "latency_ms": 176.77, "uptime_pct": 97.158, "timestamp": 20250309},
    {"region": "emea", "service": "checkout", "latency_ms": 227.67, "uptime_pct": 97.669, "timestamp": 20250310},
    {"region": "emea", "service": "catalog", "latency_ms": 148.78, "uptime_pct": 97.331, "timestamp": 20250311},
    {"region": "emea", "service": "analytics", "latency_ms": 162.16, "uptime_pct": 97.948, "timestamp": 20250312},
    {"region": "amer", "service": "payments", "latency_ms": 129.68, "uptime_pct": 97.643, "timestamp": 20250301},
    {"region": "amer", "service": "payments", "latency_ms": 129.73, "uptime_pct": 97.815, "timestamp": 20250302},
    {"region": "amer", "service": "checkout", "latency_ms": 163.05, "uptime_pct": 98.257, "timestamp": 20250303},
    {"region": "amer", "service": "analytics", "latency_ms": 219.15, "uptime_pct": 98.171, "timestamp": 20250304},
    {"region": "amer", "service": "checkout", "latency_ms": 136.06, "uptime_pct": 98.608, "timestamp": 20250305},
    {"region": "amer", "service": "payments", "latency_ms": 229.13, "uptime_pct": 97.103, "timestamp": 20250306},
    {"region": "amer", "service": "analytics", "latency_ms": 217.35, "uptime_pct": 97.659, "timestamp": 20250307},
    {"region": "amer", "service": "payments", "latency_ms": 139.53, "uptime_pct": 98.719, "timestamp": 20250308},
    {"region": "amer", "service": "checkout", "latency_ms": 184.41, "uptime_pct": 99.417, "timestamp": 20250309},
    {"region": "amer", "service": "support", "latency_ms": 169.54, "uptime_pct": 99.16, "timestamp": 20250310},
    {"region": "amer", "service": "checkout", "latency_ms": 116.39, "uptime_pct": 98.692, "timestamp": 20250311},
    {"region": "amer", "service": "analytics", "latency_ms": 152.65, "uptime_pct": 98.547, "timestamp": 20250312}
]


def p95(values: List[float]) -> float:
    # Same as numpy.percentile(values, 95) (linear interpolation)
    v = sorted(values)
    k = (len(v) - 1) * 0.95
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def metrics(regions: List[str], threshold: float) -> dict:
    out = {}
    for region in regions:
        rows = [r for r in DATA if r["region"] == region]
        if not rows:
            continue
        lat = [r["latency_ms"] for r in rows]
        up = [r["uptime_pct"] for r in rows]
        out[region] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": p95(lat),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > threshold),
        }
    return out


# =====================================================================
# GA1 Q6: 12-factor config precedence  ->  GET /effective-config
# =====================================================================
CFG_DEFAULTS = {"port": 8000, "workers": 1, "debug": False, "log_level": "info",
                "api_key": "default-secret-000"}
CFG_YAML = {"workers": 11, "debug": False, "log_level": "info"}          # config.development.yaml
CFG_DOTENV = {"APP_PORT": "8638", "NUM_WORKERS": "13", "APP_DEBUG": "true",
              "APP_LOG_LEVEL": "debug"}                                  # .env file
CFG_OSENV = {"APP_PORT": "8256", "APP_DEBUG": "true", "APP_LOG_LEVEL": "info"}  # OS env vars

ENV_ALIASES = {"NUM_WORKERS": "workers"}


def env_to_key(name: str):
    if name in ENV_ALIASES:
        return ENV_ALIASES[name]
    if name.startswith("APP_"):
        k = name[4:].lower()
        return "workers" if k in ("workers", "num_workers") else k
    return None


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(str(value).strip())
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return value if isinstance(value, str) else str(value)


@app.get("/effective-config")
async def effective_config(request: Request):
    cfg = dict(CFG_DEFAULTS)
    cfg.update(CFG_YAML)
    for layer in (CFG_DOTENV, CFG_OSENV):
        for name, val in layer.items():
            k = env_to_key(name)
            if k:
                cfg[k] = val
    for item in request.query_params.getlist("set"):
        if "=" in item:
            k, v = item.split("=", 1)
            k = k.strip()
            k = ENV_ALIASES.get(k, k)
            if k.upper().startswith("APP_"):
                k = env_to_key(k.upper())
            cfg[k.lower()] = v
    out = {}
    for k, v in cfg.items():
        try:
            out[k] = coerce(k, v)
        except ValueError:
            out[k] = v
    out["api_key"] = "****"
    return out


# =====================================================================
# GA1 Q14: live MCP server  ->  POST /mcp
# =====================================================================
import hashlib
import json as _json
import uuid
from fastapi.responses import JSONResponse

MCP_EMAIL = "25f1000365@ds.study.iitm.ac.in".strip().lower()
MCP_TOOL = {
    "name": "solve_challenge",
    "description": "Returns the first 16 hex chars of SHA-256(challenge:email), "
                   "using the X-Exam-Challenge request header.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}


def mcp_result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def mcp_error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def mcp_handle(msg: dict, request: Request):
    method = msg.get("method")
    msg_id = msg.get("id")
    if msg_id is None:  # notification (e.g. notifications/initialized)
        return None
    if method == "initialize":
        params = msg.get("params") or {}
        return mcp_result(msg_id, {
            "protocolVersion": params.get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tds-ga1-mcp", "version": "1.0.0"},
        })
    if method == "ping":
        return mcp_result(msg_id, {})
    if method == "tools/list":
        return mcp_result(msg_id, {"tools": [MCP_TOOL]})
    if method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return mcp_error(msg_id, -32602, f"Unknown tool: {name}")
        challenge = request.headers.get("x-exam-challenge", "")
        text = hashlib.sha256(f"{challenge}:{MCP_EMAIL}".encode()).hexdigest()[:16]
        return mcp_result(msg_id, {"content": [{"type": "text", "text": text}], "isError": False})
    return mcp_error(msg_id, -32601, f"Method not found: {method}")


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(mcp_error(None, -32700, "Parse error"), status_code=400)
    session = request.headers.get("mcp-session-id") or uuid.uuid4().hex
    headers = {"Mcp-Session-Id": session}
    if isinstance(payload, list):
        replies = [r for r in (mcp_handle(m, request) for m in payload) if r is not None]
        if not replies:
            return Response(status_code=202, headers=headers)
        return JSONResponse(replies, headers=headers)
    reply = mcp_handle(payload, request)
    if reply is None:
        return Response(status_code=202, headers=headers)
    return JSONResponse(reply, headers=headers)


@app.get("/mcp")
async def mcp_get():
    # No server-initiated SSE stream; allowed by the Streamable HTTP spec
    return Response(status_code=405, headers={"Allow": "POST"})


@app.delete("/mcp")
async def mcp_delete():
    return Response(status_code=200)


# =====================================================================
# GA1 Q15: The Ledger Agent  ->  POST /answer  {"question": "..."}
# =====================================================================
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ledger  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402


@app.post("/answer")
async def ledger_answer(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    question = str(body.get("question", "")).strip()
    if not question:
        return JSONResponse({"error": "send JSON {\"question\": \"...\"}"}, status_code=400)
    result, _query, _source = await run_in_threadpool(ledger.answer, question)
    return {"answer": result}


@app.get("/{path:path}")
async def health(request: Request, path: str = ""):
    return {"status": "ok", "version": "ga1-v2", "path_seen": request.url.path,
            "hint": "POST {\"regions\": [...], \"threshold_ms\": 180}"}


@app.options("/{path:path}")
async def preflight(path: str = ""):
    return Response(status_code=204)


@app.post("/{path:path}")
async def analytics(request: Request, path: str = ""):
    body = await request.json()
    result = metrics(body.get("regions", []), float(body.get("threshold_ms", 180)))
    # Return both shapes: {"regions": {...}} and top-level region keys
    return {"regions": result, **result}
