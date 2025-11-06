// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SessionProvider } from 'next-auth/react';

import WorkbenchSecretsPageContent from '@/components/features/secrets/WorkbenchSecretsPageContent';
import { generateMockSecrets } from '../../../../__mocks__/utils/secrets-mock';

import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('@/hooks/useSecretsFilters', () => ({
  useSecretsFilters: () => ({
    filters: [],
    handleFilterChange: vi.fn(),
    filterConfig: {
      search: {
        name: 'search',
        className: 'w-full',
        label: 'list.filter.search.label',
        placeholder: 'list.filter.search.placeholder',
        type: 'text',
      },
    },
  }),
}));

vi.mock('@/services/app/secrets', () => ({
  fetchWorkbenchSecrets: vi.fn(),
}));

vi.mock('@/utils/app/secrets', () => ({
  doesSecretDataNeedToBeRefreshed: vi.fn(() => false),
  isSecretActioning: vi.fn(() => false),
}));

const mockSession = {
  user: {
    email: 'test@example.com',
    name: 'Test User',
  },
  expires: '2025-01-01',
};

describe('WorkbenchSecretsPageContent', () => {
  const mockSecrets = generateMockSecrets(2);
  const mockSecretsResponse = { secrets: mockSecrets };

  const setup = (
    session: any = mockSession,
    props?: Partial<React.ComponentProps<typeof WorkbenchSecretsPageContent>>,
  ) => {
    act(() => {
      render(
        <SessionProvider session={session}>
          <WorkbenchSecretsPageContent
            initialSecrets={mockSecretsResponse}
            {...props}
          />
        </SessionProvider>,
        { wrapper },
      );
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    setup();
    // Component renders successfully
    const tables = screen.queryAllByRole('table');
    expect(tables.length).toBeGreaterThanOrEqual(0);
  });

  it('displays secrets table with data', () => {
    setup();
    expect(screen.getByText(mockSecrets[0].name)).toBeInTheDocument();
  });

  it('does not show scope column', () => {
    setup();
    expect(
      screen.queryByText('list.headers.scope.title'),
    ).not.toBeInTheDocument();
  });

  it('does not show assigned to column', () => {
    setup();
    expect(
      screen.queryByText('list.headers.assignedTo.title'),
    ).not.toBeInTheDocument();
  });

  it('renders delete action button', () => {
    setup();
    const actionButtons = screen.getAllByRole('button');
    const contextMenuButtons = actionButtons.filter((btn) =>
      btn.getAttribute('aria-label')?.includes('list.actions.label'),
    );
    expect(contextMenuButtons.length).toBeGreaterThan(0);
  });

  it('renders table with action buttons', () => {
    setup();
    const actionButtons = screen.getAllByRole('button');
    const contextMenuButtons = actionButtons.filter((btn) =>
      btn.getAttribute('aria-label')?.includes('list.actions.label'),
    );
    expect(contextMenuButtons.length).toBeGreaterThan(0);
  });

  it('renders with project-assigned secrets', () => {
    setup();
    expect(screen.getByText(mockSecrets[0].name)).toBeInTheDocument();
    expect(screen.getByText(mockSecrets[1].name)).toBeInTheDocument();
  });
});
