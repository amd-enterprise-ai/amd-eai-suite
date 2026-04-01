// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { vi } from 'vitest';

/**
 * Mock clipboard API for testing
 */
export const mockClipboard = {
  writeText: vi.fn(() => Promise.resolve()),
  readText: vi.fn(() => Promise.resolve('')),
};

/**
 * Setup clipboard mock on navigator object
 */
export const setupClipboardMock = () => {
  Object.assign(navigator, {
    clipboard: mockClipboard,
  });
};
