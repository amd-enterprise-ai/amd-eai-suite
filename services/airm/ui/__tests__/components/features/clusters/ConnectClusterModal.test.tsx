// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { addCluster, getCluster } from '@/services/app/clusters';

import ConnectClusterModal from '@/components/features/clusters/ConnectClusterModal';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

vi.mock('@/services/app/clusters', () => ({
  addCluster: vi.fn(),
  getCluster: vi.fn(),
}));

const renderConnectClusterModal = (onOpenChange = vi.fn(), isOpen = true) => {
  return act(() => {
    render(
      <ConnectClusterModal onOpenChange={onOpenChange} isOpen={isOpen} />,
      { wrapper },
    );
  });
};

describe('ConnectClusterModal', () => {
  beforeEach(() => {
    (addCluster as Mock).mockClear();
    (getCluster as Mock).mockClear();
  });

  it('renders ConnectClusterModal component', async () => {
    await renderConnectClusterModal();
    const modelTitle = screen.getAllByText('connectCluster.title');
    expect(modelTitle.length).toBeGreaterThan(0);
  });

  it('Create cluster API call will be called', async () => {
    (addCluster as Mock).mockResolvedValueOnce({
      id: 'cluster-id-1',
      name: null,
      userSecret: 'issued-token',
    });

    await renderConnectClusterModal();

    const nextButton = screen.getByText('connectCluster.start.actions.next');
    await fireEvent.click(nextButton);

    await waitFor(() => {
      expect(addCluster).toHaveBeenCalled();
      expect(screen.getByText(/cluster-id-1/i)).toBeInTheDocument();
      expect(screen.getByText(/issued-token/i)).toBeInTheDocument();
    });
  });

  it('confirm script step', async () => {
    (addCluster as Mock).mockResolvedValueOnce({
      id: 'cluster-id-1',
      name: null,
      userSecret: 'issued-token',
    });

    await renderConnectClusterModal();

    const nextButton = screen.getByText('connectCluster.start.actions.next');
    await fireEvent.click(nextButton);

    await waitFor(() => {
      expect(addCluster).toHaveBeenCalled();
      expect(screen.getByText(/cluster-id-1/i)).toBeInTheDocument();
      expect(screen.getByText(/issued-token/i)).toBeInTheDocument();
    });

    const scriptStepNextButton = screen.getByText(
      'connectCluster.script.actions.next',
    );
    expect(scriptStepNextButton).toBeDisabled();

    const confirmCheckbox = screen.getByRole('checkbox');
    await fireEvent.click(confirmCheckbox);
    expect(scriptStepNextButton).not.toBeDisabled();
  });

  it('show final step', async () => {
    (addCluster as Mock).mockResolvedValueOnce({
      id: 'cluster-id-1',
      name: null,
      userSecret: 'issued-token',
    });

    await renderConnectClusterModal();

    const nextButton = screen.getByText('connectCluster.start.actions.next');
    await fireEvent.click(nextButton);

    await waitFor(() => {
      expect(addCluster).toHaveBeenCalled();
      expect(screen.getByText(/cluster-id-1/i)).toBeInTheDocument();
      expect(screen.getByText(/issued-token/i)).toBeInTheDocument();

      //   expect(screen.queryByText('issued-token')).toBeInTheDocument();
    });

    const scriptStepNextButton = screen.getByText(
      'connectCluster.script.actions.next',
    );
    expect(scriptStepNextButton).toBeDisabled();

    const confirmCheckbox = screen.getByRole('checkbox');
    await fireEvent.click(confirmCheckbox);
    expect(scriptStepNextButton).not.toBeDisabled();

    await fireEvent.click(scriptStepNextButton);

    await waitFor(() => {
      expect(
        screen.getByText('connectCluster.final.content.description'),
      ).toBeInTheDocument();
    });
  });
});
