"""Handshake and capability checks."""

from mcpcheck.client import ServerGone, Timeout
from mcpcheck.core import ROBUST, SPEC, Fail, Skip, Warn, check, want_result

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


@check("init-twice", "a second initialize does not take the server down", ROBUST,
       "not specified; a client that reconnects badly should not be able to kill the process")
def init_twice(c):
    c.initialize()
    try:
        c.initialize()
    except (Timeout, ServerGone) as e:
        raise Fail("second initialize: %s" % e)
    # what matters is whether the session still works afterwards
    want_result(c.call("tools/list"))
    return "still serving after a duplicate handshake"


@check("pre-init", "a request before initialize is refused, not crashed on", ROBUST,
       "MCP lifecycle: clients SHOULD NOT send requests before initialize; server behaviour is unspecified")
def pre_init(c):
    rid = c.new_id()
    c.send("tools/list", {}, id=rid)
    try:
        resp = c.await_id(rid, timeout=5)
    except Timeout:
        raise Fail("no reply at all - a client that gets the order wrong just hangs")
    except ServerGone:
        raise Fail("server exited")
    if "error" in resp:
        return "refused with %s" % resp["error"].get("code")
    raise Warn("answered it anyway - allowed, but the handshake is then decorative")


@check("caps-honoured", "declared capabilities actually work", SPEC,
       "MCP: a server that advertises a capability has to serve it")
def caps_honoured(c):
    result = want_result(c.initialize())
    caps = result.get("capabilities") or {}
    served = []
    for name, method in (("tools", "tools/list"),
                         ("resources", "resources/list"),
                         ("prompts", "prompts/list")):
        if name not in caps:
            continue
        resp = c.call(method)
        if "error" in resp:
            raise Fail("advertises %s but %s returned %s: %s"
                       % (name, method, resp["error"].get("code"),
                          resp["error"].get("message")))
        served.append(name)
    if not served:
        raise Skip("advertises none of tools, resources or prompts")
    return "serves " + ", ".join(served)
