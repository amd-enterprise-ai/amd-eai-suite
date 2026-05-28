// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

import { installHooksTestJsdom } from '../../utils/__tests__/vitestJsdomSetup';

installHooksTestJsdom();

afterEach(() => {
  cleanup();
});
