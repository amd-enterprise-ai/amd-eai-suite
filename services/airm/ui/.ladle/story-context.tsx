// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';

// Context to track if we're inside a Story component
// This is used to prevent markdown elements from rendering inside Story
export const StoryContext = React.createContext<boolean>(false);
