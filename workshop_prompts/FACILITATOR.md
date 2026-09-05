# Facilitator notes — using these prompts

## Handout order

Give students **one prompt file at a time** after they finish the previous checkpoint’s live demo / hands-on.

Do not give the whole folder up front — they will skip ahead and the arc collapses.

## If the model drifts (common)

| Symptom | What to tell the student to paste next |
|---|---|
| Invents `enable_user_memories` | “Use `update_memory_on_run=True` and `add_memories_to_context=True` only. Agno 3 does not have `enable_user_memories`.” |
| Builds an MCP server in-repo | “Stop. MCP is external at localhost:8081. Do not add mcp_server/.” |
| Replaces review with a tool | “Review must stay an unconditional `await review_reply(...)` after `agent.arun`.” |
| Adds `--mode sprint` | “No mode flags. One instructions block; agent decides.” |
| Rewrites the whole repo | “Only touch the files listed under Files to change / add.” |
| Uses SQLite instead of Postgres | “Use PostgresDb and docker-compose on port 5532 as specified.” |

## Consistency across IDEs / models

Each prompt is intentionally **self-contained** (rules + goal + file list + done-when).  
Students should paste the **entire file contents below the horizontal rule**, not a paraphrase.

If Cursor / Copilot / Claude Code / Windsurf produce different layouts, the acceptance commands at the bottom are the source of truth — not file-for-file identity with the reference branch.

## Reference recovery

```bash
git fetch origin
git checkout checkpoint-N
```

Use when a student is blocked >5 minutes or their tree is too messy to continue.
