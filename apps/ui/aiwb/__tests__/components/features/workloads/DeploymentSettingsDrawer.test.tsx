// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, Mock } from 'vitest';

import { DeploymentSettingsDrawer } from '@/components/features/workloads/DeploymentSettingsDrawer';
import {
  updateAimScalingPolicy,
  createAimScalingPolicyConfig,
  DEFAULT_AUTOSCALING,
} from '@/lib/app/aims';
import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockAutoScalingConfig = {
  metrics: [
    {
      type: 'PodMetric' as const,
      podmetric: {
        metric: {
          backend: 'opentelemetry' as const,
          metricNames: [
            'vllm:num_requests_running',
            'vllm:num_requests_waiting',
          ],
          query: 'vllm:num_requests_waiting',
          operationOverTime: 'avg',
        },
        target: {
          type: 'AverageValue',
          value: '1',
        },
      },
    },
  ],
};

vi.mock('@/lib/app/aims', () => ({
  updateAimScalingPolicy: vi.fn(),
  createAimScalingPolicyConfig: vi.fn(() => mockAutoScalingConfig),
  AIM_MAX_REPLICAS: 30,
  DEFAULT_AUTOSCALING: {
    minReplicas: 1,
    maxReplicas: 3,
    metricQuery: 'vllm:num_requests_waiting',
    operationOverTime: 'avg',
    targetType: 'AverageValue',
    targetValue: 1,
  },
}));

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};

vi.mock('@amdenterpriseai/hooks', () => ({
  useSystemToast: () => ({
    toast: mockToast,
  }),
}));

// Mock DrawerForm to simplify testing
vi.mock('@amdenterpriseai/components', () => ({
  DrawerForm: vi.fn(
    ({
      isOpen,
      onCancel,
      onFormSuccess,
      title,
      confirmText,
      cancelText,
      isActioning,
      defaultValues,
      renderFields,
    }) => {
      if (!isOpen) return null;

      // Create a mock form object for renderFields
      const mockForm = {
        watch: vi.fn((field: string) => defaultValues[field]),
        control: {
          register: vi.fn(),
          unregister: vi.fn(),
          getFieldState: vi.fn(),
          _subjects: {
            array: {
              next: vi.fn(),
            },
          },
        },
        setValue: vi.fn(),
        register: vi.fn().mockReturnValue({}),
        formState: { errors: {} },
        getValues: vi.fn(() => defaultValues),
      };

      return (
        <div data-testid="drawer-form">
          <div data-testid="drawer-title">{title}</div>
          <div data-testid="drawer-confirm-text">{confirmText}</div>
          <div data-testid="drawer-cancel-text">{cancelText}</div>
          <div data-testid="drawer-is-actioning">
            {isActioning ? 'true' : 'false'}
          </div>
          <div data-testid="drawer-default-values">
            {JSON.stringify(defaultValues)}
          </div>
          <div data-testid="drawer-fields">{renderFields(mockForm as any)}</div>
          <button
            data-testid="submit-button"
            onClick={() => onFormSuccess(defaultValues)}
          >
            Submit
          </button>
          <button data-testid="cancel-button" onClick={onCancel}>
            Cancel
          </button>
        </div>
      );
    },
  ),
}));

// Mock AutoscalingFormFields
vi.mock('@/components/features/models/AutoscalingFormFields', () => ({
  AutoscalingFormFields: vi.fn(({ form, className }) => (
    <div data-testid="autoscaling-form-fields" className={className}>
      Autoscaling Form Fields
    </div>
  )),
}));

