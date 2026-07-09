// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ReactNode } from 'react';

export type StepPageStep = {
  label: string;
  content: ReactNode;
  /**
   * Replaces the default Previous/Next footer for this step.
   * When provided, `hideNext`, `hidePrev`, `nextActionLabel`, and
   * `backActionLabel` are ignored.
   */
  customActions?: ReactNode;
  nextActionLabel?: string;
  backActionLabel?: string;
  /**
   * Called instead of the internal step advance when Previous/Next is pressed.
   * Use this to gate transitions on async validation, then call
   * `setStep`/`incrementStep` on the ref once the work succeeds.
   */
  onStepChange?: (step: number) => void;
  hideNext?: boolean;
  hidePrev?: boolean;
};

export type StepPageHandle = {
  incrementStep: () => void;
  setStep: (step: number) => void;
};
