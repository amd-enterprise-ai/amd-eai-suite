// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import router from 'next/router';
import DeployingInformer from '@/components/features/catalog/DeployingInformer';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';

// Mock next/router
vi.mock('next/router', () => ({
  default: {
    push: vi.fn(),
  },
}));

// Mock PrimaryButton to simplify
vi.mock('@/components/shared/Buttons/PrimaryButton', () => ({
  default: (props: any) => (
    <button onClick={props.onPress}>{props.children}</button>
  ),
}));

// Provide a simple translation mock
const t = (key: string) => key;

const inferenceWorkload = mockWorkloads.find((w) => w.id === 'workload-1');
// Create a version with only host (no externalHost) for that specific test
const hostOnlyWorkload = inferenceWorkload
  ? {
      ...inferenceWorkload,
      output: { host: inferenceWorkload.output?.externalHost },
    }
  : ({ output: { host: 'https://host.example.com' } } as any);

describe('DeployingInformer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders deploying state when not deployed', () => {
    render(
      <DeployingInformer
        name="My Workload"
        isDeployed={false}
        isModelDeployment={false}
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

  it('renders ready state and triggers router push for model deployment', () => {
    const push = (router as any).push as any;
    render(
      <DeployingInformer
        name={inferenceWorkload?.displayName || 'Model Workload'}
        isDeployed={true}
        isModelDeployment={true}
        workloadId={inferenceWorkload?.id || 'model-1'}
        workloadData={inferenceWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(push).toHaveBeenCalledWith(
      `/chat/?workload=${inferenceWorkload?.id || 'model-1'}`,
    );
  });

  it('opens external host when non-model deployment has externalHost', () => {
    window.open = vi.fn();
    render(
      <DeployingInformer
        name={inferenceWorkload?.displayName || 'Service Workload'}
        isDeployed={true}
        isModelDeployment={false}
        workloadId={inferenceWorkload?.id || 'svc-1'}
        workloadData={inferenceWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(window.open).toHaveBeenCalledWith(
      inferenceWorkload?.output?.externalHost,
      '_blank',
    );
  });

  it('opens host when non-model deployment has only host (no externalHost)', () => {
    window.open = vi.fn();
    render(
      <DeployingInformer
        name={hostOnlyWorkload?.displayName || 'Service Workload'}
        isDeployed={true}
        isModelDeployment={false}
        workloadId={hostOnlyWorkload?.id || 'svc-2'}
        workloadData={hostOnlyWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(window.open).toHaveBeenCalledWith(
      hostOnlyWorkload?.output?.host,
      '_blank',
    );
  });

  it('does nothing if no workloadId provided', () => {
    window.open = vi.fn();
    const push = (router as any).push as any;
    render(
      <DeployingInformer
        name="No ID"
        isDeployed={true}
        isModelDeployment={false}
        workloadId=""
        workloadData={inferenceWorkload}
        t={t as any}
      />,
    );
    fireEvent.click(
      screen.getByText('deployModal.deploymentStatus.launchButtonReady'),
    );
    expect(push).not.toHaveBeenCalled();
    expect(window.open).not.toHaveBeenCalled();
  });
});
