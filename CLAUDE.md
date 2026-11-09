# LandStack: land records on a map
Read docs/PROJECT_BRIEF.md and docs/HANDOFF.md at the start of every session.

## Rules
- Work on one phase at a time. Never start the next phase on your own.
- Plan first: say what you will do and which files you will touch. Then build.
- After building, explain every new concept in simple words, as if I am 10.
- Never run git commit. I commit once at the end of each phase.
- Spatial SQL stays visible in backend/app/checks.py. No ORM.
- Measure area with a geography cast (square metres). Skip or repair invalid shapes before the overlap and zone checks.
- Seed data is deterministic (fixed seed) and always writes planted_truth.json.
- The risk score is computed by code. Models and LLMs never change it.
- Every conflict check has a pytest test that compares against planted_truth.json.
- Never commit .env or API keys. Model names and keys live in .env.

## Reports
End every task with a report in the format in docs/REPORT_FORMAT.md. The last line of every report must be: Usage check: if you have used more than 60% of your limit, type HANDOFF.

## HANDOFF
When I type HANDOFF, or say my usage is above 60%:
1. Update docs/HANDOFF.md so it is true right now, in plain words.
2. Update docs/PROJECT_BRIEF.md if anything big changed.
3. Do not commit.
4. Print one ready-to-paste prompt for the next tool (Antigravity unless I name another). It must tell that tool to: read both docs files; start with a 5-line plain summary of where we are; do the next task (name it and the files); not run git commit; and end with a report in the REPORT_FORMAT.md format.
5. Tell me in one line which tool is best for that next task.
