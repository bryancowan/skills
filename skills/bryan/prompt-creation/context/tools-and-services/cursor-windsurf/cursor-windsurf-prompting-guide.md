# Cursor / Windsurf Prompting Guide

## Overview
Cursor and Windsurf are AI-first IDEs that edit code inside an open codebase. The most common failure modes are editing the wrong file and breaking existing logic. Prompts must include explicit file scope, do-not-touch lists, and a binary stop condition.

## Key principles
- Never give a global instruction without a file anchor. Always name the exact file path and function/component.
- Include the language and version explicitly (e.g., "TypeScript 5.4 strict, React 18").
- "Done when:" is required — defines when the agent stops editing.
- For complex tasks, split into sequential prompts rather than one large prompt.

## Template

```
File: [exact/path/to/file.ext]
Function/Component: [exact name]

Current Behavior:
[what this code does right now — be specific]

Desired Change:
[what it should do after the edit — be specific]

Scope:
Only modify [function/component/section].
Do NOT touch: [list everything to leave unchanged]

Constraints:
- Language/framework: [version]
- Do not add dependencies not already in [package.json / requirements.txt]
- Preserve existing [type signatures / API contracts / variable names]

Done When:
[exact binary condition that confirms the change worked]
```

## Anti-patterns
- "Update the login function" with no file path → ambiguous, agent guesses
- "Make it better" → no binary stop condition, agent over-edits
- Pasting the whole codebase as context → scope to the relevant file only
- Asking for two unrelated changes in one prompt → split into Prompt 1 and Prompt 2

## Example
```
File: src/pages/Login.tsx
Function: handleLogin

Current Behavior:
Submits the form and navigates to /dashboard on success. No error handling for 401 responses.

Desired Change:
On 401, set local state `loginError` to "Invalid credentials" and stay on the page. Other status codes keep current behavior.

Scope:
Only modify handleLogin. Do NOT touch: form markup, validation logic, route config, useAuth hook.

Constraints:
- TypeScript 5.4 strict, React 18, no new dependencies.
- Preserve the existing Promise return type.

Done When:
A 401 response sets loginError and the user remains on /login. All other status codes behave as before.
```
