"""Runs the battery against one server.

Every check gets its own process. That is slow - a run is one spawn per check -
but several checks are about what happens after the server has been mistreated,
and sharing a session would let one check's damage show up as another's failure.
"""

import sys
import time

from mcpcheck.client import RawClient, ServerGone, Timeout
from mcpcheck.core import ERROR, FAIL, PASS, SKIP, WARN, Fail, Result, Skip, Warn, load_all


class Server:
    def __init__(self, name, command, args=None, env=None, cwd=None, notes=""):
        self.name = name
        # "python" means whatever interpreter is running mcpcheck, so a servers
        # file stays portable across venvs
        self.command = sys.executable if command == "python" else command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = cwd
        self.notes = notes

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["command"], d.get("args"), d.get("env"),
                   d.get("cwd"), d.get("notes", ""))

    def client(self, timeout):
        return RawClient(self.command, self.args, self.env, self.cwd, timeout)


class ServerRun:
    def __init__(self, server):
        self.server = server
        self.results = []
        self.reachable = True
        self.problem = ""
        self.identity = ""

    def counts(self):
        out = {PASS: 0, WARN: 0, FAIL: 0, SKIP: 0, ERROR: 0}
        for r in self.results:
            out[r.status] += 1
        return out

    def failures(self, severity=None):
        return [r for r in self.results
                if r.status == FAIL and (severity is None or r.check.severity == severity)]

    def as_dict(self):
        return {
            "server": self.server.name,
            "command": " ".join([self.server.command] + self.server.args),
            "reachable": self.reachable,
            "problem": self.problem,
            "identity": self.identity,
            "counts": self.counts(),
            "results": [r.as_dict() for r in self.results],
        }


def probe(server, timeout=20):
    """One handshake, to tell 'this server is broken' apart from 'this server
    is not installed'."""
    c = server.client(timeout)
    try:
        c.start()
    except FileNotFoundError:
        return False, "command not found: %s" % server.command, ""
    except OSError as e:
        return False, str(e), ""
    try:
        resp = c.initialize()
        info = (resp.get("result") or {}).get("serverInfo") or {}
        return True, "", "%s %s" % (info.get("name", "?"), info.get("version", ""))
    except Timeout:
        return False, "no reply to initialize in %ss" % timeout, ""
    except ServerGone:
        tail = " | ".join(c.stderr_tail[-3:])[:200]
        return False, "exited during initialize%s" % (": " + tail if tail else ""), ""
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e), ""
    finally:
        c.stop()


def run_server(server, only=None, timeout=10, on_result=None):
    run = ServerRun(server)
    ok, problem, identity = probe(server)
    run.reachable, run.problem, run.identity = ok, problem, identity
    if not ok:
        return run

    for chk in load_all():
        if only and chk.id not in only:
            continue
        run.results.append(run_check(server, chk, timeout))
        if on_result:
            on_result(run.results[-1])
    return run


def run_check(server, chk, timeout):
    started = time.time()
    c = server.client(timeout)
    try:
        c.start()
        detail = chk.fn(c) or ""
        return Result(chk, PASS, detail, time.time() - started)
    except Warn as e:
        return Result(chk, WARN, str(e), time.time() - started)
    except Fail as e:
        return Result(chk, FAIL, str(e), time.time() - started)
    except Skip as e:
        return Result(chk, SKIP, str(e), time.time() - started)
    except Timeout as e:
        return Result(chk, FAIL, "timed out: %s" % e, time.time() - started)
    except ServerGone as e:
        tail = " | ".join(c.stderr_tail[-2:])[:160]
        return Result(chk, FAIL, "server exited: %s%s" % (e, " | " + tail if tail else ""),
                      time.time() - started)
    except Exception as e:
        return Result(chk, ERROR, "%s: %s" % (type(e).__name__, e), time.time() - started)
    finally:
        try:
            c.stop()
        except Exception:
            pass
