import argparse
import json
import sys

from mcpcheck import report
from mcpcheck.core import SPEC, load_all
from mcpcheck.runner import Server, run_server


def load_servers(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Server.from_dict(d) for d in raw["servers"]]


def cmd_run(args):
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if command:
        servers = [Server("ad-hoc", command[0], command[1:])]
    else:
        servers = load_servers(args.servers)
        if args.server:
            wanted = set(args.server)
            servers = [s for s in servers if s.name in wanted]
            missing = wanted - {s.name for s in servers}
            if missing:
                sys.exit("not in %s: %s" % (args.servers, ", ".join(sorted(missing))))

    only = set(args.only.split(",")) if args.only else None
    if only:
        known = {c.id for c in load_all()}
        unknown = only - known
        if unknown:
            sys.exit("no such check: %s" % ", ".join(sorted(unknown)))

    runs = []
    for server in servers:
        report.server_header(server)
        run = run_server(server, only=only, timeout=args.timeout,
                         on_result=lambda r: print(report.line_for(r)))
        report.server_summary(run)
        runs.append(run)

    report.overall(runs)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"runs": [r.as_dict() for r in runs]}, fh, indent=2)
        print("\nwrote %s" % args.json)
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(report.markdown(runs))
            fh.write("\n")
            fh.write(report.failure_notes(runs))
        print("wrote %s" % args.markdown)

    spec_failures = sum(len(r.failures(SPEC)) for r in runs)
    return 1 if spec_failures else 0


def cmd_checks(args):
    for chk in load_all():
        print("%-22s %-8s %s" % (chk.id, chk.severity, chk.title))
        print("%-22s %s" % ("", chk.ref))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mcpcheck",
                                     description="conformance checks for MCP stdio servers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run the battery")
    run.add_argument("--servers", default="servers.json")
    run.add_argument("--server", action="append", help="only this server, repeatable")
    run.add_argument("--only", help="comma separated check ids")
    run.add_argument("--timeout", type=float, default=10.0)
    run.add_argument("--json", help="write the full results here")
    run.add_argument("--markdown", help="write a results table here")
    run.add_argument("command", nargs=argparse.REMAINDER,
                     help="after --, a server command to test instead of the servers file")
    run.set_defaults(fn=cmd_run)

    checks = sub.add_parser("checks", help="list what gets tested")
    checks.set_defaults(fn=cmd_checks)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
