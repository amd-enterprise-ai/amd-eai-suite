// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { ReactNode } from 'react';

import {
  installPackageTestJsdom,
  resetActiveProjectLocalStorage,
} from './vitestJsdomSetup';

installPackageTestJsdom();

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: {
      user: {
        email: 'test@example.com',
        id: 'test-user-id',
        roles: ['Platform Administrator'],
      },
    },
    status: 'authenticated',
    update: vi.fn(),
  }),
  SessionProvider: ({ children }: { children: ReactNode }) => children,
}));

beforeEach(() => {
  resetActiveProjectLocalStorage();
});

afterEach(() => {
  cleanup();
});
