"""Tool declarations, and what happens when a tool is called wrongly.

mcpcheck never calls a tool with arguments that would let it succeed - the
worst it sends is a name that does not exist or arguments that fail validation.
"""

from mcpcheck.core import ROBUST, SPEC, Fail, Skip, check, tool_list

MISSING_NAME = "mcpcheck_no_such_tool"


def _pick_validating_tool(tools):
    """A tool whose schema demands at least one string argument."""
    for t in tools:
        schema = t.get("inputSchema") or {}
        required = schema.get("required") or []
        props = schema.get("properties") or {}
        for name in required:
            if (props.get(name) or {}).get("type") == "string":
                return t, name
    return None, None


@check("tools-shape", "every tool has a name and an object inputSchema", SPEC,
       "MCP tools: name and inputSchema are required, and inputSchema is a JSON Schema object")
def tools_shape(c):
    c.initialize()
    tools = tool_list(c)
    if not tools:
        raise Skip("server exposes no tools")
    bad = []
    for i, t in enumerate(tools):
        label = t.get("name") or "#%d" % i
        if not t.get("name") or not isinstance(t.get("name"), str):
            bad.append("%s: no usable name" % label)
            continue
        schema = t.get("inputSchema")
        if not isinstance(schema, dict):
            bad.append("%s: inputSchema is %s" % (label, type(schema).__name__))
        elif schema.get("type") != "object":
            bad.append("%s: inputSchema type is %r" % (label, schema.get("type")))
    if bad:
        raise Fail("; ".join(bad[:4]) + (" (+%d more)" % (len(bad) - 4) if len(bad) > 4 else ""))
    return "%d tools, all declared properly" % len(tools)


@check("tools-unique", "tool names are unique", SPEC,
       "MCP tools: the name is how a tool is addressed, so duplicates are unresolvable")
def tools_unique(c):
    c.initialize()
    tools = tool_list(c)
    if not tools:
        raise Skip("server exposes no tools")
    seen = {}
    for t in tools:
        seen[t.get("name")] = seen.get(t.get("name"), 0) + 1
    dupes = [n for n, count in seen.items() if count > 1]
    if dupes:
        raise Fail("duplicated: %s" % ", ".join(map(str, dupes)))
    return "%d distinct names" % len(seen)


@check("tools-described", "tools carry a description", ROBUST,
       "not required by the spec, but the description is the only thing a model has to choose on")
def tools_described(c):
    c.initialize()
    tools = tool_list(c)
    if not tools:
        raise Skip("server exposes no tools")
    bare = [t.get("name") for t in tools if not (t.get("description") or "").strip()]
    if bare:
        raise Fail("%d of %d have none: %s" % (len(bare), len(tools), ", ".join(map(str, bare[:5]))))
    shortest = min(len(t["description"]) for t in tools)
    return "all %d described, shortest is %d chars" % (len(tools), shortest)


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


@check("missing-required-arg", "a required argument is actually enforced", ROBUST,
       "MCP: servers SHOULD validate arguments against the schema they published")
def missing_required_arg(c):
    c.initialize()
    tools = tool_list(c)
    tool, arg = _pick_validating_tool(tools)
    if not tool:
        raise Skip("no tool declares a required string argument")
    resp = c.call("tools/call", {"name": tool["name"], "arguments": {}})
    if "error" in resp:
        return "%s without %r -> error %s" % (tool["name"], arg, resp["error"].get("code"))
    if (resp.get("result") or {}).get("isError"):
        return "%s without %r -> isError" % (tool["name"], arg)
    raise Fail("%s ran with its required %r missing" % (tool["name"], arg))


@check("wrong-arg-type", "an argument of the wrong type is rejected", ROBUST,
       "MCP: servers SHOULD validate arguments against the schema they published")
def wrong_arg_type(c):
    c.initialize()
    tools = tool_list(c)
    tool, arg = _pick_validating_tool(tools)
    if not tool:
        raise Skip("no tool declares a required string argument")
    resp = c.call("tools/call", {"name": tool["name"], "arguments": {arg: 12345}})
    if "error" in resp:
        return "%s with an int for %r -> error %s" % (tool["name"], arg, resp["error"].get("code"))
    if (resp.get("result") or {}).get("isError"):
        return "%s with an int for %r -> isError" % (tool["name"], arg)
    raise Fail("%s accepted an integer where its schema says string (%r)" % (tool["name"], arg))
