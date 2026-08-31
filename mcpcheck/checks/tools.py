"""Tool declarations, and what happens when a tool that does not exist is called.

mcpcheck never calls a real tool - the only name it ever sends is one no server
has, so pointing it at a server with side effects is safe.
"""

from mcpcheck.core import ROBUST, SPEC, Fail, Skip, check, tool_list

MISSING_NAME = "mcpcheck_no_such_tool"


@check("params-described", "tool arguments carry descriptions", ROBUST,
       "not required; an argument with no description is guesswork for the model filling it in")
def params_described(c):
    c.initialize()
    tools = tool_list(c)
    if not tools:
        raise Skip("server exposes no tools")
    total = undescribed = 0
    worst = []
    for t in tools:
        props = ((t.get("inputSchema") or {}).get("properties")) or {}
        for pname, spec in props.items():
            total += 1
            if not isinstance(spec, dict) or not (spec.get("description") or "").strip():
                undescribed += 1
                worst.append("%s.%s" % (t.get("name"), pname))
    if not total:
        raise Skip("no tool takes arguments")
    if undescribed:
        raise Fail("%d of %d undescribed: %s" % (undescribed, total, ", ".join(worst[:5])))
    return "all %d arguments described" % total


@check("unknown-tool", "calling a tool that does not exist is an error", SPEC,
       "MCP tools: an unknown tool name is an error, either a JSON-RPC error or isError on the result")
def unknown_tool(c):
    c.initialize()
    tool_list(c)
    resp = c.call("tools/call", {"name": MISSING_NAME, "arguments": {}})
    if "error" in resp:
        return "JSON-RPC error %s" % resp["error"].get("code")
    result = resp.get("result") or {}
    if result.get("isError"):
        return "isError result"
    raise Fail("reported success for a tool that does not exist")
