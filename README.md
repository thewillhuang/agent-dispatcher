Agent Dispatcher
===============

Autonomous pull-based dispatcher that picks up Ready tickets from the Kanban board and implements them.

Overview
--------

This dispatcher runs as a scheduled job (cron every 5 minutes) and:

1. Queries the Kanban board for Ready tickets
2. Checks WIP limits (max 3 In Progress)
3. Runs deduplication checks (existing PRs, feature branches, recent claims)
4. Claims the highest priority Ready ticket
5. Creates a PR and automerges it

Board Configuration
-------------------

- Project: Agent Work (thewillhuang/agentneo)
- Project V2 ID: PVT_kwHOAHgLT84BUsgT (use `projectsV2(first: 1)`, NOT `projectsV2(number: 3)`)
- Status field ID: PVTSSF_lAHOAHgLT84BUsgTzhCINu8
- Priority field ID: PVTSSF_lAHOAHgLT84BUsgTzhCIOZg

Status Options:
- Backlog: f75ad846
- Ready: 61e4505c
- In progress: 47fc9ee4
- In review: df73e18b
- Done: 98236657

Priority Options:
- P0: 79628723
- P1: 0a877460
- P2: da944a9c

Installation
------------

1. Copy `agent-dispatcher.py` to your desired location
2. Ensure `gh` CLI is installed and authenticated
3. Set up credentials:
   ```bash
   export GITHUB_TOKEN="your_personal_access_token"
   ```
4. Add to crontab (runs every 5 minutes):
   ```
   */5 * * * * /usr/bin/python3 /path/to/agent-dispatcher.py >> /var/log/agent-dispatcher.log 2>&1
   ```

Or use the provided systemd service:
```bash
sudo cp systemd-service.service /etc/systemd/system/agent-dispatcher.service
sudo systemctl daemon-reload
sudo systemctl enable --now agent-dispatcher
```

Deduplication Checks
--------------------

Before claiming a ticket, the dispatcher runs three checks:

1. **Existing PR check**: Looks for open PRs with "Closes #N" or "Fixes #N" in the body
2. **Feature branch check**: Ensures no existing branch for the issue
3. **Recent claim check**: Verifies no recent "claiming" comment exists

If any check matches, the issue is skipped.

Workflow
--------

1. Dispatcher wakes up (every 5 minutes or via event trigger)
2. Checks if WIP limit (3 In Progress) is reached
3. Queries board for Ready items
4. Sorts by priority (P0 > P1 > P2)
5. Runs dedup checks on highest priority Ready ticket
6. Claims the ticket (sets Status to "In progress")
7. Creates PR with automated merge enabled
8. PR is auto-merged when ready (squash + delete branch)

Migration Warning
----------------

Do NOT replace this cron with an event-driven system until the replacement has been verified working end-to-end. When migrating, keep the old cron running alongside the new system, confirm the new system is actually picking up work, THEN retire the old cron. Killing the cron before the replacement works resulted in 10+ minutes of complete system idle.

Critical GraphQL Query Pattern
------------------------------

Use the safe query pattern to avoid null pointer issues with archived/removed items:

```bash
gh api graphql -f 'query=
  query {
    repository(owner: "thewillhuang", name: "agentneo") {
      projectsV2(first: 1) {
        nodes {
          items(first: 100) {
            nodes {
              id
              content {
                __typename
                ... on Issue { number title state }
                ... on PullRequest { number title state merged }
              }
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2SingleSelectField { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
'
```

Always check `totalCount` before iterating:

```bash
TOTAL=$(echo "$DATA" | jq '.data.repository.projectV2.items.totalCount')
if [ "$TOTAL" = "0" ] || [ "$TOTAL" = "null" ]; then
    echo "No items on board"
fi
```

Dependencies
------------

- GitHub CLI (`gh`)
- Python 3.6+
- Standard library only (no external dependencies required)

Logging
-------

All output is sent to syslog via cron, or can be redirected to a file:

```
*/5 * * * * /usr/bin/python3 /path/to/agent-dispatcher.py >> /var/log/agent-dispatcher.log 2>&1
```

Error Handling
--------------

- Failed GraphQL queries are logged to stderr
- Failed claims are logged but don't stop the dispatcher
- Empty board state results in [IDLE] output