// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import SecretsPageContent from '@/components/features/secrets/SecretsPageContent';
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
  fetchSecrets: vi.fn(),
}));

vi.mock('@/utils/app/secrets', () => ({
  doesSecretDataNeedToBeRefreshed: vi.fn(() => false),
  isSecretActioning: vi.fn(() => false),
}));

describe('SecretsPageContent', () => {
  const mockSecrets = generateMockSecrets(2);
  const mockSecretsResponse = { secrets: mockSecrets };
  const mockActions = [
    {
      key: 'delete',
      label: 'Delete',
      onPress: vi.fn(),
    },
  ];

  const setup = (
    props?: Partial<React.ComponentProps<typeof SecretsPageContent>>,
  ) => {
    act(() => {
      render(
        <SecretsPageContent
          initialSecrets={mockSecretsResponse}
          actions={mockActions}
          {...props}
        />,
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

  it('shows scope column by default', () => {
    setup();
    expect(screen.getByText('list.headers.scope.title')).toBeInTheDocument();
  });

  it('hides scope column when showScopeColumn is false', () => {
    setup({ showScopeColumn: false });
    expect(
      screen.queryByText('list.headers.scope.title'),
    ).not.toBeInTheDocument();
  });

  it('shows assigned to column by default', () => {
    setup();
    expect(
      screen.getByText('list.headers.assignedTo.title'),
    ).toBeInTheDocument();
  });

  it('hides assigned to column when showAssignedToColumn is false', () => {
    setup({ showAssignedToColumn: false });
    expect(
      screen.queryByText('list.headers.assignedTo.title'),
    ).not.toBeInTheDocument();
  });

  it('does not show additional actions by default', () => {
    setup();
    expect(screen.queryByText('Add Secret')).not.toBeInTheDocument();
  });

  it('shows additional actions when showAddButton is true and additionalActions provided', () => {
    const additionalActions = <button>Add Secret</button>;
    setup({ showAddButton: true, additionalActions });
    expect(screen.getByText('Add Secret')).toBeInTheDocument();
  });

  it('renders additional modals when provided', () => {
    const additionalModals = <div data-testid="custom-modal">Custom Modal</div>;
    setup({ additionalModals });
    expect(screen.getByTestId('custom-modal')).toBeInTheDocument();
  });

  it('uses provided actions in table', () => {
    const customActions = [
      {
        key: 'edit',
        label: 'Edit',
        onPress: vi.fn(),
      },
      {
        key: 'delete',
        label: 'Delete',
        onPress: vi.fn(),
      },
    ];

    setup({ actions: customActions });
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
});
