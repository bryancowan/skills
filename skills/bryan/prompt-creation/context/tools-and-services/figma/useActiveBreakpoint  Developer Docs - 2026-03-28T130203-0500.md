---
title: "useActiveBreakpoint | Developer Docs"
source: "https://developers.figma.com/docs/code/use-active-breakpoint/"
author:
published:
created: 2026-03-28
description: "useActiveBreakpoint helps you build components that work well in responsive sets by providing information about the current breakpoint."
tags:
  - "clippings"
status: "Unread"
note:
related:
---
`useActiveBreakpoint` helps you build components that work well in responsive sets by providing information about the current breakpoint.

With `useActiveBreakpoint`, you can access the name and size of the active breakpoint in your component. This enables responsive layouts and conditional rendering based on available space.

## Reference

### useActiveBreakpoint()

Call `useActiveBreakpoint()` to get the current breakpoint's name, width, and height.

```jsx
import {
  useActiveBreakpoint,
} from "figma:react";

export default function Component({ text }) {
  const { name, width, height } = useActiveBreakpoint();

  // Different layouts based on breakpoint width
  if (width < 480) {
    return (
      <span className="text-xs">
        {name} ({width}px × {height}px)
      </span>
    );
  } else if (width < 800) {
    return (
      <span className="text-m">
        {name} ({width}px × {height}px)
      </span>
    );
  } else {
    return (
      <span className="text-l">
        {name} ({width}px × {height}px)
      </span>
    );
  }
}
```

#### Returns

`useActiveBreakpoint` returns an object with these properties:

| Property | Type | Description |
| --- | --- | --- |
| name | string | The name of the active breakpoint. Default names are `Desktop`, `Tablet`, and `Mobile`, but users can provide custom names. Don't assume specific names exist. |
| width | number | The width of the active breakpoint's page, in pixels. |
| height | number | The height of the active breakpoint's page, in pixels. |

## Example use cases

- **Responsive styling:** Style your component differently based on the current breakpoint.
- **Conditional rendering:** Dynamically show or hide components based on the available space.
