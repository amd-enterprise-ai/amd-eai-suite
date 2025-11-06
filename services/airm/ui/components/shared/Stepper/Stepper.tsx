// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { cn } from '@heroui/react';

type StepperStep = {
  label: string;
  onPress?: (step: number) => void;
};

interface Props {
  className?: string;
  step: number;
  steps: StepperStep[];
}

const Stepper: React.FC<Props> = ({ step, steps, className }) => {
  return (
    <ol
      className={cn(
        'flex items-start text-xs text-slate-900 dark:text-slate-100  font-medium sm:text-base',
        className,
      )}
    >
      {steps?.map((_step, idx) => {
        return (
          <li
            key={`stepper-${idx}`}
            className={cn('flex relative', {
              "after:content-['']  after:w-full after:h-0.5  after:inline-block after:absolute lg:after:top-5 after:top-3 after:left-4":
                idx < steps.length - 1,
              'w-full': idx < steps.length - 1,
              'text-primary after:bg-primary': idx < step,
              'text-primary after:bg-slate-200 after:dark:bg-slate-800 font-bold':
                idx === step,
              'text-slate-400 dark:text-slate-500 after:bg-slate-200 after:dark:bg-slate-800':
                idx > step,
            })}
          >
            <div
              className="block whitespace-nowrap z-10"
              onClick={() => {
                if (_step.onPress) {
                  _step.onPress(idx);
                }
              }}
            >
              <span
                className={cn(
                  'w-8 h-8 border-2  rounded-full flex justify-center items-center mx-auto mb-3 text-sm text-white lg:w-10 lg:h-10',
                  {
                    'bg-primary border-transparent flex w-full relative':
                      idx < step,
                    'bg-primary-50 dark:bg-primary-950 border-primary text-primary':
                      idx === step,
                    'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500':
                      idx > step,
                  },
                )}
              >
                {idx + 1}
              </span>
              <div className="max-w-8 text-wrap text-sm">{_step.label}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
};

export default Stepper;
