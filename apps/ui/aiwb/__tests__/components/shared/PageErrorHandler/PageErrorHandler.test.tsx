// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor } from '@testing-library/react';

import { useRouter } from 'next/router';
import { useProject } from '@/contexts/ProjectContext';

import { ActionButton } from '@amdenterpriseai/components';

import { PageErrorHandler } from '@/components/shared/PageErrorHandler/PageErrorHandler';

import userEvent from '@testing-library/user-event';

// Mock Next.js router
const mockRouter = {
  pathname: '/start',
  replace: vi.fn(),
  push: vi.fn(),
  asPath: '/start',
};

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: vi.fn(),
}));

const mockUseProject = vi.mocked(useProject);
const mockRefetchProjects = vi.fn();

// Mock translations - return key as value for stable assertions
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@amdenterpriseai/components', async (importOriginal) => ({
  ...(await importOriginal()),
  ActionButton: ({ children, onPress, ...props }: any) => (
    <button onClick={onPress} {...props}>
      {children}
    </button>
  ),
}));

const setProjectState = (
  overrides: Partial<ReturnType<typeof useProject>> = {},
) => {
  mockUseProject.mockReturnValue({
    isStandaloneMode: false,
    activeProject: 'project-1',
    projects: [{ id: 'project-1', name: 'Project 1' }],
    isLoading: false,
    isInitialized: true,
    projectError: null,
    refetchProjects: mockRefetchProjects,
    setActiveProject: vi.fn(),
    ...overrides,
  });
};

describe('PageErrorHandler Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as any).mockReturnValue(mockRouter);
    setProjectState();
  });

  describe('Rendering States', () => {
    it('renders children when project validation is not required', async () => {
      setProjectState({
        activeProject: null,
        projects: [],
        isInitialized: false,
      });
      render(
        <PageErrorHandler>
          <div data-testid="main-content">
            <h1>Welcome to Dashboard</h1>
            <button>Dashboard Action</button>
          </div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByTestId('main-content')).toBeInTheDocument();
      });

      expect(screen.getByText('Welcome to Dashboard')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Dashboard Action' }),
      ).toBeInTheDocument();
    });

    it('renders loading state while projects are loading', async () => {
      setProjectState({ isLoading: true });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="chat-content">Chat Interface</div>
        </PageErrorHandler>,
      );

      expect(screen.getByText('charts.loading')).toBeInTheDocument();
      expect(screen.queryByTestId('chat-content')).not.toBeInTheDocument();
    });

    it('renders loading state while required project context is initializing', async () => {
      setProjectState({ isInitialized: false });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="content">Page Content</div>
        </PageErrorHandler>,
      );

      expect(screen.getByText('charts.loading')).toBeInTheDocument();
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('renders no projects error when required and user has no projects', async () => {
      setProjectState({ activeProject: null, projects: [] });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="datasets-content">Datasets Content</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(
          screen.getByText('error.noSubmittableProjects.title'),
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText('error.noSubmittableProjects.description'),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('datasets-content')).not.toBeInTheDocument();
    });

    it('renders network error when project fetch failed and no cached projects exist', async () => {
      setProjectState({
        activeProject: null,
        projects: [],
        projectError: new Error('Network failure'),
      });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="workloads-content">Workloads Content</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('error.fetchFailed.title')).toBeInTheDocument();
      });

      expect(
        screen.getByText('error.fetchFailed.description'),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('workloads-content')).not.toBeInTheDocument();
    });

    it('renders children when projects exist even if latest background fetch failed', async () => {
      setProjectState({
        projectError: new Error('Transient error'),
      });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="content">Workbench Content</div>
        </PageErrorHandler>,
      );
      expect(screen.getByTestId('content')).toBeInTheDocument();
      expect(
        screen.queryByText('error.fetchFailed.title'),
      ).not.toBeInTheDocument();
    });

    it('renders no active project component when projects exist but no active project selected', async () => {
      setProjectState({
        activeProject: null,
        projects: [{ id: 'project-1', name: 'Project 1' }],
      });
      render(
        <PageErrorHandler
          projectRequired={true}
          noActiveProjectComponent={<div data-testid="project-prompt" />}
        >
          <div data-testid="content">Workbench Content</div>
        </PageErrorHandler>,
      );
      expect(screen.getByTestId('project-prompt')).toBeInTheDocument();
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('calls refetchProjects when retry action is clicked', async () => {
      const user = userEvent.setup();
      setProjectState({
        activeProject: null,
        projects: [],
        projectError: new Error('Network failure'),
      });
      render(
        <PageErrorHandler projectRequired={true}>
          <div data-testid="content">Workbench Content</div>
        </PageErrorHandler>,
      );
      await waitFor(() => {
        expect(screen.getByText('error.fetchFailed.title')).toBeInTheDocument();
      });
      const retryButton = screen.getByRole('button', {
        name: 'error.refreshActionLabel',
      });
      await user.click(retryButton);
      expect(mockRefetchProjects).toHaveBeenCalledTimes(1);
    });
  });
});
