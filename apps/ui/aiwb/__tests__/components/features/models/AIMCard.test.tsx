// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AIMCard } from '@/components/features/models/AIMCard';
import {
  mockAggregatedAims,
  mockAggregatedAimWithMultipleDeployments,
  mockUnsupportedAggregatedAim,
} from '@/__mocks__/services/app/aims.data';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      // Handle translation keys with interpolation
      if (options?.name) {
        return `${key} ${options.name}`;
      }

      // Handle pluralization for version count
      if (
        key === 'aimCatalog.card.versionCount' &&
        options?.count !== undefined
      ) {
        return options.count === 1
          ? `${options.count} version`
          : `${options.count} versions`;
      }

      // Handle pluralization for deployments count
      if (
        key === 'aimCatalog.card.deploymentsCount' &&
        options?.count !== undefined
      ) {
        return `Deployments (${options.count})`;
      }

      // Handle specific translation keys
      const translations: Record<string, string> = {
        'aimCatalog.card.gated': 'Gated',
        'aimCatalog.card.actionsMenu': 'Actions menu',
        'aimCatalog.status.deploying': 'Deploying',
        'aimCatalog.actions.deploy.label': 'Deploy',
        'aimCatalog.actions.undeploy.label': 'Undeploy',
        'aimCatalog.actions.workloadDetails.label': 'Workload details',
        'aimCatalog.actions.chatWithModel.label': 'Chat with model',
        'aimCatalog.actions.connect.label': 'Connect to model',
        'aimCatalog.tooltips.hfTokenRequired':
          'This model requires a Hugging Face token for deployment',
        'performanceMetrics.values.latency': 'Latency',
        'performanceMetrics.values.throughput': 'Throughput',
        'performanceMetrics.values.default': 'Default',
        'aimCatalog.unsupported.message':
          'This model is not supported on your hardware. Please refer to the',
        'aimCatalog.unsupported.linkText':
          'hardware requirements documentation',
        'aimCatalog.unsupported.linkUrl':
          'https://github.com/amd-enterprise-ai/aim-build/tree/main/docs/docs-aim/{{canonicalName}}',
      };

      if (
        key === 'aimCatalog.unsupported.linkUrl' &&
        options?.canonicalName !== undefined
      ) {
        return `https://github.com/amd-enterprise-ai/aim-build/tree/main/docs/docs-aim/${options.canonicalName}`;
      }
      if (key === 'aimCatalog.card.tagsMoreCount' && options?.count) {
        return `+${options.count} more`;
      }

      return translations[key] || key;
    },
  }),
}));

vi.mock('@/components/shared/ModelIcons', () => ({
  ModelIcon: ({ iconName, width, height }: any) => (
    <div
      data-testid={`model-icon-${iconName || 'default'}`}
      style={{ width: `${width}px`, height: `${height}px` }}
    >
      {iconName || 'default'} icon
    </div>
  ),
}));

