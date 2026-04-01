// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ReactNode } from 'react';

export type StepModalStep = {
  label: string;
  content: ReactNode;
  customActions?: ReactNode;
  nextActionLabel?: string;
  backActionLabel?: string;
  onStepChange?: (step: number) => void;
  hideNext?: boolean;
  hidePrev?: boolean;
  canCloseByOverlayPress?: boolean;
};

export type StepModalHandle = {
  incrementStep: () => void;
  setStep: (step: number) => void;
};
