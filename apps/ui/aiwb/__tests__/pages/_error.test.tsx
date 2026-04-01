// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';
import Error, { getStaticProps } from '@/pages/_error';
import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { NextPageContext } from 'next';

// Mock next/router
vi.mock('next/router', () => ({
  useRouter: () => ({
    pathname: '/error',
    route: '/error',
    query: {},
    asPath: '/error',
    push: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(() => console.log('Router reload called')),
    prefetch: vi.fn(),
    back: vi.fn(),
    beforePopState: vi.fn(),
    events: {
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
    },
  }),
}));

// Mock serverSideTranslations
vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn().mockResolvedValue({
    common: {
      error: 'Error',
    },
  }),
}));

describe('Error Page', () => {
  it('should render error component', () => {
    const errorMessage = 'Test error message';

    const { container } = render(<Error error={errorMessage} />, {
      wrapper,
    });

    expect(container).toBeTruthy();
    // Check that the error page structure is rendered
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });

  it('should render refresh button', () => {
    render(<Error error="Test error" />, {
      wrapper,
    });

    // Should have buttons rendered (both show details and refresh)
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
  });

  it('should handle show details button interaction', () => {
    render(<Error error="Test error for details" />, {
      wrapper,
    });

    // Get the first button (show details button)
    const buttons = screen.getAllByRole('button');
    const showDetailsButton = buttons[0];

    // Click the show details button
    fireEvent.click(showDetailsButton);

    // The button should still be there after click
    expect(showDetailsButton).toBeInTheDocument();
  });

  describe('getStaticProps', () => {
    it('should return props with error message when err is provided', async () => {
      const mockContext: Partial<NextPageContext> = {
        locale: 'en',
        err: {
          name: 'Test Error',
          message: 'Test error message',
          stack: 'Test stack',
        },
      };

      const result = await getStaticProps(mockContext as NextPageContext);

      expect(result).toEqual({
        props: {
          error: 'Test error message',
        },
      });
    });

    it('should return default error message when no err is provided', async () => {
      const mockContext: Partial<NextPageContext> = {
        locale: 'en',
        err: undefined,
      };

      const result = await getStaticProps(mockContext as NextPageContext);

      expect(result).toEqual({
        props: {
          error: 'An unknown error occurred',
        },
      });
    });

    it('should use default locale when locale is not provided', async () => {
      const mockContext: Partial<NextPageContext> = {
        locale: undefined,
        err: {
          name: 'Test Error',
          message: 'Test error message',
          stack: 'Test stack',
        },
      };

      const result = await getStaticProps(mockContext as NextPageContext);

      expect(result).toEqual({
        props: {
          error: 'Test error message',
        },
      });
    });
  });
});
