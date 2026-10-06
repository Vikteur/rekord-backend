---
name: fetch-jira-ticket
description: "Fetch a Jira ticket (PROJ-1234 or URL) via the Atlassian MCP: summary, description, acceptance criteria, epic, subtasks, links, comments. Use at ticket start or before dispatching an orchestrator."
argument-hint: "<ticket key or Jira URL> [--comments]"
---

# Fetch Jira Ticket

Retrieves a Jira issue through the Atlassian MCP server and returns a normalized brief that orchestrators and analysts can consume directly.

## Input

`$ARGUMENTS` — a ticket key (`PROJ-1422`, case-insensitive) or a Jira URL (`https://<site>.atlassian.net/browse/PROJ-1422`, or any URL with `selectedIssue=PROJ-1422`). Extract the key with `[A-Za-z][A-Za-z0-9]+-\d+` and uppercase it. No key → ask for one.

## Tool discovery

The MCP server name varies per install, so match tools by suffix, not full name. If they are deferred, load them in one `ToolSearch` call (query `jira issue`).

| Purpose | Atlassian remote MCP / claude.ai connector | `mcp-atlassian` (sooperset) |
|---|---|---|
| Resolve cloud id | `*getAccessibleAtlassianResources` | not needed |
| Get issue | `*getJiraIssue` | `*jira_get_issue` |
| Search (subtasks / epic children) | `*searchJiraIssuesUsingJql` | `*jira_search` |
| Remote links (PRs, Confluence) | `*getJiraIssueRemoteIssueLinks` | `*jira_get_issue` (included) |

No Jira tool available, or the server is listed as failed to connect → stop and tell the user. Do not fall back to web fetching or guessing ticket content.

## Steps

1. **Cloud id** (Atlassian remote MCP only): call `getAccessibleAtlassianResources` once and pick the site whose URL matches the input URL; otherwise the only/first site. Reuse it for every call below.
2. **Issue**: fetch the issue with all fields (`expand=renderedFields,names` where supported). Include comments when `--comments` is passed or the description is thin (< ~5 lines).
3. **Epic**: read the parent (`fields.parent`, or the "Epic Link" custom field found via `names`). Record its key and summary.
4. **Subtasks / children**: use `fields.subtasks`; if the ticket is an Epic, run JQL `parent = <KEY> ORDER BY rank` for its children.
5. **Links**: collect `fields.issuelinks` (type + direction + key + summary + status) and remote links (GitHub PRs, Confluence, Figma).
6. **Acceptance criteria**: take a dedicated AC custom field if `names` exposes one; otherwise extract the section of the description headed "Acceptance criteria" / "AC" / "Given/When/Then". If none exists, say so — never invent criteria.

Convert ADF/wiki markup to plain Markdown. Keep the description verbatim apart from formatting; do not summarize it away.

## Output

```markdown
# <KEY> — <summary>

| Field | Value |
|---|---|
| Type / Status / Priority | <type> / <status> / <priority> |
| Epic | <EPIC-KEY> — <epic summary> |
| Assignee / Reporter | <assignee> / <reporter> |
| Sprint / Fix version / Labels | … |
| URL | <browse URL> |

## Description
<verbatim, as Markdown>

## Acceptance criteria
- …  (or: "None specified in the ticket.")

## Subtasks
- <KEY> [<status>] <summary>

## Linked issues
- <link type> <KEY> [<status>] <summary>

## Remote links
- <title> — <url>

## Comments  (only when fetched; newest last, author + date)
```

Omit empty sections except Acceptance criteria.

## Integration

The output is shaped for the orchestrator handoff: pass `<KEY>`, the epic key, and the Description + Acceptance criteria sections as the ticket description to `orchestrator`. Subagents cannot see this conversation's MCP tools reliably, so fetch here and hand them the text.

Read-only skill: never transition, edit, assign, or comment on the issue.
