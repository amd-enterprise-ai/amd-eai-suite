// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Mock } from 'vitest';

import { DeployCustomAIMDrawer } from '@/components/features/models/DeployCustomAIMDrawer';
import wrapper from '@/__tests__/ProviderWrapper';
import { deployInference } from '@/lib/app/inference';
import { AIM_DEPLOY_PROFILE_OVERRIDE_KEYS } from '@/types/aims';
import { Model } from '@/types/models';
import { WorkloadStatus } from '@/types/enums/workloads';
import {
  invalidateQueriesSpy,
  wrapQueryClientWithInvalidateSpy,
} from '@/__tests__/testUtils/queryClientSpy';

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () =>
      wrapQueryClientWithInvalidateSpy(actual.useQueryClient()),
  };
});

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

vi.mock('@/lib/app/inference', () => ({
  deployInference: vi.fn(),
}));

const model: Model = {
  id: '1',
  name: 'model-1',
  canonicalName: 'org/model-1',
  resourceName: 'model-1',
  status: WorkloadStatus.COMPLETE,
};
const namespace = 'test-namespace';
const sourceUri = 'hf://org/model-1';
const onClose = vi.fn();

const renderDrawer = (
  overrides: Partial<Parameters<typeof DeployCustomAIMDrawer>[0]> = {},
) =>
  render(
    <DeployCustomAIMDrawer
      model={model}
      namespace={namespace}
      sourceUri={sourceUri}
      isOpen={true}
      onClose={onClose}
      {...overrides}
    />,
    { wrapper },
  );

describe('DeployCustomAIMDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    invalidateQueriesSpy.mockClear();
    (deployInference as Mock).mockResolvedValue({});
  });

  it('renders drawer when open', () => {
    renderDrawer();
    expect(screen.getByText('deployCustomAIMDrawer.title')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderDrawer({ isOpen: false });
    expect(
      screen.queryByText('deployCustomAIMDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('renders the header with model name, deploy target and source URI', () => {
    renderDrawer();
    expect(screen.getByText(model.name)).toBeInTheDocument();
    // The deploy-target namespace is interpolated into this label (the i18n mock
    // returns the key, so assert the label is present rather than the raw value).
    expect(
      screen.getByText('deployCustomAIMDrawer.header.deployingInto'),
    ).toBeInTheDocument();
    expect(screen.getByText(sourceUri)).toBeInTheDocument();
  });

  it('renders the display-name input', () => {
    renderDrawer();
    expect(
      screen.getByPlaceholderText(
        'deployCustomAIMDrawer.fields.displayName.placeholder',
      ),
    ).toBeInTheDocument();
  });

  it('reserves the runtime-profile placeholder slot', () => {
    renderDrawer();
    expect(screen.getByTestId('runtime-profile-slot')).toBeInTheDocument();
  });

  it('reveals autoscaling fields when the toggle is enabled', async () => {
    renderDrawer();
    expect(
      screen.queryByTestId('replica-range-slider'),
    ).not.toBeInTheDocument();
    const toggle = screen
      .getByTestId('autoscaling-toggle')
      .querySelector('input')!;
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(screen.getByTestId('replica-range-slider')).toBeInTheDocument();
    });
  });

  it('deploys with the expected payload and omits profile override fields', async () => {
    renderDrawer();
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(deployInference).toHaveBeenCalledWith(namespace, {
        model: model.resourceName,
        displayName: undefined,
        replicas: 1,
      });
    });
    const payload = (deployInference as Mock).mock.calls[0][1];
    expect(payload).not.toHaveProperty('nodePool');
    for (const key of AIM_DEPLOY_PROFILE_OVERRIDE_KEYS) {
      expect(payload).not.toHaveProperty(key);
    }
  });

  it('shows success toast and closes on successful deploy', async () => {
    renderDrawer();
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith(
        'deployCustomAIMDrawer.notifications.success',
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('invalidates the inferenceModel cache after a successful deploy', async () => {
    renderDrawer();

    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['inferenceModel'],
      });
    });
    // Existing per-namespace services cache is still invalidated alongside.
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({
      queryKey: ['project', namespace, 'aim-services'],
    });
  });

  it('shows error toast and keeps the drawer open on failed deploy', async () => {
    (deployInference as Mock).mockRejectedValue(new Error('Deploy failed'));
    renderDrawer();
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalled();
    });
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByText('deployCustomAIMDrawer.title')).toBeInTheDocument();
  });
});
