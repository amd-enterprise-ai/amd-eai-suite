// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { vi } from 'vitest';

import { installElementScrollToPolyfill } from './installElementScrollToPolyfill';

export const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

export function stubAuthEnv(): void {
  vi.stubEnv('NEXTAUTH_SECRET', 'secret');
  vi.stubEnv('KEYCLOAK_ID', 'keycloak_id');
  vi.stubEnv('KEYCLOAK_SECRET', 'keycloak_secret');
  vi.stubEnv('KEYCLOAK_ISSUER', 'keycloak_issuer');
  vi.stubEnv('DEBUG_PRINT_LIMIT', '10');
}

export function shimNodeGlobalAsWindow(): void {
  if (typeof global === 'undefined') {
    window.global = window;
  }
}

export function installResizeObserverMock(): void {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

/** DataTransfer, localStorage, location.reload, scrollIntoView, Element.scrollTo polyfill */
export function installHeavyJsdomMocks(): void {
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

  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });

  Object.defineProperty(window, 'location', {
    value: {
      ...window.location,
      reload: vi.fn(),
    },
    writable: true,
  });

  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    value: vi.fn(),
    writable: true,
  });

  installElementScrollToPolyfill();
}

/** Use in app + shared component/utils setups that run React tree tests with forms, overlays, and tables. */
export function installPackageTestJsdom(): void {
  stubAuthEnv();
  shimNodeGlobalAsWindow();
  installResizeObserverMock();
  installHeavyJsdomMocks();
}

/** Hooks-only: env + globals + ResizeObserver (avoid overriding JSDOM localStorage). */
export function installHooksTestJsdom(): void {
  stubAuthEnv();
  shimNodeGlobalAsWindow();
  installResizeObserverMock();
}

export function resetActiveProjectLocalStorage(): void {
  localStorageMock.getItem.mockImplementation((key: string) => {
    if (key === 'activeProject') {
      return JSON.stringify('project1');
    }
    return null;
  });
}
