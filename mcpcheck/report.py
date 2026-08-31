"""Terminal output and the markdown table that goes in a README."""

import sys

from mcpcheck.core import ERROR, FAIL, PASS, ROBUST, SKIP, SPEC, WARN

MARK = {PASS: "pass", WARN: "warn", FAIL: "FAIL", SKIP: "skip", ERROR: "err "}


def _out(line=""):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def line_for(result):
    return "  %-5s %-22s %s" % (MARK[result.status], result.check.id, result.detail)


def server_header(server):
    _out()
    _out(server.name)
    _out("-" * max(len(server.name), 40))


def server_summary(run):
    if not run.reachable:
        _out("  could not start: %s" % run.problem)
        return
    counts = run.counts()
    spec_fails = len(run.failures(SPEC))
    robust_fails = len(run.failures(ROBUST))
    _out("  %d passed, %d warned, %d failed (%d spec, %d robustness), %d skipped"
         % (counts[PASS], counts[WARN], counts[FAIL], spec_fails, robust_fails, counts[SKIP]))


def overall(runs):
    _out()
    _out("=" * 60)
    reachable = [r for r in runs if r.reachable]
    _out("%d of %d servers reachable" % (len(reachable), len(runs)))
    if not reachable:
        return
    clean = [r for r in reachable if not r.failures()]
    _out("%d passed everything" % len(clean))
    for r in reachable:
        c = r.counts()
        _out("  %-24s %2d pass  %2d warn  %2d fail  %2d skip"
             % (r.server.name, c[PASS], c[WARN], c[FAIL], c[SKIP]))


def markdown(runs):
    """Rows are servers, columns are checks. Only the checks that went wrong
    somewhere get a column - a table of 29 green cells says nothing."""
    reachable = [r for r in runs if r.reachable]
    if not reachable:
        return "no servers were reachable\n"

    all_ids = [res.check.id for res in reachable[0].results]
    interesting = [i for i in all_ids
                   if any(r.status != PASS for run in reachable for r in run.results
                          if r.check.id == i)]
    quiet = len(all_ids) - len(interesting)

    lines = ["| server | " + " | ".join(interesting) + " |",
             "|---" * (len(interesting) + 1) + "|"]
    for run in reachable:
        by_id = {r.check.id: r.status for r in run.results}
        cells = [{PASS: "ok", WARN: "warn", FAIL: "**fail**", SKIP: "-",
                  ERROR: "err"}.get(by_id.get(i), "?") for i in interesting]
        lines.append("| %s | %s |" % (run.server.name, " | ".join(cells)))
    for run in runs:
        if not run.reachable:
            lines.append("| %s | %s |" % (run.server.name,
                                          " | ".join(["did not start"] + [""] * (len(interesting) - 1))))
    lines.append("")
    lines.append("%d further checks passed on every server and are left out." % quiet)
    return "\n".join(lines) + "\n"


def failure_notes(runs):
    lines = []
    for run in runs:
        if not run.reachable:
            lines.append("- **%s** - did not start: %s" % (run.server.name, run.problem))
            continue
        for res in run.failures():
            lines.append("- **%s** / `%s` (%s) - %s"
                         % (run.server.name, res.check.id, res.check.severity, res.detail))
    return "\n".join(lines) + "\n" if lines else "nothing failed\n"
