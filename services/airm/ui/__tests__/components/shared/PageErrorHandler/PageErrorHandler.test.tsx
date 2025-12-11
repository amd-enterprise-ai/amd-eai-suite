// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor } from '@testing-library/react';

import { useRouter } from 'next/router';

import * as projectsService from '@/services/app/projects';

import { ErrorCodes } from '@/types/errors';

import PageErrorHandler from '@/components/shared/PageErrorHandler/PageErrorHandler';

import userEvent from '@testing-library/user-event';

// Mock Next.js router
const mockRouter = {
  pathname: '/dashboard',
  replace: vi.fn(),
  push: vi.fn(),
  asPath: '/dashboard',
};

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

// Mock the projects service
vi.mock('@/services/app/projects', () => ({
  fetchSubmittableProjects: vi.fn(),
}));

const mockFetchSubmittableProjects = vi.mocked(
  projectsService.fetchSubmittableProjects,
);

// Mock translations
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'error.noSubmittableProjects.title': 'No Projects Available',
        'error.noSubmittableProjects.description':
          'You need to have access to at least one project to use this feature.',
        'error.network.title': 'Network Error',
        'error.network.description':
          'Please check your connection and try again.',
        'error.unknown.title': 'Unknown Error',
        'error.unknown.description': 'An unexpected error occurred.',
        'error.refreshActionLabel': 'Try Again',
        'actions.showDetails.title': 'Show Details',
        'error.label': 'Error',
        'charts.loading': 'Loading...',
      };
      return translations[key] || key;
    },
  }),
}));

