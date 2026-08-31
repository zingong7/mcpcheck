"""Handshake checks."""

from mcpcheck.core import SPEC, Fail, Warn, check, want_result

# only used to tell "negotiated properly" from "replied with something odd";
# a missing entry here shows up as a warning, not a failure
KNOWN_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}


@check("init-shape", "initialize returns the required fields", SPEC,
       "MCP lifecycle: InitializeResult carries protocolVersion, capabilities, serverInfo")
def init_shape(c):
    result = want_result(c.initialize())
    missing = [k for k in ("protocolVersion", "capabilities", "serverInfo") if k not in result]
    if missing:
        raise Fail("missing from InitializeResult: %s" % ", ".join(missing))
    info = result.get("serverInfo") or {}
    if not info.get("name"):
        raise Fail("serverInfo has no name")
    return "%s %s, protocol %s" % (info.get("name"), info.get("version", "?"),
                                   result["protocolVersion"])


@check("init-version", "unsupported protocol version is negotiated, not echoed", SPEC,
       "MCP lifecycle: a server that does not support the requested version MUST reply with one it does")
def init_version(c):
    bogus = "1999-01-01"
    result = want_result(c.initialize(protocol_version=bogus))
    got = result.get("protocolVersion")
    if got == bogus:
        raise Fail("echoed back %s, which no server supports" % bogus)
    if got not in KNOWN_VERSIONS:
        raise Warn("replied %s, which is not a version mcpcheck knows" % got)
    return "negotiated down to %s" % got
