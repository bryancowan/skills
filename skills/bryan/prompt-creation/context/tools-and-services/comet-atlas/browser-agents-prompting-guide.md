# Browser Agents (Comet, Atlas, Claude in Chrome, OpenClaw Agents) Prompting Guide

## Overview
These agents drive a real browser. They click, scroll, fill forms, and complete transactions autonomously. They are not search tools — they take real actions on real pages. Permission boundaries and stop conditions for irreversible actions are critical.

## Key principles
- Describe the outcome, not the navigation steps. The agent decomposes navigation internally.
- Specify constraints explicitly — without them the agent makes its own choices.
- Add explicit permission boundaries: "Research only. Do not make any purchase."
- Add stop conditions for any irreversible action (forms, transactions, messages).
- Comet/Computer is strongest at research, comparison, data extraction.
- Atlas is stronger at multi-step commerce and account management.

## Template

```
Goal:
[single outcome — e.g., "Find the cheapest one-stop flight from NYC to Lisbon on Emirates or KLM next month, no Boeing 737 Max"]

Constraints:
- [explicit rules: airline whitelist, max stops, date range, etc.]
- Currency: [USD/EUR/...]
- Cabin: [Economy/Business]

Output:
[exact structure: e.g., "A markdown table with: Airline, Flight #, Date, Price, Layover. Cite each source URL."]

Permission Boundaries:
- Research only. Do NOT make any purchase, booking, or reservation.
- Do NOT submit any form.
- Do NOT log into any account.

Stop Conditions:
Ask for human approval before:
- Submitting any form
- Completing any transaction
- Sending any message
- Entering any payment information

Verification:
For each result, include the source URL so I can confirm.
```

## Anti-patterns
- Step-by-step navigation → defeats the purpose; agent works better with outcome framing
- No permission boundary → agent attempts to "complete the task" by purchasing
- No source URLs → unverifiable hallucinated results
- Asking the agent to "decide for me" on irreversible actions → set stop conditions instead
