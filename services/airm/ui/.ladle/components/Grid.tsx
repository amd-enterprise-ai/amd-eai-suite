// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';

// Grid component - creates a CSS grid with specified number of columns
export const Grid: React.FC<{
  children: React.ReactNode;
  col: number;
}> = ({ children, col }) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${col}, 1fr)`,
        justifyItems: 'center',
        alignItems: 'center',
        gap: '1rem',
      }}
    >
      {children}
    </div>
  );
};
