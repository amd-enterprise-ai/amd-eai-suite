// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Code, type CodeProps } from '@heroui/react';
import React from 'react';

export interface CodeBlockProps extends Omit<CodeProps, 'as' | 'children'> {
  children: React.ReactNode;
  className?: string;
  as?: 'code' | 'pre';
}

// Thin replacement for HeroUI's `Code`, which v3 removes. Wraps the v2 `Code`
// today so visuals stay identical; the stable `as` prop lets callers render the
// same styling as either a `code` or `pre` element once v3 lands.
export const CodeBlock = ({
  children,
  className,
  as = 'code',
  ...rest
}: CodeBlockProps): React.JSX.Element => (
  <Code as={as} className={className} {...rest}>
    {children}
  </Code>
);

CodeBlock.displayName = 'CodeBlock';
