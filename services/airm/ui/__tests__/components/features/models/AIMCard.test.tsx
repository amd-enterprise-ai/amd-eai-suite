// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { AIMCard } from '@/components/features/models/AIMCard';
import { mockAims } from '@/__mocks__/services/app/aims.data';
import { WorkloadStatus } from '@/types/enums/workloads';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/components/shared/ModelIcons', () => ({
  ModelIcon: ({ iconName, width, height }: any) => (
    <div
      data-testid={`model-icon-${iconName || 'default'}`}
      style={{ width: `${width}px`, height: `${height}px` }}
    >
      {iconName || 'default'} icon
    </div>
  ),
}));

describe('AIMCard', () => {
  const onDeploy = vi.fn();
  const onUndeploy = vi.fn();
  const onConnect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders card with AIM details', () => {
    const aim = mockAims[0];
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    expect(screen.getByText(aim.title)).toBeInTheDocument();
    expect(screen.getByText(aim.imageTag)).toBeInTheDocument();
    expect(screen.getByText(aim.description.short)).toBeInTheDocument();
  });

  it('shows deployed status for deployed workload', () => {
    const aim = mockAims[0];
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    expect(screen.getByText('status.deployed')).toBeInTheDocument();
  });

  it('shows pending status for pending workload', () => {
    const aim = mockAims[2];
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    expect(screen.getByText('status.deploying')).toBeInTheDocument();
  });

  it('shows undeploying status for deleting workload', () => {
    const aim = {
      ...mockAims[0],
      workload: {
        ...mockAims[0].workload!,
        status: WorkloadStatus.DELETING,
      },
    };
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    expect(screen.getByText('status.undeploying')).toBeInTheDocument();
  });

  it('renders preview chip when isPreview is true', () => {
    const aim = mockAims[2];
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('renders tags', () => {
    const aim = mockAims[0];
    render(
      <AIMCard
        item={aim}
        onDeploy={onDeploy}
        onUndeploy={onUndeploy}
        onConnect={onConnect}
      />,
    );

    aim.tags.forEach((tag: string) => {
      expect(screen.getByText(tag)).toBeInTheDocument();
    });
  });
});
