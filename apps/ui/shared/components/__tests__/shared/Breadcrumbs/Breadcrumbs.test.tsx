// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { BreadcrumbItem, Breadcrumbs } from '@amdenterpriseai/components';

describe('Breadcrumbs adapter', () => {
  it('re-exports HeroUI Breadcrumbs and BreadcrumbItem', () => {
    expect(Breadcrumbs).toBeDefined();
    expect(BreadcrumbItem).toBeDefined();
  });

  it('exposes Breadcrumbs.Item compound sub-component', () => {
    expect(Breadcrumbs.Item).toBe(BreadcrumbItem);
  });

  it('renders breadcrumb trail with flat imports', () => {
    render(
      <Breadcrumbs aria-label="Trail">
        <BreadcrumbItem href="/home">Home</BreadcrumbItem>
        <BreadcrumbItem>Current</BreadcrumbItem>
      </Breadcrumbs>,
    );

    expect(
      screen.getByRole('navigation', { name: 'Trail' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute(
      'href',
      '/home',
    );
    expect(screen.getByText('Current')).toBeInTheDocument();
  });

  it('supports compound Breadcrumbs.Item syntax', () => {
    render(
      <Breadcrumbs aria-label="Compound trail">
        <Breadcrumbs.Item href="/projects">Projects</Breadcrumbs.Item>
        <Breadcrumbs.Item>Details</Breadcrumbs.Item>
      </Breadcrumbs>,
    );

    expect(
      screen.getByRole('navigation', { name: 'Compound trail' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Projects' })).toHaveAttribute(
      'href',
      '/projects',
    );
    expect(screen.getByText('Details')).toBeInTheDocument();
  });
});
