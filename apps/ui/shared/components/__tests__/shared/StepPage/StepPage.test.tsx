// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { vi } from 'vitest';

import { StepPageHandle, StepPageStep } from '@amdenterpriseai/types';

import { StepPage } from '@/src/StepPage/StepPage';

// StepPage calls `useTranslation('common')` and derives the default Previous /
// Next aria-labels (`actions.previous`, `actions.next`) from it. Mock
// next-i18next so the translator returns raw keys and these labels stay
// deterministic regardless of any ambient i18n setup.
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('StepPage', () => {
  const steps: StepPageStep[] = [
    {
      label: 'Step 1',
      content: <div>Step 1 Content</div>,
      nextActionLabel: 'Next 1',
    },
    {
      label: 'Step 2',
      content: <div>Step 2 Content</div>,
      nextActionLabel: 'Next 2',
    },
    {
      label: 'Step 3',
      content: <div>Step 3 Content</div>,
      hideNext: true,
    },
  ];

  const renderComponent = (props = {}) =>
    render(<StepPage steps={steps} {...props} />);

  it('renders the current step content and the stepper labels', () => {
    renderComponent();

    expect(screen.getAllByText('Step 1').length).toBeGreaterThan(0);
    expect(screen.getByText('Step 1 Content')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
    expect(screen.getByText('Step 3')).toBeInTheDocument();
  });

  it('advances to the next step when Next is pressed', () => {
    renderComponent();

    fireEvent.click(screen.getByLabelText('Next 1'));
    expect(screen.getByText('Step 2 Content')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Next 2'));
    expect(screen.getByText('Step 3 Content')).toBeInTheDocument();
  });

  it('returns to the previous step when Previous is pressed', () => {
    renderComponent({ initialStep: 1 });

    expect(screen.getByText('Step 2 Content')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('actions.previous'));
    expect(screen.getByText('Step 1 Content')).toBeInTheDocument();
  });

  it('hides Previous when allowPrevious is false', () => {
    renderComponent({ initialStep: 1, allowPrevious: false });
    expect(screen.queryByLabelText('actions.previous')).not.toBeInTheDocument();
  });

  it('hides Next on the last step', () => {
    renderComponent({ initialStep: 2 });
    expect(screen.queryByLabelText('actions.next')).not.toBeInTheDocument();
  });

  it('honors hideNext / hidePrev per step', () => {
    const customSteps: StepPageStep[] = [
      { label: 'A', content: <div>A</div>, hideNext: true },
      { label: 'B', content: <div>B</div>, hidePrev: true },
    ];

    const ref = createRef<StepPageHandle>();
    render(<StepPage ref={ref} steps={customSteps} initialStep={0} />);
    expect(screen.queryByLabelText('actions.next')).not.toBeInTheDocument();

    // `initialStep` is only consumed on mount, so drive the step change via
    // the imperative handle to actually exercise step 1's `hidePrev`.
    act(() => {
      ref.current?.setStep(1);
    });
    expect(screen.queryByLabelText('actions.previous')).not.toBeInTheDocument();
  });

  it('renders customActions in place of the default footer when provided', () => {
    const customSteps: StepPageStep[] = [
      {
        label: 'Only',
        content: <div>Only Content</div>,
        customActions: <button type="button">Submit</button>,
      },
    ];

    render(<StepPage steps={customSteps} />);

    expect(screen.getByText('Submit')).toBeInTheDocument();
    expect(screen.queryByLabelText('actions.next')).not.toBeInTheDocument();
  });

  it('exposes incrementStep / setStep via the imperative handle', () => {
    const ref = createRef<StepPageHandle>();
    render(<StepPage ref={ref} steps={steps} />);

    expect(screen.getByText('Step 1 Content')).toBeInTheDocument();

    act(() => {
      ref.current?.incrementStep();
    });
    expect(screen.getByText('Step 2 Content')).toBeInTheDocument();

    act(() => {
      ref.current?.setStep(2);
    });
    expect(screen.getByText('Step 3 Content')).toBeInTheDocument();
  });

  it('clamps setStep into the valid range so out-of-bounds values do not strand the wizard', () => {
    const ref = createRef<StepPageHandle>();
    render(<StepPage ref={ref} steps={steps} />);

    act(() => {
      ref.current?.setStep(99);
    });
    expect(screen.getByText('Step 3 Content')).toBeInTheDocument();

    act(() => {
      ref.current?.setStep(-5);
    });
    expect(screen.getByText('Step 1 Content')).toBeInTheDocument();
  });

  it('delegates step changes to onStepChange when provided', () => {
    const onStepChange = vi.fn();
    const customSteps: StepPageStep[] = [
      {
        label: 'Step 1',
        content: <div>Step 1 Content</div>,
        nextActionLabel: 'Next 1',
        onStepChange,
      },
      {
        label: 'Step 2',
        content: <div>Step 2 Content</div>,
        nextActionLabel: 'Next 2',
      },
    ];

    render(<StepPage steps={customSteps} />);

    fireEvent.click(screen.getByLabelText('Next 1'));

    expect(onStepChange).toHaveBeenCalledWith(1);
    // No automatic advancement when onStepChange owns the transition.
    expect(screen.getByText('Step 1 Content')).toBeInTheDocument();
  });
});
