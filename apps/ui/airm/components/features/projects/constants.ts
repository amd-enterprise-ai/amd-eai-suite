// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';

export const CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS = {
  policy: GpuPreemptionPolicy.OnPressure,
  threshold: 10,
  gracePeriod: 30,
} as const;
