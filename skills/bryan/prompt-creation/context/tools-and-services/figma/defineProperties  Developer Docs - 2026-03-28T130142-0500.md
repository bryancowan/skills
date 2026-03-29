---
title: "defineProperties | Developer Docs"
source: "https://developers.figma.com/docs/code/define-properties/"
author:
published:
created: 2026-03-28
description: "defineProperties allows your component to define customizable properties that control its behavior and appearance. These properties appear in the Figma properties panel and right sidebar of the Figma Sites interface. The editable properties enable users of your component to modify it without editing code."
tags:
  - "clippings"
status: "Unread"
note:
related:
---
`defineProperties` allows your component to define customizable properties that control its behavior and appearance. These properties appear in the Figma properties panel and right sidebar of the Figma Sites interface. The editable properties enable users of your component to modify it without editing code.

With `defineProperties`, you can define one or more properties for a component. Each property has a type. There are four types: `string`, `number`, `boolean`, and `reference`.

```jsx
// Example usage of defineProperties with all property types
defineProperties(MyComponent, {
  text: { type: 'string', defaultValue: 'Hello' },
  count: { type: 'number', defaultValue: 1 },
  enabled: { type: 'boolean', defaultValue: true },
  icon: { type: 'reference' },
});
```

## string

`string` properties let you provide editable fields for entering text. You can set the following options when using the `string` type:

| Property | Values | Type | Description |
| --- | --- | --- | --- |
| label | any string | string | Custom label for the property in the UI |
| defaultValue | any string | string | The default value shown in the field |
| control | none (default), select | string | Type of control: text input or dropdown |
| options | list of `{value, label}` | array of objs | Dropdown options (if control is 'select') |

### default string prop

A simple text field with a label and default value.

```jsx
defineProperties(MyComponent, {
  text: {
    type: 'string',
    label: 'Display Text',
    defaultValue: 'Hello, World!',
  },
  placeholder: {
    type: 'string',
    label: 'Input Placeholder',
    defaultValue: 'Enter your name...',
  },
});
```

### options string prop

Use a dropdown for string properties by setting `control: 'select'` and providing `options`.

Options should be an array of objects: `{ value: string, label: string }`.

```jsx
defineProperties(MyComponent, {
  buttonType: {
    type: 'string',
    defaultValue: 'normal',
    control: 'select',
    options: [
      { value: 'normal', label: 'Normal' },
      { value: 'warning', label: 'Warning / Caution' },
      { value: 'secondary', label: 'Secondary' },
    ],
  },
});
```

## number

`number` properties let users input numeric values. Useful for dimensions, quantities, or any numeric configuration.

| Property | Values | Type | Description |
| --- | --- | --- | --- |
| label | any string | string | Custom label for the property in the UI |
| defaultValue | any number | number | The default value shown in the field |
| control | none (default), slider, select | string | Type of control: input, slider, or dropdown |
| min | any number | number | Minimum value (for slider) |
| max | any number | number | Maximum value (for slider) |
| step | any number | number | Step size (for slider) |
| options | list of `{value, label}` | array of objs | Dropdown options (if control is 'select') |
| description | any string | string | Optional description for the property |

### default number prop

A simple numeric input.

```jsx
defineProperties(MyComponent, {
  opacity: {
    type: 'number',
    defaultValue: 1,
    label: 'Opacity',
  },
  borderWidth: {
    type: 'number',
    defaultValue: 2,
    label: 'Border Width',
    description: 'Sets the width of the border in pixels',
  },
});
```

### slider number prop

Use a slider for number properties by setting `control: 'slider'` and providing `min`, `max`, and `step`.

```jsx
defineProperties(MyComponent, {
  opacity: {
    type: 'number',
    label: 'Opacity',
    defaultValue: 0.8,
    control: 'slider',
    min: 0,
    max: 1,
    step: 0.1,
  },
  padding: {
    type: 'number',
    label: 'Padding',
    defaultValue: 16,
    control: 'slider',
    min: 0,
    max: 32,
    step: 4,
  },
});
```

### options number prop

Use a dropdown for number properties by setting `control: 'select'` and providing `options`.

```jsx
defineProperties(MyComponent, {
  buttonType: {
    type: 'number',
    defaultValue: 1,
    control: 'select',
    options: [
      { value: 1, label: 'Regular' },
      { value: 2, label: 'Secondary' },
      { value: 3, label: 'Tertiary' },
    ],
  },
});
```

## boolean

`boolean` properties let users toggle functionality or visual elements on or off.

| Property | Values | Type | Description |
| --- | --- | --- | --- |
| label | any string | string | Custom label for the property in the UI |
| defaultValue | true, false | boolean | The default value |

```jsx
defineProperties(MyComponent, {
  hasBorder: {
    type: 'boolean',
    defaultValue: false,
    label: 'Enable Border',
  },
  isFullWidth: {
    type: 'boolean',
    defaultValue: true,
    label: 'Full Width',
  },
  showIcon: {
    type: 'boolean',
    defaultValue: true,
    label: 'Show Icon',
  },
});
```

