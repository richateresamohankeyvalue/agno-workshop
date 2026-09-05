# Prompt: checkpoint-5 → checkpoint-6 (Evaluation, cost, model portability)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-6** of an Agno workshop project. I already have **checkpoint-5** (`assistant.py` with pipeline-as-tool + mandatory review). Keep that behavior. **Add** token usage printing, **Agno’s built-in evaluation APIs**, and make model swap a one-line env change.

## HARD RULES

1. Workshop code: smallest clear change. No tests harness beyond Agno evals, no mock MCP server, no cost dashboards.
2. Do not remove the checkpoint-5 review step.
3. Do **not** hand-roll a custom “grader Agent + prompt format”. Use Agno evals:
   - Live turn: `from agno.eval.agent_as_judge import AgentAsJudgeEval`
   - Suite: `from agno.eval.suite import Case, JudgeMode, acli`
   Docs: https://docs.agno.com/features/evaluation and https://docs.agno.com/evals/agent-as-judge/overview
4. Memory from checkpoint-2 carries forward: `LearningMachine(db=db, user_memory=True)` as `learning=` on the agent.
5. Judge/grader model must be configurable via `GRADER_MODEL_ID` (different from `AGENT_MODEL_ID`).
6. Token counts come from `response.metrics` (`input_tokens`, `output_tokens`, `total_tokens`).
7. LiteLLM: `litellm.drop_params = True`, `temperature=None`, `top_p=None`.
8. Model portability = change `AGENT_MODEL_ID` in `.env` only.

## Goal

### A) Per-turn eval in `assistant.py`

After every turn print:

1. **Tokens:** `{input} in / {output} out / {total} total`
2. **Review:** (existing checkpoint-5 grounding verdict)
3. **Eval:** result from `AgentAsJudgeEval` (numeric 1–10, threshold 7) — print score / passed / reason

`AgentAsJudgeEval` criteria (one string is fine):
grounded in tools, answers the question, concise.

### B) Offline suite `evals.py`

Two `Case`s minimum, run with `await acli(cases, ...)`:

1. `greeting_quality` — input `"hi"`, `criteria=...`, `judge_mode=JudgeMode.NUMERIC`, `judge_threshold=7`
2. `calendar_uses_tool` — input `"What's on my calendar today?"`,  
   `expected_tool_calls=("get_calendar_events",)`, same judge criteria about not inventing meetings

MCP must be connected before building the agent used in Cases.

## Files to change / add

1. **`src/daily_dev_assistant/config.py`** — `grader_model_id` / `GRADER_MODEL_ID`
2. **`.env.example`** — document `GRADER_MODEL_ID` + model-swap comment on `AGENT_MODEL_ID`
3. **`src/daily_dev_assistant/grader.py`** — `build_judge_eval(settings, db=...)` returning `AgentAsJudgeEval`,  
   plus `grade_reply(...)` that calls `await evaluation.arun(input=..., output=...)`
4. **`evals.py`** — Case suite as above
5. **`src/daily_dev_assistant/agent_pipeline.py`** — `TurnMetrics` on `TurnResult` from `response.metrics`
6. **`assistant.py`** — print Model / Tokens / Review / Eval
7. **`README.md`** — how to run `assistant.py` and `evals.py`

## Do NOT

- Do not invent your own JSON grading schema / second Agent loop for scoring.
- Do not replace the reviewer with the judge; they are different checks (cp5 vs cp6).
- Do not add sprint planning (checkpoint-7).

## Done when

```bash
uv run python assistant.py --user alice
> hi
# Tokens: … / Review: … / Eval: score=…/10 passed=…

uv run python evals.py
# Cases run; process exit code reflects pass/fail

# change only AGENT_MODEL_ID in .env, re-run assistant — same script
```

After editing, list changed files and the commands above.
