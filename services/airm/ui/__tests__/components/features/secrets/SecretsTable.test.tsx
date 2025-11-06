// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { generateMockSecrets } from '../../../../__mocks__/utils/secrets-mock';

import SecretsTable from '@/components/features/secrets/SecretsTable';

import wrapper from '@/__tests__/ProviderWrapper';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

const mockFetchProjectSecrets = vi.fn();
const mockFetchSecrets = vi.fn();
vi.mock('@/services/app/secrets', () => ({
  fetchProjectSecrets: (...args: any[]) => mockFetchProjectSecrets(...args),
}));

describe('SecretsTable', () => {
  const secret = generateMockSecrets(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof SecretsTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <SecretsTable secrets={[]} isSecretsLoading={false} {...props} />,
        { wrapper },
      );
    });
    return { onOpenChange };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('render without projectId', () => {
    setup();
    expect(screen.getByText('list.headers.name.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.type.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.status.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.scope.title')).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.assignedTo.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.updatedAt.title'),
    ).toBeInTheDocument();
    expect(mockFetchProjectSecrets).not.toHaveBeenCalled();
  });
});
