---
title: "How to write great prompts | Developer Docs"
source: "https://developers.figma.com/docs/code/how-to-write-great-prompts/"
author:
published:
created: 2026-03-28
description: "When you're using the chat interface in Figma Sites to generate code layers, you're actually interacting with a focused version of Figma Make. The same general best practices apply to both Figma Make and Figma Sites. There are some differences, though, such as code layer support for properties in Figma Sites. This page covers the general approach as well as specific information for Figma Make and Figma Sites."
tags:
  - "clippings"
status: "Unread"
note:
related:
---
When you're using the chat interface in Figma Sites to generate code layers, you're actually interacting with a focused version of Figma Make. The same general best practices apply to both Figma Make and Figma Sites. There are some differences, though, such as code layer support for properties in Figma Sites. This page covers the general approach as well as specific information for Figma Make and Figma Sites.

## General best practices

Here are several best practices that are helpful to follow when working with our AI chat in Figma Make and Figma Sites:

**Be clear and direct.** When you’re writing instructions in the AI chat, it’s best to be specific about the end result that you’re looking for. When you’re specific about what you want, there are fewer opportunities to make assumptions and makes it less likely that the model will try to proactively add features you don’t intend.

**Use examples.** When you create prompts, you should provide examples of what you want the end result to be. Images can be used to help the model get closer to what you want, but there are some limitations. The model isn’t capable of processing exact colors out of an image, for example.

**Don’t provide sensitive information.** You shouldn’t provide things like API keys, email and street addresses, personal data, ID numbers, and similarly sensitive data in the AI chat itself. Instead, if you want to generate code that does something like make API requests for you, prompt the model to include a UI element that lets you input that data.

## Best practices for prompting in Figma Make

For more information about writing prompts for Figma Make, see the [Create and edit functional prototypes and web apps article](https://help.figma.com/hc/articles/31304485164695) in our Help Center.

## Best practices for prompting in Figma Sites

When prompting in Figma Sites, there are some scenarios where you should include more technical descriptions of functionality that you want.

**Components and layers with modifiable content.** Say you want to create an animated text component that you can reuse throughout your site, but you don't want the text content hardcoded into your component. Instead, you want to be able to specify different text for the component instance by instance. In this scenario, you should prompt the model to *define properties*. The model is able to generate code that includes the `defineProperties` function. Properties let you provide different values on an instance-by-instance basis. You can ask the model to define a number of different properties, including text, numbers, boolean values, and more.

For more information, see [defineProperties](https://developers.figma.com/docs/code/define-properties/).

**Responsive design and conditional rendering.** You may want components that will automatically resize based on a page's breakpoints, or only be rendered if there's enough viewport space available. In this scenario, you should prompt the model to include the `useActiveBreakpoint` function. The model can use the values that will be returned by `useActiveBreakpoint` to define different layout and functionality for the component based on the width and height of the active breakpoint.

For more information, see [useActiveBreakpoint](https://developers.figma.com/docs/code/use-active-breakpoint/).
