// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { GetServerSidePropsContext } from 'next';

import { getServerSession } from 'next-auth';

import ApiKeysPage, { getServerSideProps } from '@/pages/api-keys/index';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock next-auth
vi.mock('next-auth', () => ({
  getServerSession: vi.fn(),
}));

// Mock serverSideTranslations
vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn().mockResolvedValue({}),
}));

// Mock the project context
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'project1',
    projects: [{ id: 'project1', name: 'Project 1' }],
    isLoading: false,
    setActiveProject: vi.fn(),
  }),
}));

// Mock the API keys components
vi.mock('@/components/features/api-keys/ApiKeysTable', () => ({
  default: ({ createButton }: { createButton: React.ReactNode }) => (
    <div data-testid="api-keys-table">
      API Keys Table
      {createButton}
    </div>
  ),
}));

vi.mock('@/components/features/api-keys/CreateApiKey', () => ({
  default: ({ isOpen }: { isOpen: boolean }) => (
    <div data-testid="create-api-key" data-open={isOpen}>
      Create API Key Modal
    </div>
  ),
}));

const mockGetServerSession = vi.mocked(getServerSession);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ApiKeysPage', () => {
  describe('with active project', () => {
    it('renders API keys table with active project', () => {
      render(<ApiKeysPage />, { wrapper });

      expect(screen.getByTestId('api-keys-table')).toBeInTheDocument();
      expect(screen.getByText('list.actions.create.title')).toBeInTheDocument();
      expect(screen.getByTestId('create-api-key')).toBeInTheDocument();
    });

    it('renders create button correctly', () => {
      render(<ApiKeysPage />, { wrapper });

      const createButton = screen.getByText('list.actions.create.title');
      expect(createButton).toBeInTheDocument();
      expect(createButton.tagName).toBe('BUTTON');
    });

    it('modal is closed by default', () => {
      render(<ApiKeysPage />, { wrapper });

      const modal = screen.getByTestId('create-api-key');
      expect(modal).toHaveAttribute('data-open', 'false');
    });
  });
});

describe('getServerSideProps', () => {
  const mockContext = {
    locale: 'en',
    req: {},
    res: {},
  } as GetServerSidePropsContext;

  it('returns props with translations when session is valid', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: 'valid-token',
    } as any);

    const result = await getServerSideProps(mockContext);

    expect(result).toEqual({
      props: {},
    });

    expect(mockGetServerSession).toHaveBeenCalledWith(
      mockContext.req,
      mockContext.res,
      expect.any(Object), // authOptions
    );
  });

  it('redirects to home when session is missing', async () => {
    mockGetServerSession.mockResolvedValue(null);

    const result = await getServerSideProps(mockContext);

    expect(result).toEqual({
      redirect: {
        destination: '/',
        permanent: false,
      },
    });
  });

  it('redirects when user is missing', async () => {
    mockGetServerSession.mockResolvedValue({
      user: null,
      accessToken: 'valid-token',
    } as any);

    const result = await getServerSideProps(mockContext);

    expect(result).toEqual({
      redirect: {
        destination: '/',
        permanent: false,
      },
    });
  });

  it('redirects when user email is missing', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: null },
      accessToken: 'valid-token',
    } as any);

    const result = await getServerSideProps(mockContext);

    expect(result).toEqual({
      redirect: {
        destination: '/',
        permanent: false,
      },
    });
  });

  it('redirects when access token is missing', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: null,
    } as any);

    const result = await getServerSideProps(mockContext);

    expect(result).toEqual({
      redirect: {
        destination: '/',
        permanent: false,
      },
    });
  });

  it('handles different locales', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: 'valid-token',
    } as any);

    const contextWithDifferentLocale = {
      ...mockContext,
      locale: 'fr',
    };

    await getServerSideProps(contextWithDifferentLocale);

    expect(mockGetServerSession).toHaveBeenCalledWith(
      contextWithDifferentLocale.req,
      contextWithDifferentLocale.res,
      expect.any(Object),
    );
  });

  it('handles missing locale', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: 'valid-token',
    } as any);

    const contextWithoutLocale = {
      ...mockContext,
      locale: undefined,
    };

    const result = await getServerSideProps(contextWithoutLocale);

    expect(result).toHaveProperty('props');
  });
});

describe('API Keys Page Integration', () => {
  it('integrates table and modal correctly', () => {
    render(<ApiKeysPage />, { wrapper });

    // Both components should be present
    expect(screen.getByTestId('api-keys-table')).toBeInTheDocument();
    expect(screen.getByTestId('create-api-key')).toBeInTheDocument();

    // Create button should be passed to table
    expect(screen.getByText('list.actions.create.title')).toBeInTheDocument();
  });

  it('passes correct props to components', () => {
    render(<ApiKeysPage />, { wrapper });

    const table = screen.getByTestId('api-keys-table');
    const modal = screen.getByTestId('create-api-key');

    // Verify components are rendered (props are tested in component tests)
    expect(table).toBeInTheDocument();
    expect(modal).toBeInTheDocument();
  });
});
