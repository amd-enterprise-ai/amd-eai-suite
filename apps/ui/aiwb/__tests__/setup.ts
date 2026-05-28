// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';

import {
  installPackageTestJsdom,
  resetActiveProjectLocalStorage,
} from '@/../shared/utils/__tests__/vitestJsdomSetup';

installPackageTestJsdom();

configure({ asyncUtilTimeout: 15_000 });

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    isStandaloneMode: false,
    airmAppUrl: undefined,
    activeProject: 'project1',
    projects: [{ id: 'project1', name: 'Project 1' }],
    isLoading: false,
    setActiveProject: vi.fn(),
    projectPath: (path: string) =>
      `/project1${path.startsWith('/') ? path : `/${path}`}`,
    projectUrl: (path: string) =>
      `/project1${path.startsWith('/') ? path : `/${path}`}`,
  }),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => children,
}));

beforeEach(() => {
  resetActiveProjectLocalStorage();
});

afterEach(() => {
  cleanup();
});

vi.mock('next/router', () => ({
  useRouter: () => ({
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
  }),
}));
