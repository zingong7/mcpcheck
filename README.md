# mcpcheck

Sends deliberately broken messages to an MCP server and reports what it does
with them.

MCP servers are easy to write because the SDK handles the protocol for you. So
most of them only ever get tested with correct input. This sends the incorrect
kind - a missing field, truncated JSON, arguments of the wrong type - and checks
that the server answers instead of ignoring you.

Of the seven servers I tested, none passed everything.

## Results

Run on 2026-08-30 against the MCP servers I could install from PyPI.

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

5 other checks passed everywhere and are left out. Full output in
`data/results.json`.

All seven are Python servers on `mcp` 1.29.1, so the columns that are red
everywhere are one problem in the SDK rather than seven separate ones.

### Malformed requests get no reply

JSON-RPC says every request with an id gets an answer, even if the answer is an
error. These servers write the problem to their own log and send nothing:

```
sent      {"jsonrpc":"2.0","id":5}                     <- no "method" field
received  {"method":"notifications/message","params":{"level":"error",
           "data":"Internal Server Error"}}
```

That is a log line, not a response. The client is still waiting on id 5 and
nothing is ever coming, so it hangs. Same for a missing `jsonrpc` member,
`params` sent as a string, and broken JSON.

Unknown methods do get an error, but `-32602 Invalid request parameters` instead
of `-32601 Method not found`.

`deep-nesting` is the same problem - past about 150 levels the message fails
validation and gets dropped like the others.

### mcp-server-sqlite says a missing tool worked

```json
{"jsonrpc":"2.0","id":30,"result":{
  "content":[{"type":"text","text":"Error: Missing arguments"}],
  "isError":false}}
```

The tool does not exist and the text says "Error", but `isError` is `false`.
That field is the one a model actually reads.

### mcp-server-git stops answering after one bad line

Same SDK version as time and fetch, which both recover:

```
mcp-server-time    alive=True  answered tools/list after garbage=True
mcp-server-fetch   alive=True  answered tools/list after garbage=True
mcp-server-git     alive=True  answered tools/list after garbage=False
```

The process is still up, so a health check passes while every call times out.

### Undocumented arguments

`params-described` failed on four servers - 22 of 28 arguments in
`mcp-server-git`, and every argument in the other three. The schema is all a
model has to go on when filling in a call.

## Running it

No dependencies. Built and run on Python 3.14.

```bash
python -m mcpcheck run -- python -m mcp_server_time
```

Against the list in `servers.json`:

```bash
python -m mcpcheck run --json data/results.json --markdown data/results.md
```

`"command": "python"` means whichever interpreter is running mcpcheck, so the
file works from any venv.

```bash
python -m mcpcheck run --server mcp-server-git --only parse-error,id-echo
python -m mcpcheck checks
```

Exit status is 1 if a `spec` check failed, so it can run in CI.

## The checks

15 of them, tagged either `spec` (a MUST in JSON-RPC 2.0 or the MCP spec) or
`robust` (not required, but painful when wrong - surviving a malformed line,
handling a deeply nested payload, saying what a tool's arguments mean). A `warn`
result means the server answered but with the wrong error code, which is not as
bad as not answering at all.

The client is plain stdio JSON-RPC rather than the MCP SDK, because half the
checks send messages the SDK would not let you build. That also means mcpcheck
has no dependencies of its own.

Each check runs in a fresh process, since several of them test what state the
server is in after being mistreated.

No check ever calls a real tool. The only tool name mcpcheck sends is one no
server has, so pointing it at something with side effects is safe.

## Tests

```bash
python -m pytest tests -q
```

23 tests, no network. They run the battery against two servers in
`tests/servers/`: one written correctly, and one with a list of faults on
purpose - banner on stdout, echoed protocol version, ids coerced to integers,
answers notifications, reports success for tools that do not exist. Each fault
is tied to the check that should catch it.

## Scope

- **Python servers.** Node was not installed on the machine this ran on, so the
  npx half of the ecosystem is untested.
- **stdio transport.** HTTP and SSE are not covered.
- **Tools in depth, resources and prompts lightly.** Those two are checked as
  far as "you advertised it, does it answer".
- **Timeouts are wall clock**, ten seconds by default, settable with
  `--timeout`.
