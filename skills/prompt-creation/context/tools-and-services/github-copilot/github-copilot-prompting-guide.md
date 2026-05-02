# GitHub Copilot Prompting Guide

## Overview
Copilot completes what it predicts based on surrounding code, the current file, and the comment/signature directly above the cursor. It does not "understand intent" — it pattern-matches. The prompt is the comment, docstring, or function signature you write immediately before invoking.

## Key principles
- Write the exact function signature, docstring, or comment immediately before invoking — leave no ambiguity.
- Describe input types, return type, edge cases, and what the function must NOT do.
- Type names matter — Copilot uses TypeScript/Python types as strong signals.
- For Copilot Chat (the chat UI), write structured prompts like for Cursor — file scope, current behavior, desired change.

## Template — inline completion (the comment/signature you write)

```python
def parse_invoice_total(raw: str) -> Decimal:
    """
    Parse a localized currency string into a Decimal.

    Handles: "$1,234.56", "1.234,56 €", "USD 1,234", "(1,234.56)" (negative).
    Returns Decimal("0") for empty/None input.
    Must NOT: round, swallow exceptions, or call any network/IO.
    Raises: ValueError for unparseable strings.
    """
```

```ts
// Validate a hex color string. Accepts #RGB, #RRGGBB, #RRGGBBAA. Case-insensitive.
// Returns true for valid, false otherwise. No exceptions, no logging.
function isValidHexColor(input: string): boolean {
```

## Template — Copilot Chat

```
File: [path]
Function: [name]
Current behavior: [what it does now]
Desired change: [what it should do]
Constraints: [language, version, do-not-touch list]
Done when: [binary condition]
```

## Anti-patterns
- Vague comment ("// fix this") → completes random plausible code
- Missing edge cases in docstring → silent wrong behavior on edge inputs
- No "must not" list → adds logging/IO/exceptions you didn't want
- Asking Chat to "improve the file" without scope → over-edits
