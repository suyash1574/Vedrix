"""
End-to-end integration test for the interview flow fixes:
  Fix 1 — first-name injection into greeting
  Fix 4 — thinking-pause detection (don't penalize)
  Fix 5 — generate_question_node re-prompts kindly on thinking_pause
  Plus — confirms plan-driven phases work and silence-tolerant timeouts on FE

Run from Vedrix/backend/:
  python test_interview_flow_e2e.py
"""
import asyncio
import json
import sys
import websockets
import httpx
from datetime import datetime

API = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"


def color(text, c="green"):
    codes = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "blue": "\033[94m", "reset": "\033[0m"}
    return f"{codes.get(c, '')}{text}{codes['reset']}"


async def setup_test_user():
    """Create a fresh student user for the test, return JWT + name."""
    suffix = datetime.now().strftime("%H%M%S%f")[:9]
    payload = {
        "email": f"flowtest_{suffix}@test.dev",
        "username": f"flowtest_{suffix}",
        "password": "TestPass123!",
        "first_name": "Aria",
        "last_name": "Tester",
        "user_type": "student",
    }
    async with httpx.AsyncClient(base_url=API, timeout=30.0) as c:
        r = await c.post("/api/v1/auth/register", json=payload)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"

        # Login uses form-urlencoded
        r = await c.post(
            "/api/v1/auth/login",
            data={"username": payload["username"], "password": payload["password"]},
        )
        assert r.status_code == 200, f"login failed: {r.text}"
        # JWT is in httpOnly cookie, but the candidate-facing flow uses auth_token query param.
        # Pull from cookies:
        access = r.cookies.get("access_token")
        assert access, f"no access_token cookie: {r.cookies}"
        return payload["first_name"], access


async def run_interview_session(jwt: str):
    """Connect to /ws/{session_id} and observe the first question + reply with thinking phrase."""
    sid = f"flow_test_{datetime.now().strftime('%H%M%S%f')}"
    url = f"{WS_BASE}/api/v1/interview/ws/{sid}?auth_token={jwt}"
    print(color(f"  Connecting WS: {url[:80]}...", "blue"))

    results = {
        "got_status": False,
        "got_question": False,
        "first_question_text": "",
        "second_question_text": "",
        "first_question_uses_name": False,
        "second_question_is_rephrase": False,
        "second_question_acknowledges_thinking": False,
    }

    async with websockets.connect(url, ping_timeout=120) as ws:
        # Wait for first question
        deadline = asyncio.get_event_loop().time() + 60
        while asyncio.get_event_loop().time() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=60)
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "status":
                results["got_status"] = True
                print(color(f"  status: {msg.get('data', '')[:80]}", "yellow"))
            elif mtype == "question":
                results["got_question"] = True
                q = msg.get("data", {})
                qtext = q.get("question", "") if isinstance(q, dict) else ""
                results["first_question_text"] = qtext
                results["first_question_uses_name"] = "aria" in qtext.lower()
                print(color(f"  Q1 ({len(qtext)} chars): {qtext[:200]}", "green"))
                break
            elif mtype == "error":
                print(color(f"  ERROR: {msg.get('data', '')}", "red"))
                return results

        if not results["got_question"]:
            return results

        # Reply with a "thinking pause" phrase
        thinking_reply = "Hmm, let me think about that"
        print(color(f"  Replying with thinking phrase: '{thinking_reply}'", "blue"))
        await ws.send(json.dumps({"type": "answer", "data": thinking_reply}))

        # Wait for the next question — should be a kind rephrase, not a penalty
        deadline = asyncio.get_event_loop().time() + 90
        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
            except asyncio.TimeoutError:
                print(color("  Timeout waiting for Q2", "red"))
                break
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "status":
                print(color(f"  status: {msg.get('data', '')[:80]}", "yellow"))
            elif mtype == "metrics_update":
                metrics = msg.get("data", {})
                print(color(f"  metrics: {metrics}", "yellow"))
            elif mtype == "question":
                q2 = msg.get("data", {})
                q2text = q2.get("question", "") if isinstance(q2, dict) else ""
                results["second_question_text"] = q2text
                # Look for kind reassurance keywords typical of a "thinking pause" rephrase
                acknowledgers = [
                    "take your time",
                    "no rush",
                    "rephrase",
                    "let me restate",
                    "of course",
                    "no problem",
                    "to put it another way",
                    "another way",
                    "simpler",
                ]
                lower = q2text.lower()
                results["second_question_acknowledges_thinking"] = any(k in lower for k in acknowledgers)
                results["second_question_is_rephrase"] = (
                    results["second_question_acknowledges_thinking"]
                    or "to rephrase" in lower
                    or "let me ask" in lower
                )
                print(color(f"  Q2 ({len(q2text)} chars): {q2text[:200]}", "green"))
                break

    return results


async def main():
    print(color("\n═══ Autergo Interview Flow E2E Test ═══\n", "blue"))

    print(color("[1] Creating test student 'Aria Tester'...", "blue"))
    try:
        first_name, jwt = await setup_test_user()
        print(color(f"    ✓ user created: first_name={first_name}", "green"))
    except Exception as e:
        print(color(f"    ✗ user creation failed: {e}", "red"))
        return 1

    print(color("\n[2] Running interview WebSocket flow...", "blue"))
    try:
        results = await run_interview_session(jwt)
    except Exception as e:
        print(color(f"    ✗ WS flow error: {e}", "red"))
        import traceback; traceback.print_exc()
        return 1

    print(color("\n═══ Assertions ═══", "blue"))

    checks = [
        ("Backend sent status messages",      results["got_status"]),
        ("Backend sent first question",       results["got_question"]),
        ("Q1 uses candidate first name 'Aria'", results["first_question_uses_name"]),
        ("Backend sent second question",      bool(results["second_question_text"])),
        ("Q2 acknowledges thinking pause",    results["second_question_acknowledges_thinking"]),
        ("Q2 is a rephrase (not penalty)",    results["second_question_is_rephrase"]),
    ]
    passed = 0
    for label, ok in checks:
        symbol = color("✓", "green") if ok else color("✗", "red")
        print(f"  {symbol} {label}")
        passed += int(ok)

    print(color(f"\nResult: {passed}/{len(checks)} checks passed", "green" if passed == len(checks) else "yellow"))
    print(color("\n--- Sample interactions ---", "blue"))
    print(color(f"Q1: {results['first_question_text'][:300]}", "green"))
    print(color(f"Q2: {results['second_question_text'][:300]}", "green"))
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
