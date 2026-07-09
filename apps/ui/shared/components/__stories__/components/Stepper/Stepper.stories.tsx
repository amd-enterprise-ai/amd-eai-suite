// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';

import Stepper from '../../../src/Stepper/Stepper';

export default {
  title: 'Components/Stepper',
} satisfies StoryDefault;

const threeSteps = [
  { label: 'Model source' },
  { label: 'Model information' },
  { label: 'Runtime profile' },
];

export const FirstStep: Story = () => (
  <div className="w-full max-w-2xl">
    <Stepper step={0} steps={threeSteps} />
  </div>
);

export const MiddleStep: Story = () => (
  <div className="w-full max-w-2xl">
    <Stepper step={1} steps={threeSteps} />
  </div>
);

export const LastStep: Story = () => (
  <div className="w-full max-w-2xl">
    <Stepper step={2} steps={threeSteps} />
  </div>
);

export const ManySteps: Story = () => (
  <div className="w-full max-w-3xl">
    <Stepper
      step={2}
      steps={[
        { label: 'Connect' },
        { label: 'Onboard' },
        { label: 'Verify' },
        { label: 'Deploy' },
        { label: 'Finalize' },
      ]}
    />
  </div>
);

export const Interactive: Story = () => {
  const [step, setStep] = useState(0);
  return (
    <div className="flex flex-col gap-6 w-full max-w-2xl">
      <Stepper
        step={step}
        steps={threeSteps.map((s, i) => ({
          ...s,
          onPress: () => setStep(i),
        }))}
      />
      <p className="text-sm text-default-500">
        Click any step label to jump to it (current step: {step + 1}).
      </p>
    </div>
  );
};
