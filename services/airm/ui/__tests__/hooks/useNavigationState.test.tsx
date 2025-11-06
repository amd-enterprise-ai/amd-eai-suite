// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook, act } from '@testing-library/react';
import { vi } from 'vitest';

// Mock Next.js router
const mockPush = vi.fn();
const mockRouter = {
  pathname: '/',
  push: mockPush,
  query: {},
  asPath: '/',
  route: '/',
  basePath: '',
  isLocaleDomain: true,
  isReady: true,
  isPreview: false,
  back: vi.fn(),
  beforePopState: vi.fn(),
  prefetch: vi.fn(),
  reload: vi.fn(),
  replace: vi.fn(),
  events: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
  },
  isFallback: false,
  locale: undefined,
  locales: undefined,
  defaultLocale: undefined,
};

vi.mock('next/router', () => ({
  useRouter: () => mockRouter,
}));

// Mock the menu items
vi.mock('@/utils/app/navigation', () => ({
  airmMenuItems: [
    { href: '/', name: 'Dashboard' },
    { href: '/projects', name: 'Projects' },
    { href: '/clusters', name: 'Clusters' },
    { href: '/users', name: 'Users' },
  ],
  aiWorkbenchMenuItems: [
    { href: '/chat', name: 'Chat' },
    { href: '/datasets', name: 'Datasets' },
    { href: '/workspaces', name: 'Workspaces' },
  ],
}));

// Import after mocking
import { useNavigationState } from '@/hooks/useNavigationState';

describe('useNavigationState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset router pathname to default
    mockRouter.pathname = '/';
  });

  describe('Section Detection', () => {
    it('detects resource management section for home page', () => {
      mockRouter.pathname = '/';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('detects resource management section for projects page', () => {
      mockRouter.pathname = '/projects';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('detects resource management section for clusters page', () => {
      mockRouter.pathname = '/clusters';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('detects AI Workbench section for chat page', () => {
      mockRouter.pathname = '/chat';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['ai-workbench']);
    });

    it('detects AI Workbench section for datasets page', () => {
      mockRouter.pathname = '/datasets';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['ai-workbench']);
    });

    it('detects resource management section for users page', () => {
      mockRouter.pathname = '/users';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('returns empty array for unknown pages', () => {
      mockRouter.pathname = '/unknown-page';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual([]);
    });
  });

  describe('Toggle Section Control', () => {
    it('correctly handles toggling sections from a clean state', () => {
      mockRouter.pathname = '/'; // currentSection is 'resource-management'
      const { result } = renderHook(() => useNavigationState());

      // First, toggle the non-active section. Both should be open.
      act(() => {
        result.current.toggleSection('ai-workbench');
      });
      expect(result.current.expandedSections).toEqual([
        'resource-management',
        'ai-workbench',
      ]);

      // Next, toggle the active section to close it.
      act(() => {
        result.current.toggleSection('resource-management');
      });
      expect(result.current.expandedSections).toEqual(['ai-workbench']);

      // Toggle the remaining section to close it.
      act(() => {
        result.current.toggleSection('ai-workbench');
      });
      expect(result.current.expandedSections).toEqual([]);

      // Toggle a section to open it again.
      act(() => {
        result.current.toggleSection('resource-management');
      });
      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('maintains manual setting even when router changes', () => {
      mockRouter.pathname = '/'; // currentSection is 'resource-management'
      const { result, rerender } = renderHook(() => useNavigationState());

      // Manually close the active section
      act(() => {
        result.current.toggleSection('resource-management');
      });
      expect(result.current.expandedSections).toEqual([]);

      // Change router pathname, which changes currentSection
      mockRouter.pathname = '/chat'; // currentSection is now 'ai-workbench'
      rerender();

      // Should maintain manual setting (empty), not reset to the new currentSection
      expect(result.current.expandedSections).toEqual([]);
    });
  });

  describe('Nested Routes', () => {
    it('detects section for nested resource management routes', () => {
      mockRouter.pathname = '/projects/project-123';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('detects section for nested AI Workbench routes', () => {
      mockRouter.pathname = '/chat/conversation-456';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['ai-workbench']);
    });

    it('detects section for nested resource management routes (users)', () => {
      mockRouter.pathname = '/users/user-789';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });

    it('detects section for nested workspaces routes', () => {
      mockRouter.pathname = '/workspaces/workspace-123';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['ai-workbench']);
    });
  });

  describe('Function Stability', () => {
    it('returns stable toggleSection function reference', () => {
      const { result, rerender } = renderHook(() => useNavigationState());

      const firstToggleFunction = result.current.toggleSection;
      rerender();
      const secondToggleFunction = result.current.toggleSection;

      expect(firstToggleFunction).toBe(secondToggleFunction);
    });
  });

  describe('Edge Cases', () => {
    it('handles rapid section changes correctly', () => {
      mockRouter.pathname = '/'; // currentSection is 'resource-management'
      const { result } = renderHook(() => useNavigationState());

      act(() => {
        result.current.toggleSection('ai-workbench'); // state: ['resource-management', 'ai-workbench']
      });
      act(() => {
        result.current.toggleSection('resource-management'); // state: ['ai-workbench']
      });
      act(() => {
        result.current.toggleSection('ai-workbench'); // state: []
      });

      expect(result.current.expandedSections).toEqual([]);
    });

    it('handles empty pathname gracefully', () => {
      mockRouter.pathname = '';
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual([]);
    });

    it('handles pathname with query parameters', () => {
      mockRouter.pathname = '/projects';
      mockRouter.query = { id: 'test' };
      const { result } = renderHook(() => useNavigationState());

      expect(result.current.expandedSections).toEqual(['resource-management']);
    });
  });
});
