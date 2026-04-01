// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/// <reference types="react" />

declare module '*.svg' {
  import * as React from 'react';

  const ReactComponent: React.FC<
    React.SVGProps<SVGSVGElement> & {
      title?: string;
      className?: string;
    }
  >;

  export default ReactComponent;
}
