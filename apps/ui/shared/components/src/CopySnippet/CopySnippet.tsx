// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Snippet, type SnippetProps } from '@heroui/react';
import React from 'react';

export interface CopySnippetProps extends Omit<SnippetProps, 'children'> {
  children?: React.ReactNode;
  value?: string;
}

// HeroUI v3 removes `Snippet`; this thin adapter preserves the copy-to-clipboard
// affordance on top of the v2 implementation until a native v3 replacement lands.
// `symbol` defaults to "" so consumers get a plain copyable value (no `$` prefix).
export const CopySnippet = ({
  children,
  value,
  symbol = '',
  ...rest
}: CopySnippetProps): React.JSX.Element => (
  <Snippet symbol={symbol} {...rest}>
    {children ?? value}
  </Snippet>
);
