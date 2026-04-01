// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { generateMockProjectSecretsWithParentSecret } from '../../../../__mocks__/utils/secrets-mock';

import { ProjectSecretsTable } from '@/components/features/projects/ProjectSecretsTable';
import { ProjectSecretStatus } from '@amdenterpriseai/types';

import wrapper from '@/__tests__/ProviderWrapper';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@amdenterpriseai/hooks', () => ({
  useSystemToast: () => ({ toast: mockToast }),
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

  it('status has popup with more details for Unknown status', () => {
    const secrets = generateMockProjectSecretsWithParentSecret(1);
    secrets[0].status = ProjectSecretStatus.UNKNOWN;
    secrets[0].statusReason = 'something went wrong';

    setup({ projectSecrets: secrets });

    const statusElement = screen.getByText(
      'secretStatus.Unknown',
    ).parentElement;
    expect(statusElement).toHaveAttribute('aria-haspopup', 'dialog');
  });

  it('status does not have popup with for non-error status', () => {
    const secrets = generateMockProjectSecretsWithParentSecret(1);
    secrets[0].status = ProjectSecretStatus.SYNCED;
    secrets[0].statusReason = 'no error';

    setup({ projectSecrets: secrets });

    const statusElement = screen.getByText('secretStatus.Synced').parentElement;
    expect(statusElement).not.toHaveAttribute('aria-haspopup');
  });
});
