// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectGpuPreemptionReadOnly } from '@/components/features/projects/ProjectGpuPreemptionReadOnly';
import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';
import type { GpuPreemptionReadOnlyConfig } from '@/types/projects';
import { GPU_PREEMPTION_DISABLED } from '@/types/projects';
import { render, screen } from '@testing-library/react';
import type { TFunction } from 'i18next';

const t = ((key: string) => key) as unknown as TFunction;

describe('ProjectGpuPreemptionReadOnly', () => {
  it('shows info banner and disabled copy when pre-emption is off', () => {
    render(
      <ProjectGpuPreemptionReadOnly config={GPU_PREEMPTION_DISABLED} t={t} />,
    );
    expect(
      screen.getByText('modal.create.form.preemption.sectionTitle'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'settings.form.basicInfo.preemption.readonly.bannerDescriptionDisabled',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('settings.form.basicInfo.preemption.readonly.disabled'),
    ).toBeInTheDocument();
  });

  it('shows policy, idle timer, and GPU threshold when enabled', () => {
    render(
      <ProjectGpuPreemptionReadOnly
        config={{
          enabled: true,
          policy: GpuPreemptionPolicy.OnPressure,
          gracePeriod: 2700,
          threshold: 72,
        }}
        t={t}
      />,
    );
    expect(
      screen.getByText(/modal\.create\.form\.preemption\.policy\.label/),
    ).toBeInTheDocument();
    expect(
      screen.getByText('modal.create.form.preemption.policy.onPressure'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/modal\.create\.form\.preemption\.gracePeriod\.label/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/modal\.create\.form\.preemption\.threshold\.label/),
    ).toBeInTheDocument();
    expect(
      screen.getByText('45 modal.create.form.preemption.gracePeriod.suffix'),
    ).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
  });

  it('shows em dash for missing threshold when enabled (partial API payload)', () => {
    const partialEnabled: GpuPreemptionReadOnlyConfig = {
      enabled: true,
      policy: GpuPreemptionPolicy.Always,
      gracePeriod: 1800,
      threshold: null,
    };
    render(<ProjectGpuPreemptionReadOnly config={partialEnabled} t={t} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
