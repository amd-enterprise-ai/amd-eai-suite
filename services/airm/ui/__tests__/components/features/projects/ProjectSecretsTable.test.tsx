// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { generateMockProjectSecretsWithParentSecret } from '../../../../__mocks__/utils/secrets-mock';

import { ProjectSecretsTable } from '@/components/features/projects/ProjectSecretsTable';

import wrapper from '@/__tests__/ProviderWrapper';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

describe('ProjectSecretsTable', () => {
  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectSecretsTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectSecretsTable
          isLoading={false}
          projectSecrets={[]}
          {...props}
        />,
        {
          wrapper,
        },
      );
    });
    return { onOpenChange };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('default render', () => {
    setup();
    expect(screen.getByText('list.headers.name.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.type.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.status.title')).toBeInTheDocument();

    expect(
      screen.getByText('list.headers.updatedAt.title'),
    ).toBeInTheDocument();
  });

  it('render with data', () => {
    setup({ projectSecrets: generateMockProjectSecretsWithParentSecret(1) });
    expect(screen.getByText('My Secret 1')).toBeInTheDocument();
  });
});
