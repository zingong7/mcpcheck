import os

import pytest

from mcpcheck.client import RawClient, Timeout, _same_id
from mcpcheck.core import FAIL, PASS, Check, Result
from mcpcheck.report import markdown
from mcpcheck.runner import Server, ServerRun

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD = os.path.join(HERE, "servers", "goodserver.py")


def client():
    return RawClient("python", [GOOD])


def test_ids_compare_by_type():
    assert _same_id(1, 1)
    assert _same_id("a", "a")
    assert not _same_id(1, "1")
    assert not _same_id(True, 1)


def test_handshake_and_call():
    with client() as c:
        result = c.initialize()["result"]
        assert result["serverInfo"]["name"] == "goodserver"
        tools = c.call("tools/list")["result"]["tools"]
        assert [t["name"] for t in tools] == ["echo", "add"]


def test_await_id_skips_other_traffic():
    with client() as c:
        c.initialize()
        first = c.new_id()
        second = c.new_id()
        c.send("tools/list", {}, id=first)
        c.send("tools/list", {}, id=second)
        # asking for the second one discards the first
        assert c.await_id(second)["id"] == second


def test_await_response_ignores_notifications():
    with client() as c:
        c.initialize()
        c.drain(0.3)
        c.send_line("{ broken")
        assert c.await_response(timeout=5)["error"]["code"] == -32700


def test_timeout_is_raised_not_hung():
    with client() as c:
        c.initialize()
        c.drain(0.3)
        with pytest.raises(Timeout):
            c.recv(timeout=0.5)


def test_junk_on_stdout_is_collected():
    with RawClient("python", ["-c", "import sys; print('hello'); sys.stdout.flush(); sys.stdin.read()"]) as c:
        with pytest.raises(Exception):
            c.initialize(timeout=2)
        assert c.junk_stdout == ["hello"]


def test_markdown_marks_failures():
    chk = Check(None, "some-check", "t", "spec", "ref")
    run = ServerRun(Server("srv", "python"))
    run.results = [Result(chk, FAIL, "broke")]
    table = markdown([run])
    assert "some-check" in table
    assert "**fail**" in table

    run.results = [Result(chk, PASS, "fine")]
    assert "**fail**" not in markdown([run])
