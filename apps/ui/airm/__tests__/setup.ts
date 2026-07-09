// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';

import {
  installPackageTestJsdom,
  resetActiveProjectLocalStorage,
} from '@/../shared/utils/__tests__/vitestJsdomSetup';
import { withMockAmdenterpriseaiButtonStubs } from '@/../shared/utils/__tests__/mockAmdenterpriseaiButtonStubs';

installPackageTestJsdom();

// HeroUI v3 (React Aria) triggers async state updates that must be flushed
// inside act(). This flag tells React that the test environment supports act()
// so those updates are batched correctly instead of causing waitFor timeouts.
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('@amdenterpriseai/components', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/components')>();
  return withMockAmdenterpriseaiButtonStubs(actual);
});

configure({ asyncUtilTimeout: 15_000 });

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'project1',
    projects: [{ id: 'project1', name: 'Project 1' }],
    isLoading: false,
    setActiveProject: vi.fn(),
  }),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => children,
}));

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
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockRouter = {
  locale: 'en',
  pathname: '/',
  query: {},
  asPath: '/',
  push: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn(),
  back: vi.fn(),
  prefetch: vi.fn(),
  beforePopState: vi.fn(),
  events: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
  isFallback: false,
  isLocaleDomain: false,
  isReady: true,
};
vi.mock('next/router', () => ({
  useRouter: () => mockRouter,
  default: mockRouter,
}));

beforeEach(() => {
  resetActiveProjectLocalStorage();
});

afterEach(() => {
  cleanup();
});
