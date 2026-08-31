import os
import sys

import pytest

from mcpcheck.core import FAIL, PASS, SKIP, WARN
from mcpcheck.runner import Server, run_server

HERE = os.path.dirname(os.path.abspath(__file__))


def fixture(name):
    return Server(name, "python", [os.path.join(HERE, "servers", name + ".py")])


@pytest.fixture(scope="module")
def good():
    return {r.check.id: r for r in run_server(fixture("goodserver")).results}


@pytest.fixture(scope="module")
def bad():
    return {r.check.id: r for r in run_server(fixture("badserver")).results}


def test_good_server_is_clean(good):
    broken = {i: r.detail for i, r in good.items() if r.status not in (PASS, SKIP)}
    assert not broken


def test_every_check_ran(good):
    from mcpcheck.core import load_all
    assert set(good) == {c.id for c in load_all()}


# each of these is a fault badserver has on purpose; if a check stops firing
# here it has stopped working
@pytest.mark.parametrize("check_id", [
    "init-version",
    "unknown-method",
    "no-version",
    "parse-error",
    "id-echo",
    "notification-silence",
    "invalid-params",
    "tools-unique",
    "tools-described",
    "params-described",
    "unknown-tool",
    "missing-required-arg",
    "wrong-arg-type",
    "stdout-clean",
    "cancel-unknown",
])
def test_bad_server_is_caught(bad, check_id):
    assert bad[check_id].status == FAIL, bad[check_id].detail


def test_bad_server_still_passes_what_it_gets_right(bad):
    # it is a bad server, not a dead one - the checks should not all light up
    assert bad["init-shape"].status == PASS
    assert bad["tools-shape"].status == PASS
    assert bad["clean-exit"].status == PASS


def test_wrong_error_code_is_a_warning_not_a_failure(bad):
    # badserver answers everything it does not understand with -32603
    assert bad["no-method"].status == WARN
    assert "-32600" in bad["no-method"].detail


def test_unreachable_server_is_reported_not_raised():
    run = run_server(Server("nope", "definitely-not-a-real-binary-xyz"))
    assert not run.reachable
    assert "command not found" in run.problem
    assert run.results == []


def test_python_means_this_interpreter():
    assert Server("x", "python").command == sys.executable
