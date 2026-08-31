"""Check registry and result types."""

SPEC = "spec"        # a MUST in JSON-RPC 2.0 or the MCP spec
ROBUST = "robust"    # not required anywhere, but servers that get it wrong hurt

PASS = "pass"
WARN = "warn"       # answers, but not the way the spec words it
FAIL = "fail"
SKIP = "skip"
ERROR = "error"      # mcpcheck itself broke, not the server

REGISTRY = []


class Fail(Exception):
    pass


class Warn(Exception):
    pass


class Skip(Exception):
    pass


class Check:
    def __init__(self, fn, id, title, severity, ref, notes=None):
        self.fn = fn
        self.id = id
        self.title = title
        self.severity = severity
        self.ref = ref
        self.notes = notes


class Result:
    def __init__(self, check, status, detail="", seconds=0.0):
        self.check = check
        self.status = status
        self.detail = detail
        self.seconds = seconds

    def as_dict(self):
        return {
            "id": self.check.id,
            "title": self.check.title,
            "severity": self.check.severity,
            "ref": self.check.ref,
            "status": self.status,
            "detail": self.detail,
            "seconds": round(self.seconds, 3),
        }


def check(id, title, severity, ref, notes=None):
    def wrap(fn):
        REGISTRY.append(Check(fn, id, title, severity, ref, notes))
        return fn
    return wrap


def load_all():
    from mcpcheck.checks import lifecycle, jsonrpc, tools, robustness  # noqa: F401
    return REGISTRY


# -- helpers the checks share ----------------------------------------------

def want_error(resp, code=None, label=""):
    if not isinstance(resp, dict):
        raise Fail("expected a response object, got %r" % type(resp).__name__)
    if "error" not in resp:
        raise Fail("%sexpected an error, got a result" % (label and label + ": "))
    err = resp["error"]
    if not isinstance(err, dict) or "code" not in err:
        raise Fail("error member is malformed: %r" % (err,))
    if code is not None and err["code"] != code:
        raise Fail("expected code %d, got %s (%s)" % (code, err["code"], err.get("message", "")))
    return err


def want_result(resp):
    if not isinstance(resp, dict):
        raise Fail("expected a response object, got %r" % type(resp).__name__)
    if "error" in resp:
        e = resp["error"]
        raise Fail("server returned error %s: %s" % (e.get("code"), e.get("message")))
    if "result" not in resp:
        raise Fail("response has neither result nor error")
    return resp["result"]


def tool_list(client):
    result = want_result(client.call("tools/list"))
    tools = result.get("tools")
    if tools is None:
        raise Fail("tools/list result has no 'tools' array")
    return tools
