from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request as urlrequest

from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR.parent / "web"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


load_env_file(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
TOKENS: dict[str, str] = {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
            """
        )


init_db()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def extract_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.removeprefix("Bearer ").strip()


def require_user() -> str:
    token = extract_token()
    if not token or token not in TOKENS:
        raise PermissionError("Unauthorized")
    return TOKENS[token]


def create_session_if_needed(conn: sqlite3.Connection, username: str, session_id: int | None) -> int:
    now = utc_now_iso()
    if session_id:
        row = conn.execute(
            "SELECT id FROM sessions WHERE id = ? AND username = ?",
            (session_id, username),
        ).fetchone()
        if row:
            return int(row["id"])

    title = f"Chat {datetime.now().strftime('%m-%d %H:%M')}"
    cursor = conn.execute(
        "INSERT INTO sessions (username, title, updated_at, created_at) VALUES (?, ?, ?, ?)",
        (username, title, now, now),
    )
    return int(cursor.lastrowid)


def generate_companion_reply(user_message: str) -> str:
    text = user_message.strip()
    if not text:
        return "我在，想和我聊点什么？"

    lowered = text.lower()
    if any(word in lowered for word in ["累", "烦", "压力", "stress", "tired"]):
        return "听起来你今天有点累，我们可以先慢下来。要不要先讲讲最让你疲惫的一件事？"
    if "?" in text or "吗" in text:
        return f"这是个好问题。按你的情况，我会先从最容易执行的一步开始。你愿意先试试看吗？"
    return f"我收到啦：{text}\n\n继续说，我会一直在这陪你聊。"


def generate_azure_reply(user_message: str) -> str | None:
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview").strip()

    if not api_key or not endpoint or not deployment:
        return None

    # Accept both resource root and /openai/v1 style endpoints.
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[: -len("/openai/v1")]

    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "你是一个温和、自然、会倾听的中文陪聊助手。回答简洁、有温度。",
            },
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.8,
        "max_tokens": 250,
    }

    req = urlrequest.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            choices = body.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = (message.get("content") or "").strip()
            return content or None
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def azure_resource_base() -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[: -len("/openai/v1")]
    return endpoint


def mint_realtime_session() -> tuple[dict[str, Any] | None, str | None]:
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    base = azure_resource_base()
    deployment = os.getenv("AZURE_OPENAI_REALTIME_DEPLOYMENT", "").strip()
    voice = os.getenv("AZURE_OPENAI_REALTIME_VOICE", "alloy").strip() or "alloy"

    if not api_key or not base or not deployment:
        return None, "missing_realtime_env"

    url = f"{base}/openai/v1/realtime/client_secrets"
    payload = {
        "session": {
            "type": "realtime",
            "model": deployment,
            "instructions": "你是一个温和、自然、会倾听的中文语音陪聊助手。语气亲切，回答简洁而有温度。",
            "audio": {
                "input": {"transcription": {"model": "whisper-1"}},
                "output": {"voice": voice},
            },
        }
    }

    req = urlrequest.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return None, f"http_error:{exc.code}"
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None, "request_failed"

    token = body.get("value") or (body.get("client_secret") or {}).get("value")
    if not token:
        return None, "no_token_in_response"

    return {
        "token": token,
        "webrtc_url": f"{base}/openai/v1/realtime/calls",
        "model": deployment,
        "voice": voice,
        "expires_at": body.get("expires_at"),
    }, None


@app.get("/")
def index() -> Any:
    return app.send_static_file("index.html")


@app.get("/api/health")
def health() -> Any:
    chat_required = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_CHAT_DEPLOYMENT"]
    chat_missing = [name for name in chat_required if not os.getenv(name, "").strip()]
    realtime_required = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_REALTIME_DEPLOYMENT"]
    realtime_missing = [name for name in realtime_required if not os.getenv(name, "").strip()]
    passcode_configured = bool(os.getenv("APP_ACCESS_PASSCODE", "").strip())
    azure_ready = len(chat_missing) == 0
    return jsonify(
        {
            "ok": True,
            "azure_chat_ready": azure_ready,
            "mode": "azure" if azure_ready else "local-fallback",
            "missing_azure_env": chat_missing,
            "realtime_ready": len(realtime_missing) == 0,
            "missing_realtime_env": realtime_missing,
            "access_gate_enabled": True,
            "access_passcode_configured": passcode_configured,
        }
    )


@app.post("/api/realtime/session")
def realtime_session() -> Any:
    try:
        require_user()
    except PermissionError:
        return jsonify({"error": "unauthorized"}), 401

    data, err = mint_realtime_session()
    if err:
        return jsonify({"error": err}), 502
    return jsonify(data)


@app.post("/api/auth/login")
def login() -> Any:
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()
    access_passcode = (body.get("access_passcode") or "").strip()
    expected_passcode = os.getenv("APP_ACCESS_PASSCODE", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if not expected_passcode:
        return jsonify({"error": "server access passcode is not configured"}), 503

    if access_passcode != expected_passcode:
        return jsonify({"error": "invalid access passcode"}), 403

    now = utc_now_iso()
    pwd_hash = hash_password(password)

    with db_connect() as conn:
        existing = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, pwd_hash, now),
            )
        elif existing["password_hash"] != pwd_hash:
            return jsonify({"error": "wrong password"}), 401

    token = secrets.token_urlsafe(24)
    TOKENS[token] = username
    return jsonify({"token": token, "username": username})


@app.get("/api/sessions")
def list_sessions() -> Any:
    try:
        username = require_user()
    except PermissionError:
        return jsonify({"error": "unauthorized"}), 401

    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, updated_at, created_at
            FROM sessions
            WHERE username = ?
            ORDER BY updated_at DESC
            """,
            (username,),
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.get("/api/sessions/<int:session_id>/messages")
def list_messages(session_id: int) -> Any:
    try:
        username = require_user()
    except PermissionError:
        return jsonify({"error": "unauthorized"}), 401

    with db_connect() as conn:
        session_row = conn.execute(
            "SELECT id FROM sessions WHERE id = ? AND username = ?",
            (session_id, username),
        ).fetchone()
        if session_row is None:
            return jsonify({"error": "session not found"}), 404

        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/chat")
def chat() -> Any:
    try:
        username = require_user()
    except PermissionError:
        return jsonify({"error": "unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    user_message = (body.get("message") or "").strip()
    session_id = body.get("session_id")

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    ai_reply = generate_azure_reply(user_message) or generate_companion_reply(user_message)
    now = utc_now_iso()

    with db_connect() as conn:
        active_session_id = create_session_if_needed(conn, username, session_id)
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (active_session_id, "user", user_message, now),
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (active_session_id, "assistant", ai_reply, now),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, active_session_id),
        )

    return jsonify({"session_id": active_session_id, "reply": ai_reply})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("FLASK_DEBUG", "0").strip() == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
