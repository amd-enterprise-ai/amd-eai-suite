// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DeployFinetuneAIMDrawer } from '@/components/features/models/DeployFinetuneAIMDrawer';
import { Model } from '@/types/models';
import { WorkloadStatus } from '@/types/enums/workloads';
import wrapper from '@/__tests__/ProviderWrapper';
import { deployAim } from '@/lib/app/aims';
import { Mock } from 'vitest';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useSystemToast: () => ({
    toast: mockToast,
  }),
}));

vi.mock('@/lib/app/aims', async (importOriginal) => ({
  ...(await importOriginal()),
  deployAim: vi.fn(),
}));

const model: Model = {
  id: '1',
  name: 'model-1',
  canonicalName: 'org/model-1',
  resourceName: 'model-1',
  status: WorkloadStatus.COMPLETE,
};
const namespace = 'test-namespace';
const onClose = vi.fn();

describe('DeployFinetuneAIMDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (deployAim as Mock).mockResolvedValue({});
  });

  it('renders drawer when open', () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(
      screen.getByText('deployFinetuneAIMDrawer.title'),
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={false}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(
      screen.queryByText('deployFinetuneAIMDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('shows read-only name field with model resource name', () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(screen.getByDisplayValue(model.resourceName!)).toBeInTheDocument();
  });

  it('deploy button is enabled on open', () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(
      screen.getByText('deployFinetuneAIMDrawer.actions.deploy'),
    ).not.toBeDisabled();
  });

  it('shows success toast and calls onClose on successful deploy', async () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    // DrawerForm's confirm button uses onPress → requestSubmit(); submit the form directly
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith(
        'deployFinetuneAIMDrawer.notifications.success',
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast when deploy fails', async () => {
    (deployAim as Mock).mockRejectedValue(new Error('Deploy failed'));

    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    // DrawerForm's confirm button uses onPress → requestSubmit(); submit the form directly
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalled();
    });
  });

  it('displays model name and canonical name', () => {
    render(
      <DeployFinetuneAIMDrawer
        model={model}
        namespace={namespace}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(screen.getByText(model.name)).toBeInTheDocument();
    expect(screen.getByText(model.canonicalName)).toBeInTheDocument();
  });
});
