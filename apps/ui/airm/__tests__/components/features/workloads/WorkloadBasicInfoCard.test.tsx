// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { WorkloadBasicInfoCard } from '@/components/features/workloads/WorkloadBasicInfoCard';

import wrapper from '@/__tests__/ProviderWrapper';

describe('WorkloadBasicInfoCard', () => {
  const defaultProps = {
    name: 'my-workload',
    workloadId: 'wl-123',
    createdBy: 'user@example.com',
  };

  it('should render the section title', () => {
    render(<WorkloadBasicInfoCard {...defaultProps} />, { wrapper });
    expect(
      screen.getByText('details.sections.basicInformation'),
    ).toBeInTheDocument();
  });

  it('should render all field labels', () => {
    render(<WorkloadBasicInfoCard {...defaultProps} />, { wrapper });
    expect(screen.getByText('details.fields.name')).toBeInTheDocument();
    expect(screen.getByText('details.fields.workloadId')).toBeInTheDocument();
    expect(screen.getByText('details.fields.createdBy')).toBeInTheDocument();
  });

  it('should render the provided values', () => {
    render(<WorkloadBasicInfoCard {...defaultProps} />, { wrapper });
    expect(screen.getByText('my-workload')).toBeInTheDocument();
    expect(screen.getByText('wl-123')).toBeInTheDocument();
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
  });
});
