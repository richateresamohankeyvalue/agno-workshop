# Workshop prompts

Paste-ready prompts students use to move from one checkpoint to the next.

## How this works

1. Students start on **`checkpoint-1`** (starter code is given).
2. To reach checkpoint N, they paste **`checkpoint-0N-….md`** into their AI coding tool.
3. They run the acceptance checks at the bottom of that prompt before moving on.

## Facilitator tips

- Give students the **whole file** for a checkpoint (including the shared-constraints block at the top of each prompt). Do not summarize or rewrite the prompt live — that is how drift starts.
- If a student's agent invents files or APIs, tell them to re-paste the same prompt with:  
  `Stop. Re-read HARD RULES. Only change the files listed. Do not invent APIs.`
- Recovery: `git checkout checkpoint-N` (or hand them the reference branch) if a student is stuck more than ~5 minutes.
- Shared infrastructure (not coded by the prompt):
  - MCP: [agent-sdk-bakeoff-mcp-server](https://github.com/richateresamohankeyvalue/agent-sdk-bakeoff-mcp-server) → `docker compose up --build` → `http://localhost:8081/sse`
  - Postgres (from checkpoint-2 on): `docker compose up -d` in this workshop repo → port `5532`

## Prompt map

| After finishing | Paste this prompt | Builds |
|---|---|---|
| checkpoint-1 | `checkpoint-02-memory.md` | Memory (Postgres, user + session) |
| checkpoint-2 | `checkpoint-03-pipeline.md` | Deterministic standup pipeline |
| checkpoint-4 needs 3 first | `checkpoint-04-pause-resume.md` | Human approval pause/resume |
| checkpoint-4 | `checkpoint-05-pipeline-as-tool-review.md` | Pipeline-as-tool + mandatory review |
| checkpoint-5 | `checkpoint-06-eval-cost-portability.md` | Tokens + grader + model swap |
| checkpoint-6 | `checkpoint-07-full-assistant.md` | Full assistant, three request shapes |

There is **no** prompt for checkpoint-1 — that code is the starter kit.
