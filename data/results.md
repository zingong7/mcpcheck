| server | unknown-method | no-method | no-version | parse-error | parse-error-survives | invalid-params | params-described | unknown-tool | deep-nesting | no-batch-crash |
|---|---|---|---|---|---|---|---|---|---|---|
| mcp-server-git | **fail** | **fail** | **fail** | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** |
| mcp-server-time | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | ok | **fail** | ok |
| mcp-server-fetch | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | ok | **fail** | ok |
| mcp-server-sqlite | **fail** | **fail** | **fail** | **fail** | ok | **fail** | ok | **fail** | **fail** | ok |
| mcp-server-calculator | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| duckduckgo-mcp-server | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| mcp-simple-arxiv | **fail** | **fail** | **fail** | **fail** | ok | **fail** | **fail** | ok | **fail** | ok |
| mcp-server-docker | did not start |  |  |  |  |  |  |  |  |  |

19 further checks passed on every server and are left out.

- **mcp-server-git** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-server-git** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-git** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-git** / `parse-error` (spec) - no parse error came back
- **mcp-server-git** / `parse-error-survives` (robust) - session unusable afterwards: stdout closed (rc=None)
- **mcp-server-git** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-server-git** / `params-described` (robust) - 22 of 28 undescribed: git_status.repo_path, git_diff_unstaged.repo_path, git_diff_unstaged.context_lines, git_diff_staged.repo_path, git_diff_staged.context_lines
- **mcp-server-git** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-server-git** / `no-batch-crash` (robust) - session dead after a batch: stdout closed (rc=None)
- **mcp-server-time** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-server-time** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-time** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-time** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **mcp-server-time** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-server-time** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-server-fetch** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-server-fetch** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-fetch** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-fetch** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **mcp-server-fetch** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-server-fetch** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-server-sqlite** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-server-sqlite** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-sqlite** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-sqlite** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **mcp-server-sqlite** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-server-sqlite** / `unknown-tool` (spec) - reported success for a tool that does not exist
- **mcp-server-sqlite** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-server-calculator** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-server-calculator** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-calculator** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-server-calculator** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **mcp-server-calculator** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-server-calculator** / `params-described` (robust) - 1 of 1 undescribed: calculate.expression
- **mcp-server-calculator** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **duckduckgo-mcp-server** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **duckduckgo-mcp-server** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **duckduckgo-mcp-server** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **duckduckgo-mcp-server** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **duckduckgo-mcp-server** / `invalid-params` (spec) - no response to a request whose params were a string
- **duckduckgo-mcp-server** / `params-described` (robust) - 7 of 7 undescribed: search.query, search.max_results, search.region, fetch_content.url, fetch_content.start_index
- **duckduckgo-mcp-server** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-simple-arxiv** / `unknown-method` (spec) - expected code -32601, got -32602 (Invalid request parameters)
- **mcp-simple-arxiv** / `no-method` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-simple-arxiv** / `no-version` (spec) - dropped silently - no response of any kind, so a client just waits
- **mcp-simple-arxiv** / `parse-error` (spec) - logged the parse error as a notification instead of answering it
- **mcp-simple-arxiv** / `invalid-params` (spec) - no response to a request whose params were a string
- **mcp-simple-arxiv** / `params-described` (robust) - 9 of 9 undescribed: search_papers.query, search_papers.max_results, search_papers.sort_by, search_papers.sort_order, search_papers.date_from
- **mcp-simple-arxiv** / `deep-nesting` (robust) - no response to 400 levels of nesting
- **mcp-server-docker** - did not start: exited during initialize:         f'Error while fetching server API version: {e}' |     ) from e | docker.errors.DockerException: Error while fetching server API version: (2, 'CreateFile', 'The system cannot find the file spec
