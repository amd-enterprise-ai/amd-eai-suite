// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';

vi.unmock('@/contexts/ProjectContext');

const mockRouter = {
  query: {} as Record<string, string | undefined>,
  pathname: '/',
  locale: 'en',
  defaultLocale: 'en',
  push: vi.fn(),
};

vi.mock('next/router', () => ({
  useRouter: () => mockRouter,
}));

vi.mock('@/lib/app/app-config', () => ({
  getAppConfig: vi.fn(() =>
    Promise.resolve({
      isStandaloneMode: false,
      defaultNamespace: null,
    }),
  ),
  AppConfig: {},
}));

vi.mock('@/lib/app/projects', () => ({
  fetchProjects: vi.fn(() =>
    Promise.resolve({
      data: [
        { id: 'my-project', name: 'My Project' },
        { id: 'other-project', name: 'Other Project' },
      ],
    }),
  ),
}));

vi.mock('@amdenterpriseai/hooks', () => ({
  useLocalStorage: () => [null, vi.fn()],
}));

import { ProjectProvider, useProject } from '@/contexts/ProjectContext';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ProjectProvider>{children}</ProjectProvider>
    </QueryClientProvider>
  );
};

const waitForProjectsLoaded = async (result: {
  current: ReturnType<typeof useProject>;
}) => {
  await waitFor(() => {
    expect(result.current.projects.length).toBeGreaterThan(0);
  });
};

describe('ProjectContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRouter.query = {};
    mockRouter.pathname = '/';
    mockRouter.locale = 'en';
    mockRouter.defaultLocale = 'en';
    mockRouter.push = vi.fn();
  });

  describe('projectPath (for router.push)', () => {
    it('returns unmodified path when project is absent', async () => {
      mockRouter.query = {};

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      expect(result.current.activeProject).toBeNull();
      expect(result.current.projectPath('/models')).toBe('/models');
    });

    it('prefixes path with project when present', async () => {
      mockRouter.query = { project: 'my-project' };

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      expect(result.current.activeProject).toBe('my-project');
      expect(result.current.projectPath('/models')).toBe('/my-project/models');
    });

    it('never includes locale prefix (locale is handled by Next.js router)', async () => {
      mockRouter.query = { project: 'my-project' };
      mockRouter.locale = 'de';
      mockRouter.defaultLocale = 'en';

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      expect(result.current.projectPath('/models')).toBe('/my-project/models');
    });

    it('normalizes paths without leading slash', async () => {
      mockRouter.query = { project: 'my-project' };

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      expect(result.current.projectPath('models')).toBe('/my-project/models');
    });
  });

  describe('projectUrl (for window.open and direct links)', () => {
    describe('project handling', () => {
      it('returns unmodified path when project is absent', async () => {
        mockRouter.query = {};

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBeNull();
        expect(result.current.projectUrl('/models')).toBe('/models');
      });

      it('prefixes path with project when present', async () => {
        mockRouter.query = { project: 'my-project' };

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/models')).toBe('/my-project/models');
      });

      it('handles project with nested paths', async () => {
        mockRouter.query = { project: 'my-project' };

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/aims/123/details')).toBe(
          '/my-project/aims/123/details',
        );
      });
    });

    describe('path normalization', () => {
      it('normalizes paths without leading slash', async () => {
        mockRouter.query = { project: 'my-project' };

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('models')).toBe('/my-project/models');
      });

      it('normalizes paths without leading slash when no project', async () => {
        mockRouter.query = {};

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.projectUrl('models')).toBe('/models');
      });

      it('handles paths with query parameters', async () => {
        mockRouter.query = { project: 'my-project' };

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/chat?workload=abc')).toBe(
          '/my-project/chat?workload=abc',
        );
      });
    });

    describe('locale handling', () => {
      it('omits locale prefix for default locale', async () => {
        mockRouter.query = { project: 'my-project' };
        mockRouter.locale = 'en';
        mockRouter.defaultLocale = 'en';

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/models')).toBe('/my-project/models');
      });

      it('includes locale prefix for non-default locales', async () => {
        mockRouter.query = { project: 'my-project' };
        mockRouter.locale = 'de';
        mockRouter.defaultLocale = 'en';

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/models')).toBe(
          '/de/my-project/models',
        );
      });

      it('includes locale prefix without project', async () => {
        mockRouter.query = {};
        mockRouter.locale = 'de';
        mockRouter.defaultLocale = 'en';

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.projectUrl('/models')).toBe('/de/models');
      });

      it('handles locale prefix with query parameters', async () => {
        mockRouter.query = { project: 'my-project' };
        mockRouter.locale = 'de';
        mockRouter.defaultLocale = 'en';

        const { result } = renderHook(() => useProject(), {
          wrapper: createWrapper(),
        });

        await waitForProjectsLoaded(result);

        expect(result.current.activeProject).toBe('my-project');
        expect(result.current.projectUrl('/chat?workload=abc')).toBe(
          '/de/my-project/chat?workload=abc',
        );
      });
    });
  });

  describe('setActiveProject routing', () => {
    it('redirects to dashboard when switching project from a workload detail page', async () => {
      mockRouter.query = { project: 'my-project', id: 'workload-1' };
      mockRouter.pathname = '/[project]/workloads/[id]';

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      await act(async () => {
        result.current.setActiveProject('other-project');
      });

      expect(mockRouter.push).toHaveBeenCalledWith('/other-project/');
    });

    it('redirects to dashboard when switching project from an AIM detail page', async () => {
      mockRouter.query = { project: 'my-project', id: 'aim-service-1' };
      mockRouter.pathname = '/[project]/aims/[id]';

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      await act(async () => {
        result.current.setActiveProject('other-project');
      });

      expect(mockRouter.push).toHaveBeenCalledWith('/other-project/');
    });

    it('stays on list page when switching project from a list page', async () => {
      mockRouter.query = { project: 'my-project' };
      mockRouter.pathname = '/[project]/workloads';

      const { result } = renderHook(() => useProject(), {
        wrapper: createWrapper(),
      });

      await waitForProjectsLoaded(result);

      await act(async () => {
        result.current.setActiveProject('other-project');
      });

      expect(mockRouter.push).toHaveBeenCalledWith({
        pathname: '/[project]/workloads',
        query: { project: 'other-project' },
      });
    });
  });
});
