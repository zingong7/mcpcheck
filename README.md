# mcpcheck

Points a deliberately badly behaved JSON-RPC client at an MCP server and reports
where the server stops following the spec.

Writing an MCP server is easy, because the SDK does the protocol for you. That
is also the problem: almost nobody tests what their server does when a client
sends something wrong, and the answers turn out to be worse than you would
guess. Of the seven servers below, none passed everything, and most of what
they failed is one bug in the SDK they all sit on.

```
mcpcheck                          server under test
   |                                     |
   |  a fresh process per check          |
   |------------------------------------>|
   |  initialize, then one bad message   |
   |  (no method / no jsonrpc / broken   |
   |   json / string params / 256KB /    |
   |   400 levels of nesting / a NUL)    |
   |                                     |
   |<------------------------------------|
   |  a response, an error, a log line,  |
   |  silence, or a dead process         |
```

Nothing here is built on the MCP SDK. Half the checks send messages an SDK
client would refuse to construct, so the client is a few hundred lines of raw
stdio JSON-RPC. It has no dependencies at all, which also means it cannot be
blamed for the failures it reports.

## Results

Run on 2026-08-30, against every MCP server I could install from PyPI. Servers
are rows, checks are columns.

| server | unknown-method | no-method | no-version | parse-error | parse-error-survives | invalid-params | params-described | unknown-tool | deep-nesting | no-batch-crash |
|---|---|---|---|---|---|---|---|---|---|---|
| mcp-server-git | **fail** | **fail** | **fail** | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** |
| mcp-server-time | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | ok | **fail** | ok |
| mcp-server-fetch | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | ok | **fail** | ok |
| mcp-server-sqlite | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | **fail** | **fail** | ok |
| mcp-server-calculator | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| duckduckgo-mcp-server | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| mcp-simple-arxiv | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| mcp-server-docker | did not start (no docker daemon on this machine) |

19 further checks passed everywhere and are left out of the table. The full
output is in `data/results.json`.

**These are not seven independent results.** Every server above is Python and
every one of them is running `mcp` 1.29.1, so the six columns that are red for
all of them are one finding about the SDK, counted seven times. Read the table
as one SDK-level finding plus three server-specific ones.

### The SDK finding: a malformed request gets no answer at all

The Python SDK validates each incoming message against a pydantic union of the
request types it knows. When a message fails that validation it logs the problem
and moves on, without ever sending a response carrying the request's id.

Confirmed by hand, outside mcpcheck, against `mcp-server-time`:

```
--- request with no method member
    stdout: {"method":"notifications/message","params":{"level":"error",
             "logger":"mcp.server.exception_handler","data":"Internal Server Error"}}
    stderr: Field required [type=missing, input_value={'jsonrpc': '2.0', 'id': 5}]
```

There is a `notifications/message` log, and nothing else. JSON-RPC says that
should have been a `-32600`. The practical consequence is worse than the wrong
code: a client that sends a slightly wrong request waits forever, because
nothing will ever arrive with the id it is waiting on. The same thing happens
for a missing `jsonrpc` member, for `params` that is a string, and for broken
JSON.

A request with a valid shape but an unknown method does get an error, but a
`-32602 Invalid request parameters` rather than `-32601 Method not found` -
pydantic could not match the method name to a request type, so the failure
surfaces as a params problem.

`deep-nesting` has the same root cause. The cutoff is between 150 and 200 levels,
which is pydantic's JSON parser depth limit; past it the message is dropped
silently like any other validation failure.

### mcp-server-sqlite: a missing tool reports success

```json
{"jsonrpc":"2.0","id":30,"result":{
  "content":[{"type":"text","text":"Error: Missing arguments"}],
  "isError":false}}
```

The tool does not exist. The text says "Error". `isError` says `false`. A model
reading the structured field, which is the field that exists for exactly this
purpose, is told the call worked.

### mcp-server-git: one bad line wedges the session

Same SDK version as `mcp-server-time` and `mcp-server-fetch`, both of which
shrug off a malformed line and carry on. `mcp-server-git` stays alive but stops
answering:

```
mcp-server-time    alive=True  answered tools/list after garbage=True
mcp-server-fetch   alive=True  answered tools/list after garbage=True
mcp-server-git     alive=True  answered tools/list after garbage=False
```

A process that is up but deaf is the annoying kind of broken - the client's
health check passes and every call times out.

### Undocumented arguments

Not a spec violation, so it is scored separately, but `params-described` failed
on four servers: 22 of 28 arguments in `mcp-server-git`, and every argument in
`duckduckgo-mcp-server`, `mcp-simple-arxiv` and `mcp-server-calculator`. The
schema is the only thing a model has to go on when filling a call in.

## Running it

No dependencies. Built and run on Python 3.14.

```bash
python -m mcpcheck run -- python -m mcp_server_time
```

Against a list of servers, with a report:

```bash
python -m mcpcheck run --json data/results.json --markdown data/results.md
```

`servers.json` holds the list. `"command": "python"` means whichever interpreter
is running mcpcheck, so the file works from any venv without hardcoded paths.

```bash
python -m mcpcheck run --server mcp-server-git --only parse-error,id-echo
python -m mcpcheck checks     # what gets tested, and the rule behind each
```

Exit status is 1 if any `spec` check failed, so it works in CI.

## The checks

29 of them, in two classes:

- **spec** - a MUST in JSON-RPC 2.0 or in the MCP spec. Error codes, id echoing,
  never answering a notification, nothing but MCP messages on stdout, tools
  declaring a name and an object schema, a capability the server advertises
  actually working.
- **robust** - not required anywhere, but servers that get it wrong cause real
  trouble: surviving a malformed line, a 256KB argument, control characters and
  astral unicode in a string, a stray cancellation, exiting when stdin closes,
  enforcing a required argument, describing what a tool does.

A third status, `warn`, is for a server that answers correctly but with the
wrong error code. Getting `-32603` where the spec says `-32600` is a real
deviation, but it is not the same kind of problem as never answering, and
scoring them identically would flatten the only distinction that matters.

Every check runs in its own process. That makes a full run slow - one spawn per
check per server - but several checks are about what state the server is in
after being mistreated, and a shared session would let one check's damage show
up as the next check's failure.

mcpcheck never calls a tool with arguments that could let it succeed. The
payload checks all target a tool name that does not exist, and the validation
checks deliberately send arguments that should be rejected. Pointing it at a
server with real side effects should be safe, but read `checks/tools.py` before
you point it at anything that spends money.

## Tests

```bash
python -m pytest tests -q
```

28 tests, no network. They run the whole battery against two fixture servers in
`tests/servers/`: one deliberately correct, one with a known list of faults -
banner on stdout, echoed protocol version, ids coerced to integers, answers
notifications, reports success for tools that do not exist. Each fault is
pinned to the check that should catch it, so a check that quietly stops working
fails the suite rather than silently reporting a clean bill of health.

## Scope

- **Python servers.** Node was not installed on the machine this ran on, so the
  npx half of the ecosystem is untested - and that is where many of the well
  known servers live. The SDK finding above is a finding about one SDK.
- **stdio transport.** HTTP and SSE are not covered, so nothing here touches
  sessions, resumability or origin validation.
- **Tools in depth, resources and prompts lightly.** `resources/*` and
  `prompts/*` are checked as far as "you advertised it, does it answer".
  Subscriptions, pagination and completions are left for later.
- **Timeouts are wall clock**, ten seconds by default and settable with
  `--timeout`. A server with a slow cold start wants a larger budget.
