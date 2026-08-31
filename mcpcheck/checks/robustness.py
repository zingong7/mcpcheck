"""Transport level abuse. Nothing here calls a real tool with valid arguments -
the target is always a name that does not exist, so the only thing under test is
how the server handles the message itself.
"""

import json

from mcpcheck.client import ServerGone, Timeout
from mcpcheck.core import ROBUST, SPEC, Fail, check, want_result

MISSING_NAME = "mcpcheck_no_such_tool"


def _junk_call(c, arguments, timeout=15):
    rid = c.new_id()
    c.send("tools/call", {"name": MISSING_NAME, "arguments": arguments}, id=rid)
    return c.await_id(rid, timeout=timeout)


@check("stdout-clean", "nothing but MCP messages goes to stdout", SPEC,
       "MCP stdio transport: the server MUST NOT write anything to stdout that is not a valid MCP message")
def stdout_clean(c):
    c.initialize()
    c.call("tools/list")
    c.call("mcpcheck/definitely-not-a-method")
    c.quiet_for(0.5)
    if c.junk_stdout:
        raise Fail("%d non-message line(s) on stdout, first: %r"
                   % (len(c.junk_stdout), c.junk_stdout[0][:120]))
    return "clean"


@check("deep-nesting", "a deeply nested argument is refused, not fatal", ROBUST,
       "not specified; recursive parsers tend to blow the stack somewhere and it should be an error")
def deep_nesting(c):
    c.initialize()
    nested = {}
    cursor = nested
    for _ in range(400):
        cursor["n"] = {}
        cursor = cursor["n"]
    try:
        resp = _junk_call(c, {"deep": nested})
    except Timeout:
        raise Fail("no response to 400 levels of nesting")
    except ServerGone:
        raise Fail("server exited on 400 levels of nesting")
    if not isinstance(resp, dict):
        raise Fail("got %s back" % type(resp).__name__)
    return "handled, %s" % ("error" if "error" in resp else "result")


@check("no-batch-crash", "a JSON-RPC batch is answered or refused, not fatal", ROBUST,
       "batching was removed in MCP 2025-06-18, so the useful question is only whether it is survivable")
def no_batch_crash(c):
    c.initialize()
    batch = [
        {"jsonrpc": "2.0", "id": 9001, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 9002, "method": "tools/list", "params": {}},
    ]
    c.send_line(json.dumps(batch))
    c.quiet_for(1.5)
    try:
        want_result(c.call("tools/list", timeout=8))
    except (Timeout, ServerGone) as e:
        raise Fail("session dead after a batch: %s" % e)
    return "survived"
