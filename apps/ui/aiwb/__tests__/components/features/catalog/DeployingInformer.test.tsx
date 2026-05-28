// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import DeployingInformer from '@/components/features/catalog/DeployingInformer';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';

// Mock PrimaryButton to simplify
vi.mock('@amdenterpriseai/components', async (importOriginal) => ({
  ...(await importOriginal()),
  PrimaryButton: (props: any) => (
    <button onClick={props.onPress}>{props.children}</button>
  ),
}));

// Provide a simple translation mock
const t = (key: string) => key;

const inferenceWorkload = mockWorkloads.find((w) => w.id === 'workload-1');

describe('DeployingInformer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders deploying state when not deployed', () => {
    render(
      <DeployingInformer
        name="My Workload"
        isDeployed={false}
        workloadId=""
        workloadData={{}}
        t={t as any}
      />,
    );
    expect(
      screen.getByText('deployModal.deploymentStatus.deployingMessage'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('deployModal.deploymentStatus.launchButtonPending'),
    ).toBeInTheDocument();
  });

  it('opens external host when non-model deployment has externalHost', () => {
    window.open = vi.fn();
    render(
      <DeployingInformer
        name={inferenceWorkload?.displayName || 'Service Workload'}
        isDeployed={true}
        workloadId={inferenceWorkload?.id || 'svc-1'}
        workloadData={inferenceWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(window.open).toHaveBeenCalledWith(
      inferenceWorkload?.endpoints?.external,
      '_blank',
    );
  });

  it('does nothing if no workloadId provided', () => {
    window.open = vi.fn();
    render(
      <DeployingInformer
        name="No ID"
        isDeployed={true}
        workloadId=""
        workloadData={inferenceWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(window.open).not.toHaveBeenCalled();
  });
});
