// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { useForm, FormProvider } from 'react-hook-form';
import { vi } from 'vitest';

import { AutoscalingFormFields } from '@/components/features/models/AutoscalingFormFields';
import { DEFAULT_AUTOSCALING, AIM_MAX_REPLICAS } from '@/lib/app/aims';
import type { AutoscalingFieldValues } from '@/lib/app/aims';
import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Helper component to wrap AutoscalingFormFields with form context
const FormWrapper = ({
  defaultValues = DEFAULT_AUTOSCALING,
  children,
}: {
  defaultValues?: AutoscalingFieldValues;
  children?: React.ReactNode;
}) => {
  const form = useForm<AutoscalingFieldValues>({
    defaultValues,
  });

  return (
    <FormProvider {...form}>
      <AutoscalingFormFields form={form} />
      {children}
    </FormProvider>
  );
};

describe('AutoscalingFormFields', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Exports', () => {
    it('exports MAX_REPLICAS_LIMIT constant', () => {
      expect(AIM_MAX_REPLICAS).toBe(30);
    });

    it('exports DEFAULT_AUTOSCALING_VALUES with correct defaults', () => {
      expect(DEFAULT_AUTOSCALING).toEqual({
        minReplicas: 1,
        maxReplicas: 3,
        metricQuery: 'vllm:num_requests_running',
        operationOverTime: 'avg',
        targetType: 'Value',
        targetValue: 10,
      });
    });

    it('DEFAULT_AUTOSCALING_VALUES contains correct min/max replicas', () => {
      expect(DEFAULT_AUTOSCALING.minReplicas).toBe(1);
      expect(DEFAULT_AUTOSCALING.maxReplicas).toBe(3);
    });
  });

  describe('Rendering', () => {
    it('renders replica range section', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getByText('replicaRange')).toBeInTheDocument();
    });

    it('renders replica range slider with correct label', () => {
      render(<FormWrapper />, { wrapper });

      // Range slider has two handles (min and max)
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBe(2);
    });

    it('renders scaling metric select', () => {
      render(<FormWrapper />, { wrapper });

      // HeroUI may render labels multiple times (visible + aria)
      expect(screen.getAllByText('scalingMetric.label').length).toBeGreaterThan(
        0,
      );
    });

    it('renders aggregation select', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getAllByText('aggregation.label').length).toBeGreaterThan(
        0,
      );
    });

    it('renders target type select', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getAllByText('targetType.label').length).toBeGreaterThan(0);
    });

    it('renders target value input', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getAllByText('targetValue.label').length).toBeGreaterThan(
        0,
      );
    });

    it('displays default replica range', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getByText('1 - 3')).toBeInTheDocument();
    });

    it('displays custom replica range when provided', () => {
      render(
        <FormWrapper
          defaultValues={{
            ...DEFAULT_AUTOSCALING,
            minReplicas: 2,
            maxReplicas: 10,
          }}
        />,
        { wrapper },
      );

      expect(screen.getByText('2 - 10')).toBeInTheDocument();
    });
  });

  describe('Form Field Descriptions', () => {
    it('shows scaling metric description', () => {
      render(<FormWrapper />, { wrapper });

      expect(
        screen.getByText('scalingMetric.descriptions.runningRequests'),
      ).toBeInTheDocument();
    });

    it('shows aggregation description', () => {
      render(<FormWrapper />, { wrapper });

      expect(screen.getByText('aggregation.description')).toBeInTheDocument();
    });

    it('shows target value description for Value type', () => {
      render(<FormWrapper />, { wrapper });

      expect(
        screen.getByText('targetValue.descriptions.value'),
      ).toBeInTheDocument();
    });

    it('shows target value description for AverageValue type', () => {
      render(
        <FormWrapper
          defaultValues={{
            ...DEFAULT_AUTOSCALING,
            targetType: 'AverageValue',
          }}
        />,
        { wrapper },
      );

      expect(
        screen.getByText('targetValue.descriptions.averageValue'),
      ).toBeInTheDocument();
    });
  });

  describe('Custom className', () => {
    it('applies custom className when provided', () => {
      const FormWrapperWithCustomClass = () => {
        const form = useForm<AutoscalingFieldValues>({
          defaultValues: DEFAULT_AUTOSCALING,
        });
        return (
          <FormProvider {...form}>
            <AutoscalingFormFields form={form} className="custom-test-class" />
          </FormProvider>
        );
      };

      const { container } = render(<FormWrapperWithCustomClass />, { wrapper });

      expect(container.querySelector('.custom-test-class')).toBeInTheDocument();
    });

    it('uses default className when not provided', () => {
      const { container } = render(<FormWrapper />, { wrapper });

      // Default class is applied via className prop
      const formContainer = container.querySelector('.flex.flex-col.gap-4');
      expect(formContainer).toBeInTheDocument();
    });
  });

  describe('Target Value Input', () => {
    it('renders target value input with number type', () => {
      render(<FormWrapper />, { wrapper });

      const input = screen.getByRole('spinbutton');
      expect(input).toHaveAttribute('type', 'number');
    });

    it('has minimum value of 1', () => {
      render(<FormWrapper />, { wrapper });

      const input = screen.getByRole('spinbutton');
      expect(input).toHaveAttribute('min', '1');
    });
  });
});