describe('WorkloadSettingsDrawer', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (updateAimScalingPolicy as Mock).mockResolvedValue(undefined);
  });

  describe('Rendering', () => {
    it('renders drawer when open', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByTestId('drawer-form')).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      render(
        <DeploymentSettingsDrawer isOpen={false} onClose={mockOnClose} />,
        {
          wrapper,
        },
      );

      expect(screen.queryByTestId('drawer-form')).not.toBeInTheDocument();
    });

    it('displays correct title', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByTestId('drawer-title')).toHaveTextContent(
        'settingsTitle',
      );
    });

    it('displays correct button labels', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByTestId('drawer-confirm-text')).toHaveTextContent(
        'actions.save',
      );
      expect(screen.getByTestId('drawer-cancel-text')).toHaveTextContent(
        'actions.cancel',
      );
    });

    it('renders autoscaling description', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByText('description')).toBeInTheDocument();
    });

    it('renders AutoscalingFormFields', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByTestId('autoscaling-form-fields')).toBeInTheDocument();
    });

    it('passes correct className to AutoscalingFormFields', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      const formFields = screen.getByTestId('autoscaling-form-fields');
      expect(formFields).toHaveClass('flex', 'flex-col', 'gap-5');
    });
  });

  describe('Default Values', () => {
    it('uses DEFAULT_AUTOSCALING_VALUES when no initialValues provided', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      const defaultValues = JSON.parse(
        screen.getByTestId('drawer-default-values').textContent || '{}',
      );

      expect(defaultValues).toEqual(DEFAULT_AUTOSCALING);
    });

    it('uses provided initialValues', () => {
      const customValues = {
        minReplicas: 2,
        maxReplicas: 10,
        metricQuery: 'vllm:num_requests_waiting',
        operationOverTime: 'max',
        targetType: 'AverageValue',
        targetValue: 5,
      };

      render(
        <DeploymentSettingsDrawer
          isOpen={true}
          onClose={mockOnClose}
          initialValues={customValues}
        />,
        { wrapper },
      );

      const defaultValues = JSON.parse(
        screen.getByTestId('drawer-default-values').textContent || '{}',
      );

      expect(defaultValues).toEqual(customValues);
    });
  });

  describe('Form Submission', () => {
    it('calls updateWorkloadScaling on submit with workloadId', async () => {
      render(
        <DeploymentSettingsDrawer
          isOpen={true}
          onClose={mockOnClose}
          namespace="test-namespace"
          id="test-workload-123"
        />,
        { wrapper },
      );

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(createAimScalingPolicyConfig).toHaveBeenCalledWith({
          metricQuery: DEFAULT_AUTOSCALING.metricQuery,
          operationOverTime: DEFAULT_AUTOSCALING.operationOverTime,
          targetType: DEFAULT_AUTOSCALING.targetType,
          targetValue: DEFAULT_AUTOSCALING.targetValue,
        });
        expect(updateAimScalingPolicy).toHaveBeenCalledWith(
          'test-namespace',
          'test-workload-123',
          {
            minReplicas: DEFAULT_AUTOSCALING.minReplicas,
            maxReplicas: DEFAULT_AUTOSCALING.maxReplicas,
            autoScaling: mockAutoScalingConfig,
          },
        );
      });
    });

    it('shows error toast when workloadId is missing', async () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        // Should show error toast for missing workloadId
        expect(mockToast.error).toHaveBeenCalledWith(
          'notifications.noWorkloadId',
        );
      });

      // Should not call updateWorkloadScaling without workloadId
      expect(updateAimScalingPolicy).not.toHaveBeenCalled();
    });

    it('calls onClose after successful submission', async () => {
      render(
        <DeploymentSettingsDrawer
          isOpen={true}
          onClose={mockOnClose}
          namespace="test-namespace"
          id="test-workload-123"
        />,
        { wrapper },
      );

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('calls onSuccess after successful submission', async () => {
      render(
        <DeploymentSettingsDrawer
          isOpen={true}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
          namespace="test-namespace"
          id="test-workload-123"
        />,
        { wrapper },
      );

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('handles API error gracefully', async () => {
      (updateAimScalingPolicy as Mock).mockRejectedValue(
        new Error('API Error'),
      );

      render(
        <DeploymentSettingsDrawer
          isOpen={true}
          onClose={mockOnClose}
          namespace="test-namespace"
          id="test-workload-123"
        />,
        { wrapper },
      );

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);

      // Should not call onClose on error
      await waitFor(() => {
        expect(mockOnClose).not.toHaveBeenCalled();
      });
    });
  });

  describe('Cancel Action', () => {
    it('calls onClose when cancel button is clicked', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      const cancelButton = screen.getByTestId('cancel-button');
      fireEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('shows not actioning initially', () => {
      render(<DeploymentSettingsDrawer isOpen={true} onClose={mockOnClose} />, {
        wrapper,
      });

      expect(screen.getByTestId('drawer-is-actioning')).toHaveTextContent(
        'false',
      );
    });
  });
});
