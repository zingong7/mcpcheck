"""A deliberately correct MCP stdio server, used to check that mcpcheck is not
just failing everything. Hand rolled rather than built on the SDK so that the
tests do not depend on whatever the SDK happens to do this month.
"""

import json
import sys

VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18"]

ready = False

TOOLS = [
    {
        "name": "echo",
        "description": "Return the text you pass in, unchanged.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "What to echo back."}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "Add two numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Left operand."},
                "b": {"type": "number", "description": "Right operand."},
            },
            "required": ["a", "b"],
        },
    },
]


def write(msg):
    sys.stdout.buffer.write(json.dumps(msg).encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def error(id, code, message):
    write({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})


def result(id, payload):
    write({"jsonrpc": "2.0", "id": id, "result": payload})


def call_tool(id, params):
    name = params.get("name")
    args = params.get("arguments") or {}
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if spec is None:
        return error(id, -32602, "unknown tool: %r" % (name,))

    schema = spec["inputSchema"]
    for required in schema["required"]:
        if required not in args:
            return result(id, {"isError": True,
                               "content": [{"type": "text", "text": "missing argument %s" % required}]})
    types = {"string": str, "number": (int, float)}
    for key, value in args.items():
        want = types.get((schema["properties"].get(key) or {}).get("type"))
        if want and not isinstance(value, want):
            return result(id, {"isError": True,
                               "content": [{"type": "text", "text": "%s has the wrong type" % key}]})

    if name == "echo":
        text = args["text"]
    else:
        text = str(args["a"] + args["b"])
    return result(id, {"content": [{"type": "text", "text": text}]})


def handle(msg):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return error(msg.get("id") if isinstance(msg, dict) else None,
                     -32600, "not a JSON-RPC 2.0 request")

    id = msg.get("id")
    method = msg["method"]
    params = msg.get("params")

    if params is not None and not isinstance(params, (dict, list)):
        return error(id, -32602, "params must be an object or array")
    if id is None:
        return  # notification: say nothing

    if method == "initialize":
        global ready
        ready = True
        asked = (params or {}).get("protocolVersion")
        return result(id, {
            "protocolVersion": asked if asked in VERSIONS else VERSIONS[-1],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "goodserver", "version": "1.0.0"},
        })
    if not ready:
        return error(id, -32600, "not initialized yet")
    if method == "tools/list":
        return result(id, {"tools": TOOLS})
    if method == "tools/call":
        return call_tool(id, params or {})
    return error(id, -32601, "method not found: %s" % method)


def main():
    for raw in sys.stdin.buffer:
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            error(None, -32700, "parse error")
            continue
        if isinstance(msg, list):
            error(None, -32600, "batches are not supported")
            continue
        handle(msg)


if __name__ == "__main__":
    main()
