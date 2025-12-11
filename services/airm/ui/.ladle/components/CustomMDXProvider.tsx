// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { StoryContext } from '../story-context';

// Helper to add ladle-markdown class to className
const addMarkdownClass = (
  className?: string,
  defaultClass = 'ladle-markdown',
): string => {
  if (!className) return defaultClass;
  if (className.includes(defaultClass)) return className;
  return `${defaultClass} ${className}`.trim();
};

// Helper component wrapper that checks StoryContext
// When inside a Story, markdown elements render just their children (no wrapper)
const createMarkdownComponent = <T extends HTMLElement>(Tag: string) => {
  return React.forwardRef<T, React.HTMLAttributes<T>>((props, ref) => {
    // Check if we're inside a Story component via context
    const isInsideStory = React.useContext(StoryContext);

    // If inside Story, render children without the markdown wrapper element
    // This effectively "unwraps" MDX's markdown parsing
    if (isInsideStory) {
      return <>{props.children}</>;
    }

    // Outside Story, render with markdown styling
    return React.createElement(
      Tag as keyof React.JSX.IntrinsicElements,
      {
        ...props,
        className: addMarkdownClass(props.className),
        ref,
      } as any,
    );
  });
};

// MDX components configuration - prevents markdown elements from rendering inside Story
export const mdxComponents = {
  p: createMarkdownComponent<HTMLParagraphElement>('p'),
  h1: createMarkdownComponent<HTMLHeadingElement>('h1'),
  h2: createMarkdownComponent<HTMLHeadingElement>('h2'),
  h3: createMarkdownComponent<HTMLHeadingElement>('h3'),
  h4: createMarkdownComponent<HTMLHeadingElement>('h4'),
  h5: createMarkdownComponent<HTMLHeadingElement>('h5'),
  h6: createMarkdownComponent<HTMLHeadingElement>('h6'),
  ul: createMarkdownComponent<HTMLUListElement>('ul'),
  ol: createMarkdownComponent<HTMLOListElement>('ol'),
  li: createMarkdownComponent<HTMLLIElement>('li'),
  a: createMarkdownComponent<HTMLAnchorElement>('a'),
  strong: createMarkdownComponent<HTMLElement>('strong'),
  em: createMarkdownComponent<HTMLElement>('em'),
  del: createMarkdownComponent<HTMLElement>('del'),
  u: createMarkdownComponent<HTMLElement>('u'),
  pre: createMarkdownComponent<HTMLPreElement>('pre'),
  table: createMarkdownComponent<HTMLTableElement>('table'),
  thead: createMarkdownComponent<HTMLTableSectionElement>('thead'),
  tbody: createMarkdownComponent<HTMLTableSectionElement>('tbody'),
  tr: createMarkdownComponent<HTMLTableRowElement>('tr'),
  th: createMarkdownComponent<HTMLTableCellElement>('th'),
  td: createMarkdownComponent<HTMLTableCellElement>('td'),
  blockquote: createMarkdownComponent<HTMLQuoteElement>('blockquote'),
  hr: createMarkdownComponent<HTMLHRElement>('hr'),
  input: createMarkdownComponent<HTMLInputElement>('input'),
};