## reference

`reference` properties allow your component to incorporate instances of other components from the current file or attached libraries.

In the Figma Sites interface, in the properties that appear in the code editor or at the top of the right sidebar, you can select a component from your libraries to apply as the value of a `reference` property.

| Property | Values | Type | Description |
| --- | --- | --- | --- |
| label | any string | string | Custom label for the property in the UI |
| defaultValue | React component | component | Default React component to use when no reference is selected |

The name of a key for `defineProperties` must correspond to a React component in your code. The following examples uses `Icon`, `Avatar`, and `ActionButton` as keys, but these are only examples. The exact names will depend on the code in your code layer or component.

```jsx
defineProperties(MyComponent, {
  Icon: {
    type: 'reference',
    label: 'Icon',
    defaultValue: ListIcon,
  },
  Avatar: {
    type: 'reference',
    label: 'User Avatar',
    defaultValue: DefaultAvatar,
  },
  ActionButton: {
    type: 'reference',
    label: 'Action Button',
  },
});
```

The code to implement the previous examples of the reference property might look like this, where `ListIcon` is a component imported from `lucide-react` and `DefaultAvatar` is a React component in your code layer:

```jsx
import { defineProperties } from "figma:react";
import { List as ListIcon } from "lucide-react";

function DefaultAvatar() {
  return (
    <div className="w-8 h-8 bg-gray-300 rounded-full">
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full p-1">
        <circle cx="12" cy="8" r="3"/>
        <path d="M12 14c-4 0-6 2-6 4v2h12v-2c0-2-2-4-6-4z"/>
      </svg>
    </div>
  );
}

export default function MyComponent({ Icon, Avatar, ActionButton }) {
  return (
    <div>
      {Icon && <Icon />}
      {Avatar && <Avatar />}
      {ActionButton && <ActionButton />}
    </div>
  );
}

defineProperties(MyComponent, {
  Icon: {
    type: 'reference',
    label: 'Icon',
    defaultValue: ListIcon,
  },
  Avatar: {
    type: 'reference',
    label: 'User Avatar',
    defaultValue: DefaultAvatar,
  },
  ActionButton: {
    type: 'reference',
    label: 'Action Button',
  },
});
```

## setter

You can make a property updatable from inside your component by adding a `setter` to its definition. The `setter` should be a string matching the name of a function prop that updates the property’s value. When the property is changed in the site, such as when the text of an input changes or a button is clicked, this function will be called with the new value. If the property is bound to a [variable](https://help.figma.com/hc/en-us/articles/15339657135383-Guide-to-variables-in-Figma), the variable will also be updated.

This enables two-way data flow between your component and the Figma UI, allowing code layers and component instances to share and update data.

The `setter` is typically used with React state setters (in the examples, `setText`, `setSize`, `setMode`). The function receives the new value as its argument.

### Text setter example

```jsx
import { useState } from "react";
import { defineProperties } from "figma:react";

export default function ExampleTextLayer({ text, setText }) {
  const handleTextChange = (event) => {
    setText(event.target.value);
  };

  return (
    <div>
      <div>
        <label htmlFor="text-input" className="block">
          Text:
        </label>
        <input
          id="text-input"
          type="text"
          value={text}
          onChange={handleTextChange}
          className="p-1 border rounded"
        />
      </div>
    </div>
  );
}

defineProperties(ExampleTextLayer, {
  text: {
    type: "string",
    defaultValue: "Hello, world!",
    setter: "setText",
  },
});
```

### Number setter example

```jsx
import { defineProperties } from "figma:react";
import { useState } from "react";

export default function ExampleNumberLayer({
  size,
  setSize,
}) {
  const handleSizeChange = (event) => {
    setSize(parseFloat(event.target.value));
  };

  return (
    <div>
      <div>
        <label htmlFor="size-input" className="block">
          Size:
        </label>
        <input
          id="size-input"
          type="number"
          value={size}
          onChange={handleSizeChange}
          className="p-1 border rounded"
        />
      </div>
    </div>
  );
}

defineProperties(ExampleNumberLayer, {
  size: {
    type: "number",
    defaultValue: 10,
    setter: "setSize",
  },
});
```

### Boolean setter example

```jsx
import { defineProperties } from "figma:react";

export default function ExampleBooleanLayer({ mode, setMode }) {
  const toggleValue = () => setMode(!mode);     // true = dark, false = light

  return (
    <div className="flex flex-col items-center space-y-4">
      <button
        type="button"
        onClick={toggleValue}
        className="w-16 h-16 bg-transparent border-2 border-black text-black rounded-full flex items-center justify-center text-sm text-center hover:shadow-inner transition-shadow"
      >
        {mode ? 'Dark' : 'Light'}
      </button>
    </div>
  );
}

defineProperties(ExampleBooleanLayer, {
  mode: {
    type: "boolean",
    defaultValue: false,
    setter: "setMode",
  },
});
```
