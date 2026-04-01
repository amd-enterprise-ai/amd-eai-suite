// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { ProjectSelectPrompt } from '@/components/ProjectSelect/ProjectSelectPrompt';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock HeroMessage component
vi.mock('@amdenterpriseai/components', () => ({
  HeroMessage: ({ icon: Icon, title, description, endContent }: any) => (
    <div data-testid="hero-message">
      {Icon && <Icon data-testid="hero-icon" />}
      <h1>{title}</h1>
      <p>{description}</p>
      {endContent && <div data-testid="hero-end-content">{endContent}</div>}
    </div>
  ),
}));

// Mock ProjectSelect component
vi.mock('@/components/ProjectSelect/ProjectSelect', () => ({
  ProjectSelect: ({ size, showTooltip }: any) => (
    <div
      data-testid="project-select"
      data-size={size}
      data-show-tooltip={showTooltip}
    >
      Project Select
    </div>
  ),
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', () => ({
  IconCheckupList: (props: any) => (
    <div data-testid="checkup-list-icon" {...props}>
      Checkup List Icon
    </div>
  ),
}));

describe('ProjectSelectPrompt', () => {
  it('should render the component', () => {
    render(<ProjectSelectPrompt />);

    expect(screen.getByTestId('hero-message')).toBeInTheDocument();
  });

  it('should render with correct icon', () => {
    render(<ProjectSelectPrompt />);

    expect(screen.getByTestId('hero-icon')).toBeInTheDocument();
  });

  it('should render with correct translation keys', () => {
    render(<ProjectSelectPrompt />);

    expect(screen.getByText('projectSelectPrompt.title')).toBeInTheDocument();
    expect(
      screen.getByText('projectSelectPrompt.description'),
    ).toBeInTheDocument();
  });

  it('should render ProjectSelect with correct props', () => {
    render(<ProjectSelectPrompt />);

    const projectSelect = screen.getByTestId('project-select');
    expect(projectSelect).toBeInTheDocument();
    expect(projectSelect).toHaveAttribute('data-size', 'md');
    expect(projectSelect).toHaveAttribute('data-show-tooltip', 'false');
  });

  it('should render ProjectSelect in endContent section', () => {
    render(<ProjectSelectPrompt />);

    const endContent = screen.getByTestId('hero-end-content');
    expect(endContent).toBeInTheDocument();
    expect(endContent).toContainElement(screen.getByTestId('project-select'));
  });
});