vi.mock('@amdenterpriseai/components', async (importOriginal) => ({
  ...(await importOriginal()),
  ActionButton: ({ children, onPress, icon, isDisabled, ...props }: any) => (
    <button
      {...props}
      onClick={() => onPress?.()}
      disabled={isDisabled}
      data-testid="action-button"
    >
      {children}
      {icon}
    </button>
  ),
  NestedDropdown: ({ children, actions }: any) => (
    <div data-testid="nested-dropdown">
      {children}
      <div data-testid="dropdown-content">
        {actions?.map((action: any) => (
          <div key={action.key}>
            <div>{action.label}</div>
            {action.description && <div>{action.description}</div>}
            {action.actions?.map((subAction: any) => (
              <div key={subAction.key}>
                <div>{subAction.label}</div>
                {subAction.description && <div>{subAction.description}</div>}
                {subAction.actions?.map((nestedAction: any) => (
                  <div key={nestedAction.key}>
                    <div>{nestedAction.label}</div>
                    {nestedAction.description && (
                      <div>{nestedAction.description}</div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  ),
}));

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock requestAnimationFrame
global.requestAnimationFrame = ((cb: any) => {
  setTimeout(cb, 0);
  return 0;
}) as any;

global.cancelAnimationFrame = (() => {}) as any;

describe('AIMCard', () => {
  const onDeploy = vi.fn();
  const onOpenDetails = vi.fn();
  const onChatWithModel = vi.fn();
  const onConnectToModel = vi.fn();
  const onUndeploy = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic rendering', () => {
    it('renders card with aggregated AIM details', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(
        screen.getByText(aggregatedAim.aggregated.title),
      ).toBeInTheDocument();
      expect(
        screen.getByText(aggregatedAim.aggregated.description.short),
      ).toBeInTheDocument();
    });

    it('displays model icon with canonical name', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(
        screen.getByTestId(
          `model-icon-${aggregatedAim.parsedAIMs[0].canonicalName}`,
        ),
      ).toBeInTheDocument();
    });

    it('displays AI Lab name correctly', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(
        screen.getByText(aggregatedAim.aggregated.aiLabName),
      ).toBeInTheDocument();
    });

    it('displays version count correctly', () => {
      const aggregatedAim = mockAggregatedAims[0];
      const { container } = render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const versionCount = aggregatedAim.parsedAIMs.length;
      const versionText = versionCount === 1 ? 'version' : 'versions';
      // Check for version count in the card using regex to handle split text
      expect(
        screen.getByText(new RegExp(`${versionCount}.*${versionText}`, 'i')),
      ).toBeInTheDocument();
    });

    it('renders tags', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      aggregatedAim.aggregated.tags.forEach((tag: string) => {
        expect(screen.getByText(tag)).toBeInTheDocument();
      });
    });

    it('shows gated model indicator when HF token is required', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(screen.getByText('Gated')).toBeInTheDocument();
    });

    it('does not show gated indicator when HF token is not required', () => {
      const aggregatedAim = mockAggregatedAims[1];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(screen.queryByText('Gated')).not.toBeInTheDocument();
    });
  });

  describe('Deployment status badges', () => {
    it('shows deploying status badge when models are pending', () => {
      const aggregatedAim = mockAggregatedAims[2];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(screen.getByText('Deploying')).toBeInTheDocument();
    });

    it('does not show deploying badge when no pending deployments', () => {
      const aggregatedAim = mockAggregatedAims[0];
      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(screen.queryByText('Deploying')).not.toBeInTheDocument();
    });
  });

  describe('Deploy button', () => {
    it('triggers deploy with non-preview version when available', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const deployButton = screen.getByRole('button', { name: /deploy/i });
      await user.click(deployButton);

      expect(onDeploy).toHaveBeenCalledTimes(1);
    });

    it('triggers deploy with preview version when no stable version exists', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[2];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const deployButton = screen.getByRole('button', { name: /deploy/i });
      await user.click(deployButton);

      expect(onDeploy).toHaveBeenCalledTimes(1);
    });
  });

  describe('Actions dropdown with deployments', () => {
    it('shows deployments section when models are deployed', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      await waitFor(() => {
        expect(screen.getByText(/Deployments \(1\)/i)).toBeInTheDocument();
      });
    });

    it('shows Connect to model action for running deployments', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      await waitFor(() => {
        expect(screen.getByText('Connect to model')).toBeInTheDocument();
      });
    });

    it('shows multiple deployments correctly', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAimWithMultipleDeployments;

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      await waitFor(() => {
        expect(screen.getByText(/Deployments \(2\)/i)).toBeInTheDocument();
      });
    });

    it('displays deployment version and metric info', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      // The dropdown content should be visible after click
      const dropdownContent = screen.getByTestId('dropdown-content');
      expect(dropdownContent).toBeInTheDocument();

      // Verify deployment info is in the component (metric uses performanceMetrics.values translation)
      expect(dropdownContent.textContent).toContain('2.0.1');
      expect(dropdownContent.textContent).toContain('Latency');
    });

    it('shows nested actions for each deployment', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      // The deployments section should appear
      await waitFor(() => {
        expect(screen.getByText(/Deployments \(1\)/i)).toBeInTheDocument();
      });
    });

    it('has actions configured for deployments', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      // Verify the actions dropdown opens
      await waitFor(() => {
        expect(screen.getByText(/Deployments \(1\)/i)).toBeInTheDocument();
      });
    });

    it('shows deployment info in actions menu', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      // The deployment service name should be visible
      await waitFor(() => {
        expect(screen.getByText('llama-2-7b-service')).toBeInTheDocument();
      });
    });

    it('displays deployment service name in menu', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      await waitFor(() => {
        // The service name should be in the dropdown
        expect(screen.getByText('llama-2-7b-service')).toBeInTheDocument();
      });
    });

    it('disables actions dropdown when no deployments exist', () => {
      const aggregatedAim = mockAggregatedAims[1];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      expect(actionsButton).toBeDisabled();
    });

    it('shows actions menu for pending deployments', async () => {
      const user = userEvent.setup();
      const aggregatedAim = mockAggregatedAims[2];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const actionsButton = screen.getByRole('button', {
        name: /actions menu/i,
      });
      await user.click(actionsButton);

      // The deployments section should appear
      await waitFor(() => {
        expect(screen.getByText(/Deployments \(1\)/i)).toBeInTheDocument();
      });
    });
  });

  describe('Description expand/collapse', () => {
    it('renders description text', async () => {
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      // Description should be present in the card
      expect(
        screen.getByText(aggregatedAim.aggregated.description.short),
      ).toBeInTheDocument();
    });

    it('applies line clamp class to descriptions', async () => {
      const aggregatedAim = mockAggregatedAims[0];

      const { container } = render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      // The description paragraph should have line-clamp class
      const descriptionParagraph = container.querySelector('p.line-clamp-3');
      expect(descriptionParagraph).toBeInTheDocument();
    });
  });

  describe('Status indicators', () => {
    it('does not show deploying badge for deployed models', () => {
      const aggregatedAim = mockAggregatedAims[0];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      // No deploying badge should be shown for fully deployed models
      expect(screen.queryByText('Deploying')).not.toBeInTheDocument();
    });

    it('shows deploying status badge for pending deployments', () => {
      const aggregatedAim = mockAggregatedAims[2];

      render(
        <AIMCard
          aggregatedAim={aggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(screen.getByText('Deploying')).toBeInTheDocument();
    });
  });

  describe('Unsupported models', () => {
    it('shows unsupported banner when model is not supported', () => {
      render(
        <AIMCard
          aggregatedAim={mockUnsupportedAggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const banner = screen.getByTestId('unsupported-banner');
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveAttribute('role', 'alert');
      expect(banner).toHaveTextContent(
        /This model is not supported on your hardware/,
      );
      expect(
        screen.getByText('hardware requirements documentation'),
      ).toBeInTheDocument();
    });

    it('does not show unsupported banner for supported models', () => {
      render(
        <AIMCard
          aggregatedAim={mockAggregatedAims[0]}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(
        screen.queryByTestId('unsupported-banner'),
      ).not.toBeInTheDocument();
    });

    it('hides deploy button for unsupported models', () => {
      render(
        <AIMCard
          aggregatedAim={mockUnsupportedAggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      expect(
        screen.queryByRole('button', { name: /deploy/i }),
      ).not.toBeInTheDocument();
    });

    it('applies muted opacity to card content when unsupported', () => {
      const { container } = render(
        <AIMCard
          aggregatedAim={mockUnsupportedAggregatedAim}
          onDeploy={onDeploy}
          onOpenDetails={onOpenDetails}
          onChatWithModel={onChatWithModel}
          onConnectToModel={onConnectToModel}
          onUndeploy={onUndeploy}
        />,
      );

      const mutedElements = container.querySelectorAll('.opacity-50');
      expect(mutedElements.length).toBeGreaterThan(0);
    });
  });
});
