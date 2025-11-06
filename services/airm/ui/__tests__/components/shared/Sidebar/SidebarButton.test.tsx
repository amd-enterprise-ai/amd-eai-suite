// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render } from '@testing-library/react';

import { SidebarButton } from '@/components/shared/Navigation/SidebarButton';

import '@testing-library/jest-dom';

describe('SidebarButton', () => {
  const mockHref = '/example';

  it('should render link with text and icon when href is provided', () => {
    const { getByText, getByRole } = render(
      <SidebarButton
        isSidebarMini={true}
        text="Button Text"
        icon={<span>Icon</span>}
        href={mockHref}
      />,
    );

    const link = getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveTextContent('Button Text');
    expect(getByText('Icon')).toBeInTheDocument();
    expect(link).toHaveAttribute('href', mockHref);
  });
});
