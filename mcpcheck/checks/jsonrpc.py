"""JSON-RPC 2.0 conformance. None of this is MCP specific - it is the layer
underneath, and it is where most of the surprises turned up."""

import json

from mcpcheck.client import ServerGone, Timeout
from mcpcheck.core import ROBUST, SPEC, Fail, Warn, check, want_error, want_result

METHOD_NOT_FOUND = -32601
INVALID_REQUEST = -32600
PARSE_ERROR = -32700
INVALID_PARAMS = -32602


@check("unknown-method", "unknown method returns -32601", SPEC,
       "JSON-RPC 2.0 s5.1")
def unknown_method(c):
    c.initialize()
    resp = c.call("mcpcheck/definitely-not-a-method")
    err = want_error(resp, METHOD_NOT_FOUND)
    return (err.get("message") or "")[:60]


@check("no-method", "request with no method returns -32600", SPEC,
       "JSON-RPC 2.0 s5.1: an object without a method member is not a valid request")
def no_method(c):
    c.initialize()
    rid = c.new_id()
    c.drain(0.4)
    c.send_line(json.dumps({"jsonrpc": "2.0", "id": rid}))
    try:
        resp = c.await_response(timeout=6)
    except Timeout:
        raise Fail("dropped silently - no response of any kind, so a client just waits")
    err = want_error(resp)
    if resp.get("id") != rid:
        return "errored, but with id %r instead of %r" % (resp.get("id"), rid)
    if err["code"] != INVALID_REQUEST:
        raise Warn("errored with %s rather than -32600" % err["code"])
    return "-32600"


@check("no-version", "request without jsonrpc:2.0 is rejected", SPEC,
       "JSON-RPC 2.0 s4: the jsonrpc member MUST be exactly '2.0'")
def no_version(c):
    c.initialize()
    rid = c.new_id()
    c.drain(0.4)
    c.send_line(json.dumps({"id": rid, "method": "tools/list", "params": {}}))
    try:
        resp = c.await_response(timeout=6)
    except Timeout:
        raise Fail("dropped silently - no response of any kind, so a client just waits")
    if "error" not in resp:
        raise Fail("served the request anyway")
    return "rejected with %s" % resp["error"].get("code")


@check("parse-error", "broken JSON returns -32700", SPEC,
       "JSON-RPC 2.0 s5.1")
def parse_error(c):
    c.initialize()
    c.drain(0.4)
    c.send_line('{"jsonrpc": "2.0", "id": 99, "method": ')
    try:
        resp = c.await_response(timeout=6)
    except Timeout:
        logged = [m for m in c.messages
                  if isinstance(m, dict) and m.get("method") == "notifications/message"]
        if logged:
            raise Fail("logged the parse error as a notification instead of answering it")
        raise Fail("no parse error came back")
    except ServerGone:
        raise Fail("server exited on malformed input")
    if not isinstance(resp, dict) or "error" not in resp:
        raise Fail("expected -32700, got %s" % str(resp)[:80])
    if resp["error"].get("code") != PARSE_ERROR:
        raise Warn("errored with %s rather than -32700" % resp["error"].get("code"))
    return "-32700"


@check("parse-error-survives", "the session outlives a malformed message", ROBUST,
       "not specified; one bad line from a proxy or a stray log write should not end the session")
def parse_error_survives(c):
    c.initialize()
    c.send_line("this is not json at all")
    try:
        want_result(c.call("tools/list", timeout=8))
    except (Timeout, ServerGone) as e:
        raise Fail("session unusable afterwards: %s" % e)
    return "recovered"


@check("id-echo", "response id matches the request id exactly", SPEC,
       "JSON-RPC 2.0 s5: id MUST be the same value, and the comparison is type sensitive")
def id_echo(c):
    c.initialize()
    rid = "mcpcheck-7"
    c.send("tools/list", {}, id=rid)
    try:
        resp = c.await_id(rid, timeout=8)
    except Timeout:
        seen = [m.get("id") for m in c.messages if isinstance(m, dict) and "id" in m]
        raise Fail("nothing came back carrying id %r (ids seen: %r)" % (rid, seen[-3:]))
    if resp.get("id") != rid:
        raise Fail("asked with %r, answered with %r" % (rid, resp.get("id")))
    return "string ids round trip"


@check("response-shape", "responses carry jsonrpc:2.0 and exactly one of result/error", SPEC,
       "JSON-RPC 2.0 s5")
def response_shape(c):
    resp = c.initialize()
    problems = []
    if resp.get("jsonrpc") != "2.0":
        problems.append("jsonrpc is %r" % resp.get("jsonrpc"))
    if ("result" in resp) == ("error" in resp):
        problems.append("has both result and error" if "result" in resp else "has neither")
    if problems:
        raise Fail("; ".join(problems))
    return "well formed"


@check("notification-silence", "an unknown notification draws no response", SPEC,
       "JSON-RPC 2.0 s4.1: the server MUST NOT reply to a notification")
def notification_silence(c):
    c.initialize()
    c.notify("notifications/mcpcheck-unknown", {"note": "ignore me"})
    stray = [m for m in c.quiet_for(2.0)
             if isinstance(m, dict) and "id" in m and ("result" in m or "error" in m)]
    if stray:
        raise Fail("answered a notification with %s" % str(stray[0])[:80])
    return "silent"


@check("invalid-params", "wrong-shaped params are refused", SPEC,
       "JSON-RPC 2.0 s5.1: -32602 for invalid params")
def invalid_params(c):
    c.initialize()
    c.drain(0.4)
    rid = c.new_id()
    c.send_line(json.dumps({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                            "params": "this should be an object"}))
    try:
        resp = c.await_response(timeout=8)
    except Timeout:
        raise Fail("no response to a request whose params were a string")
    except ServerGone:
        raise Fail("server exited on string params")
    err = want_error(resp)
    if err["code"] != INVALID_PARAMS:
        raise Warn("errored with %s rather than -32602" % err["code"])
    return "-32602"


@check("pipelined-ids", "three requests in flight all come back", SPEC,
       "MCP: requests are asynchronous, a client does not have to wait for each reply")
def pipelined_ids(c):
    c.initialize()
    c.drain(0.4)
    ids = [c.new_id() for _ in range(3)]
    for rid in ids:
        c.send("tools/list", {}, id=rid)
    seen = []
    try:
        while len(seen) < 3:
            msg = c.recv(timeout=10)
            if isinstance(msg, dict) and "id" in msg:
                seen.append(msg["id"])
    except Timeout:
        raise Fail("only %d of 3 replies arrived (%r)" % (len(seen), seen))
    except ServerGone:
        raise Fail("server exited after sending %d of 3 replies" % len(seen))
    if sorted(map(str, seen)) != sorted(map(str, ids)):
        raise Fail("sent %r, got back %r" % (ids, seen))
    return "all three, order irrelevant"
