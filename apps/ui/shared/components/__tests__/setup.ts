// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import React from 'react';

import {
  installPackageTestJsdom,
  resetActiveProjectLocalStorage,
} from '@/../utils/__tests__/vitestJsdomSetup';

installPackageTestJsdom();

const defaultSession = {
  data: {
    user: {
      email: 'test@example.com',
      id: 'test-user-id',
      roles: [] as string[],
    },
  },
  status: 'authenticated' as const,
  update: vi.fn(),
};

vi.mock('next-auth/react', () => ({
  useSession: vi.fn(() => defaultSession),
  SessionProvider: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

beforeEach(() => {
  resetActiveProjectLocalStorage();
});

afterEach(() => {
  cleanup();
});
