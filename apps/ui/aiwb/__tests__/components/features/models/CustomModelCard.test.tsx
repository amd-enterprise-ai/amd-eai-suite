// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CustomModelCard } from '@/components/features/models/CustomModelCard';
import { mockAggregatedAims } from '@/__mocks__/services/app/aims.data';
import { AggregatedAIM } from '@/types/aims';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (
        key === 'aimCatalog.card.versionCount' &&
        typeof options?.count === 'number'
      ) {
        return options.count === 1
          ? `${options.count} version`
          : `${options.count} versions`;
      }
      if (
        key === 'customModels.card.tagsMoreCount' &&
        typeof options?.count === 'number'
      ) {
        return `+${options.count}`;
      }
      return key;
    },
  }),
}));

vi.mock('@amdenterpriseai/components', async (importOriginal) => ({
  ...(await importOriginal()),
  // Render dropdown actions inline so the test can interact with them
  // without going through HeroUI's portalled menu.
  NestedDropdown: ({
    children,
    actions,
  }: {
    children: React.ReactNode;
    actions: { key: string; label: string; onPress: () => void }[];
  }) => (
    <div data-testid="nested-dropdown">
      {children}
      <div data-testid="dropdown-content">
        {actions.map((action) => (
          <button
            key={action.key}
            data-testid={`menu-item-${action.key}`}
            onClick={() => action.onPress()}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  ),
}));

const baseAim: AggregatedAIM = mockAggregatedAims[0];

/** baseAim with a specific composed onboard phase (deployability gates on this). */
const withPhase = (
  onboardPhase: AggregatedAIM['aggregated']['onboardPhase'],
): AggregatedAIM => ({
  ...baseAim,
  aggregated: { ...baseAim.aggregated, onboardPhase },
});

const readyAim = withPhase('Ready');

describe('CustomModelCard', () => {
  const handlers = {
    onModelSettings: vi.fn(),
    onDelete: vi.fn(),
    onDeploy: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the action menu items (settings, delete)', () => {
    render(<CustomModelCard aggregatedAim={baseAim} {...handlers} />);

    expect(screen.getByTestId('menu-item-settings')).toHaveTextContent(
      'customModels.card.actions.settings.label',
    );
    expect(screen.getByTestId('menu-item-delete')).toHaveTextContent(
      'customModels.card.actions.delete.label',
    );
  });

  it('invokes the matching handler when an action is selected', () => {
    render(<CustomModelCard aggregatedAim={baseAim} {...handlers} />);

    fireEvent.click(screen.getByTestId('menu-item-settings'));
    expect(handlers.onModelSettings).toHaveBeenCalledWith(baseAim);

    fireEvent.click(screen.getByTestId('menu-item-delete'));
    expect(handlers.onDelete).toHaveBeenCalledWith(baseAim);
  });

  it('routes the Deploy button click to onDeploy when the model is Ready', () => {
    render(<CustomModelCard aggregatedAim={readyAim} {...handlers} />);

    fireEvent.click(screen.getByTestId('custom-model-card-deploy'));

    expect(handlers.onDeploy).toHaveBeenCalledWith(readyAim);
  });

  it('enables Deploy and shows no status pill when the model is Ready', () => {
    render(<CustomModelCard aggregatedAim={readyAim} {...handlers} />);

    expect(screen.getByTestId('custom-model-card-deploy')).toBeEnabled();
    expect(
      screen.queryByText('customModels.card.status.failed'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('customModels.card.status.importing'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('customModels.card.status.onboarding'),
    ).not.toBeInTheDocument();
  });

  it('shows Importing status pill and disables Deploy while weights are being imported', () => {
    render(
      <CustomModelCard aggregatedAim={withPhase('Importing')} {...handlers} />,
    );

    expect(screen.getByTestId('custom-model-card-deploy')).toBeDisabled();
    expect(
      screen.getByText('customModels.card.status.importing'),
    ).toBeInTheDocument();
  });

  it('shows Failed status pill and disables Deploy when onboarding failed', () => {
    // The bug guard: a failed weight import composes to phase 'Failed' even
    // when an AIMProfile exists. The card must surface the failure and keep
    // Deploy disabled so the user cannot deploy a model with missing weights.
    render(
      <CustomModelCard aggregatedAim={withPhase('Failed')} {...handlers} />,
    );

    expect(screen.getByTestId('custom-model-card-deploy')).toBeDisabled();
    expect(
      screen.getByText('customModels.card.status.failed'),
    ).toBeInTheDocument();
  });

  it('shows Onboarding status pill and disables Deploy for Pending phase', () => {
    render(
      <CustomModelCard aggregatedAim={withPhase('Pending')} {...handlers} />,
    );

    expect(screen.getByTestId('custom-model-card-deploy')).toBeDisabled();
    expect(
      screen.getByText('customModels.card.status.onboarding'),
    ).toBeInTheDocument();
  });
});
