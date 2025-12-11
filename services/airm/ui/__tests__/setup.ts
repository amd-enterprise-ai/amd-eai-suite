// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';

vi.stubEnv('NEXTAUTH_SECRET', 'secret');
vi.stubEnv('KEYCLOAK_ID', 'keycloak_id');
vi.stubEnv('KEYCLOAK_SECRET', 'keycloak_secret');
vi.stubEnv('KEYCLOAK_ISSUER', 'keycloak_issuer');
vi.stubEnv('DEBUG_PRINT_LIMIT', '10');

if (typeof global === 'undefined') {
  window.global = window;
}

// Mock ResizeObserver
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock DataTransfer and related APIs for file upload testing
(global as any).DataTransfer = class MockDataTransfer {
  files: FileList;
  items: DataTransferItemList;
  types: string[];

  constructor() {
    this.files = [] as any;
    this.items = {
      length: 0,
      add: vi.fn(),
      remove: vi.fn(),
      clear: vi.fn(),
      [Symbol.iterator]: function* () {},
    } as any;
    this.types = [];
  }
};

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock location.reload to prevent actual reloads in tests
Object.defineProperty(window, 'location', {
  value: {
    ...window.location,
    reload: vi.fn(),
  },
  writable: true,
});

// Mock scrollIntoView
Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
  value: vi.fn(),
  writable: true,
});

// Global mock for the project context - this ensures all components that use useProject work
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'project1',
    projects: [{ id: 'project1', name: 'Project 1' }],
    isLoading: false,
    setActiveProject: vi.fn(),
  }),
  ProjectProvider: ({ children }: { children: React.ReactNode }) => children,
}));

beforeEach(() => {
  vi.clearAllMocks();
  // Set up default localStorage mock behavior
  localStorageMock.getItem.mockImplementation((key: string) => {
    if (key === 'activeProject') {
      return JSON.stringify('project1');
    }
    return null;
  });
});

afterEach(() => {
  cleanup();
});
