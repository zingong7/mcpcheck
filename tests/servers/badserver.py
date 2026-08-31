"""A server with a known list of defects, so the tests can prove each check
actually fires. Every fault in here is one I hit in a real server first.

  - prints a banner on stdout
  - echoes back whatever protocolVersion the client asked for
  - coerces request ids to integers
  - -32603 for an unknown method
  - answers notifications
  - reports success for a tool that does not exist
  - never validates arguments
  - ships two tools with the same name and no descriptions
"""

import json
import sys

TOOLS = [
    {"name": "echo", "inputSchema": {"type": "object",
                                     "properties": {"text": {"type": "string"}},
                                     "required": ["text"]}},
    {"name": "echo", "inputSchema": {"type": "object", "properties": {}}},
]


def write(msg):
    sys.stdout.buffer.write(json.dumps(msg).encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def coerce(id):
    try:
        return int(id)
    except (TypeError, ValueError):
        return 0


def handle(msg):
    id = coerce(msg.get("id"))
    method = msg.get("method")
    params = msg.get("params")
    if not isinstance(params, dict):
        params = {}

    if method == "initialize":
        return write({"jsonrpc": "2.0", "id": id, "result": {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "badserver", "version": "0.1.0"},
        }})
    if method == "tools/list":
        return write({"jsonrpc": "2.0", "id": id, "result": {"tools": TOOLS}})
    if method == "tools/call":
        return write({"jsonrpc": "2.0", "id": id,
                      "result": {"content": [{"type": "text", "text": "sure, done"}]}})
    write({"jsonrpc": "2.0", "id": id,
           "error": {"code": -32603, "message": "internal error"}})


def main():
    sys.stdout.buffer.write(b"badserver listening on stdio\n")
    sys.stdout.buffer.flush()
    for raw in sys.stdin.buffer:
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue  # swallowed, no -32700
        if isinstance(msg, dict):
            handle(msg)


if __name__ == "__main__":
    main()