describe('PageErrorHandler Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as any).mockReturnValue(mockRouter);
  });

  describe('Rendering States', () => {
    it('should render children when no validation is required (unprotected page)', async () => {
      // Setup unprotected page
      mockRouter.pathname = '/dashboard';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/dashboard',
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
      expect(mockFetchSubmittableProjects).not.toHaveBeenCalled();
    });

    it('should render loading state initially when validation is required', async () => {
      // Setup protected page
      mockRouter.pathname = '/chat';
      (useRouter as any).mockReturnValue({ ...mockRouter, pathname: '/chat' });

      // Make API call hang to show loading state
      let resolveProjects: (value: any) => void;
      const projectsPromise = new Promise((resolve) => {
        resolveProjects = resolve;
      });
      mockFetchSubmittableProjects.mockReturnValue(projectsPromise);

      render(
        <PageErrorHandler>
          <div data-testid="chat-content">Chat Interface</div>
        </PageErrorHandler>,
      );

      // Should show loading state
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByTestId('chat-content')).not.toBeInTheDocument();

      // Resolve with projects
      resolveProjects!({ projects: [{ id: '1', name: 'Test Project' }] });

      await waitFor(() => {
        expect(screen.getByTestId('chat-content')).toBeInTheDocument();
      });

      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    it('should render children when validation passes (has projects)', async () => {
      // Setup protected page with valid projects
      mockRouter.pathname = '/models';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/models',
      });
      mockFetchSubmittableProjects.mockResolvedValue({
        projects: [
          { id: '1', name: 'Project 1' },
          { id: '2', name: 'Project 2' },
        ],
      });

      render(
        <PageErrorHandler>
          <div data-testid="models-content">
            <h1>Models Page</h1>
            <div>Model List</div>
          </div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByTestId('models-content')).toBeInTheDocument();
      });

      expect(screen.getByText('Models Page')).toBeInTheDocument();
      expect(screen.getByText('Model List')).toBeInTheDocument();
      expect(mockFetchSubmittableProjects).toHaveBeenCalledTimes(1);
    });

    it('should render error message when validation fails (no projects)', async () => {
      // Setup protected page with no projects
      mockRouter.pathname = '/datasets';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/datasets',
      });
      mockFetchSubmittableProjects.mockResolvedValue({ projects: [] });

      render(
        <PageErrorHandler>
          <div data-testid="datasets-content">Datasets Content</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('No Projects Available')).toBeInTheDocument();
      });

      expect(
        screen.getByText(
          'You need to have access to at least one project to use this feature.',
        ),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('datasets-content')).not.toBeInTheDocument();
    });

    it('should render error message when validation fails (network error)', async () => {
      // Setup protected page with network error
      mockRouter.pathname = '/workloads';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/workloads',
      });
      mockFetchSubmittableProjects.mockRejectedValue(
        new Error('Network failure'),
      );

      render(
        <PageErrorHandler>
          <div data-testid="workloads-content">Workloads Content</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('Network Error')).toBeInTheDocument();
      });

      expect(
        screen.getByText('Please check your connection and try again.'),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('workloads-content')).not.toBeInTheDocument();
    });

    it('should render error message for workspaces page when no projects available', async () => {
      mockRouter.pathname = '/workspaces';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/workspaces',
      });
      mockFetchSubmittableProjects.mockResolvedValue({ projects: [] });

      render(
        <PageErrorHandler>
          <div data-testid="workspaces-content">Workspaces Content</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('No Projects Available')).toBeInTheDocument();
      });

      expect(
        screen.getByText(
          'You need to have access to at least one project to use this feature.',
        ),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId('workspaces-content'),
      ).not.toBeInTheDocument();
    });

    it('should allow retry after error and show success', async () => {
      const user = userEvent.setup();

      mockRouter.pathname = '/chat';
      (useRouter as any).mockReturnValue({ ...mockRouter, pathname: '/chat' });

      // Initially fail
      mockFetchSubmittableProjects.mockRejectedValue(
        new Error('Initial failure'),
      );

      render(
        <PageErrorHandler>
          <div data-testid="chat-content">Chat Interface</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('Network Error')).toBeInTheDocument();
      });

      // Setup successful retry
      mockFetchSubmittableProjects.mockClear();
      mockFetchSubmittableProjects.mockResolvedValue({
        projects: [{ id: '1', name: 'New Project' }],
      });

      // Click retry button
      const retryButton = screen.getByRole('button', { name: 'Try Again' });
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByTestId('chat-content')).toBeInTheDocument();
      });

      expect(screen.queryByText('Network Error')).not.toBeInTheDocument();
      expect(mockFetchSubmittableProjects).toHaveBeenCalledTimes(1);
    });

    it('should show loading state during retry', async () => {
      const user = userEvent.setup();

      mockRouter.pathname = '/datasets';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/datasets',
      });

      // Initially no projects
      mockFetchSubmittableProjects.mockResolvedValue({ projects: [] });

      render(
        <PageErrorHandler>
          <div data-testid="datasets-content">Datasets</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('No Projects Available')).toBeInTheDocument();
      });

      // Setup slow retry
      let resolveRetry: (value: any) => void;
      const retryPromise = new Promise((resolve) => {
        resolveRetry = resolve;
      });
      mockFetchSubmittableProjects.mockClear();
      mockFetchSubmittableProjects.mockReturnValue(retryPromise);

      // Click retry
      const retryButton = screen.getByRole('button', { name: 'Try Again' });
      await user.click(retryButton);

      // Should show loading
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(
        screen.queryByText('No Projects Available'),
      ).not.toBeInTheDocument();

      // Complete retry successfully
      resolveRetry!({ projects: [{ id: '1', name: 'Success' }] });

      await waitFor(() => {
        expect(screen.getByTestId('datasets-content')).toBeInTheDocument();
      });
    });

    it('should handle retry that fails again', async () => {
      const user = userEvent.setup();

      mockRouter.pathname = '/models';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/models',
      });

      // Initially network error
      mockFetchSubmittableProjects.mockRejectedValue(
        new Error('Network error'),
      );

      render(
        <PageErrorHandler>
          <div data-testid="models-content">Models</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByText('Network Error')).toBeInTheDocument();
      });

      // Setup retry that also fails
      mockFetchSubmittableProjects.mockClear();
      mockFetchSubmittableProjects.mockRejectedValue(
        new Error('Still failing'),
      );

      // Click retry
      const retryButton = screen.getByRole('button', { name: 'Try Again' });
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Network Error')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('models-content')).not.toBeInTheDocument();
      expect(mockFetchSubmittableProjects).toHaveBeenCalledTimes(1);
    });
    it('should handle partial path matches correctly', async () => {
      // Test that /chat/room/123 should match /chat validation
      mockRouter.pathname = '/chat/room/123';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/chat/room/123',
      });
      mockFetchSubmittableProjects.mockResolvedValue({
        projects: [{ id: '1', name: 'Chat Project' }],
      });

      render(
        <PageErrorHandler>
          <div data-testid="chat-room-content">Chat Room</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByTestId('chat-room-content')).toBeInTheDocument();
      });

      expect(mockFetchSubmittableProjects).toHaveBeenCalledTimes(1);
    });
    it('should not validate similar but different paths', async () => {
      // Test that /chatroom should not match /chat validation
      mockRouter.pathname = '/chatroom';
      (useRouter as any).mockReturnValue({
        ...mockRouter,
        pathname: '/chatroom',
      });

      render(
        <PageErrorHandler>
          <div data-testid="chatroom-content">Chat Room App</div>
        </PageErrorHandler>,
      );

      await waitFor(() => {
        expect(screen.getByTestId('chatroom-content')).toBeInTheDocument();
      });

      // Should not call validation since /chatroom doesn't start with /chat exactly
      expect(mockFetchSubmittableProjects).not.toHaveBeenCalled();
    });
  });
});
