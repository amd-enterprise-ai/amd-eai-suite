// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logout } from '@amdenterpriseai/utils/app';

// Mock next-auth/react
vi.mock('next-auth/react', () => ({
  signOut: vi.fn(),
}));

describe('logout', () => {
  let originalLocation: Location;
  let mockFetch: ReturnType<typeof vi.fn>;
  let mockSignOut: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    // Save original location
    originalLocation = window.location;

    // Mock window.location
    delete (window as any).location;
    window.location = { ...originalLocation } as Location;

    // Mock fetch
    mockFetch = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({ path: '/auth/login' }),
    });
    global.fetch = mockFetch;

    // Mock setTimeout
    vi.useFakeTimers();
  });

  afterEach(() => {
    // Restore original location
    window.location = originalLocation;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should call logout API endpoint', async () => {
    const logoutPromise = logout();

    // Fast-forward timers
    await vi.runAllTimersAsync();
    await logoutPromise;

    expect(mockFetch).toHaveBeenCalledWith('/api/auth/logout', {
      method: 'POST',
    });
  });

  it('should call signOut with redirect false', async () => {
    // Get fresh mock for this test
    const { signOut } = await import('next-auth/react');
    const mockSignOut = vi.mocked(signOut);

    const logoutPromise = logout();

    await vi.runAllTimersAsync();
    await logoutPromise;

    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
  });

  it('should redirect to the path returned by the API', async () => {
    const mockPath = '/custom/redirect';
    mockFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ path: mockPath }),
    });

    const logoutPromise = logout();

    await vi.runAllTimersAsync();
    await logoutPromise;

    expect(window.location as any).toBe(mockPath);
  });

  it('should wait 100ms before redirecting', async () => {
    const logoutPromise = logout();

    // Advance only 50ms
    vi.advanceTimersByTime(50);

    // Location should not be set yet
    expect(typeof window.location).toBe('object');

    // Advance remaining time
    await vi.runAllTimersAsync();
    await logoutPromise;

    expect(window.location as any).toBe('/auth/login');
  });
});
