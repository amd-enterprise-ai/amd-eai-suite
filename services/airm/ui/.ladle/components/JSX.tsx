// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { StoryContext } from '../story-context';

// JSX component - prevents markdown rendering for its children
export const JSX: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <StoryContext.Provider value={true}>{children}</StoryContext.Provider>;
};
