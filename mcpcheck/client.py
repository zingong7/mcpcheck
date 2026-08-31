"""Raw stdio JSON-RPC client. Deliberately not built on the MCP SDK - half the
checks send things a well behaved client would never send."""

import json
import queue
import subprocess
import sys
import threading
import time

DEFAULT_TIMEOUT = 10.0
PROTOCOL_VERSION = "2025-06-18"


class Timeout(Exception):
    pass


class ServerGone(Exception):
    pass


class RawClient:
    def __init__(self, command, args=None, env=None, cwd=None, timeout=DEFAULT_TIMEOUT):
        self.command = command
        self.args = list(args or [])
        self.env = env
        self.cwd = cwd
        self.timeout = timeout

        self.proc = None
        self._inbox = queue.Queue()
        self._reader = None
        self._next_id = 1

        # everything the server put on stdout that wasn't a JSON object
        self.junk_stdout = []
        self.stderr_tail = []
        self.messages = []          # every parsed message, in arrival order

    # -- lifecycle ---------------------------------------------------------

    def start(self):
        popen_env = None
        if self.env:
            import os
            popen_env = dict(os.environ)
            popen_env.update(self.env)

        self.proc = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=popen_env,
            cwd=self.cwd,
            bufsize=0,
        )
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        return self

    def _read_stdout(self):
        buf = b""
        try:
            while True:
                chunk = self.proc.stdout.read(1)
                if not chunk:
                    break
                if chunk == b"\n":
                    line = buf.decode("utf-8", "replace").strip()
                    buf = b""
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        self.junk_stdout.append(line[:400])
                        continue
                    if not isinstance(msg, (dict, list)):
                        self.junk_stdout.append(line[:400])
                        continue
                    self.messages.append(msg)
                    self._inbox.put(msg)
                else:
                    buf += chunk
        except Exception:
            pass
        finally:
            self._inbox.put(_EOF)

    def _drain_stderr(self):
        try:
            for line in self.proc.stderr:
                text = line.decode("utf-8", "replace").rstrip()
                self.stderr_tail.append(text)
                del self.stderr_tail[:-40]
        except Exception:
            pass

    def stop(self):
        if not self.proc:
            return
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # -- sending -----------------------------------------------------------

    def new_id(self):
        i = self._next_id
        self._next_id += 1
        return i

    def send_line(self, text):
        # bypasses json entirely so checks can post garbage
        if self.proc.poll() is not None:
            raise ServerGone("server exited before write (rc=%s)" % self.proc.returncode)
        try:
            self.proc.stdin.write(text.encode("utf-8") + b"\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise ServerGone(str(e))

    def send(self, method, params=None, id=None, jsonrpc="2.0"):
        msg = {"method": method}
        if jsonrpc is not None:
            msg["jsonrpc"] = jsonrpc
        if id is not None:
            msg["id"] = id
        if params is not None:
            msg["params"] = params
        self.send_line(json.dumps(msg))
        return id

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self.send_line(json.dumps(msg))

    # -- receiving ---------------------------------------------------------

    def recv(self, timeout=None):
        deadline = time.time() + (timeout or self.timeout)
        while True:
            left = deadline - time.time()
            if left <= 0:
                raise Timeout("no message in %.1fs" % (timeout or self.timeout))
            try:
                msg = self._inbox.get(timeout=min(left, 0.25))
            except queue.Empty:
                continue
            if msg is _EOF:
                raise ServerGone("stdout closed (rc=%s)" % self.proc.poll())
            return msg

    def await_id(self, want_id, timeout=None):
        """Responses to other ids and any notifications in between are dropped."""
        deadline = time.time() + (timeout or self.timeout)
        while True:
            left = deadline - time.time()
            if left <= 0:
                raise Timeout("no response for id %r" % (want_id,))
            msg = self.recv(timeout=left)
            if isinstance(msg, dict) and "id" in msg and _same_id(msg["id"], want_id):
                return msg
            if isinstance(msg, list):
                return msg

    def drain(self, settle=0.0):
        """Throw away anything queued, optionally waiting first. Checks that read
        with recv() rather than await_id() need this, or a server that answers
        notifications/initialized late shows up as their failure instead of the
        notification check's."""
        if settle:
            try:
                self.quiet_for(settle)
            except ServerGone:
                pass
        while True:
            try:
                self._inbox.get_nowait()
            except queue.Empty:
                return

    def await_response(self, timeout=None):
        """First message that is a response, whatever id it carries. A server
        answering a malformed request often uses a null id, and treating that as
        silence would be a lie."""
        deadline = time.time() + (timeout or self.timeout)
        while True:
            left = deadline - time.time()
            if left <= 0:
                raise Timeout("no response in %.1fs" % (timeout or self.timeout))
            msg = self.recv(timeout=left)
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return msg
            if isinstance(msg, list):
                return msg

    def quiet_for(self, seconds):
        """Collect anything that arrives in a window. Used to prove silence."""
        got = []
        end = time.time() + seconds
        while True:
            left = end - time.time()
            if left <= 0:
                return got
            try:
                msg = self._inbox.get(timeout=min(left, 0.1))
            except queue.Empty:
                continue
            if msg is _EOF:
                raise ServerGone("stdout closed (rc=%s)" % self.proc.poll())
            got.append(msg)

    # -- the normal handshake, for checks that need a live session ---------

    def initialize(self, protocol_version=PROTOCOL_VERSION, timeout=None):
        rid = self.new_id()
        self.send("initialize", {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "mcpcheck", "version": "0.1.0"},
        }, id=rid)
        resp = self.await_id(rid, timeout=timeout)
        self.notify("notifications/initialized")
        return resp

    def call(self, method, params=None, timeout=None):
        rid = self.new_id()
        self.send(method, params, id=rid)
        return self.await_id(rid, timeout=timeout)


class _EOFType:
    pass


_EOF = _EOFType()


def _same_id(a, b):
    # JSON-RPC ids are compared by value and type; 1 and "1" are different ids.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if type(a) is type(b):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return False
