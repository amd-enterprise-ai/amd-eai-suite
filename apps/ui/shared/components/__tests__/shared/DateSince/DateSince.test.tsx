// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { DateSince } from '@amdenterpriseai/components';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouter } from 'next/router';

const mockFormatDistance = vi.fn();
const mockFormatRelative = vi.fn();
const mockDifferenceInCalendarDays = vi.fn();

vi.mock('date-fns', () => ({
  differenceInCalendarDays: (...args: unknown[]) =>
    mockDifferenceInCalendarDays(...args),
  format: (d: Date, _f: string) =>
    d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }),
  formatDistance: (...args: unknown[]) => mockFormatDistance(...args),
  formatRelative: (...args: unknown[]) => mockFormatRelative(...args),
}));

vi.mock('date-fns/locale', () => ({
  enUS: {},
}));

vi.mock('next/router', () => ({
  useRouter: vi.fn(() => ({ locale: 'en' })),
}));

vi.mock('@heroui/react', async () => {
  const actual =
    await vi.importActual<typeof import('@heroui/react')>('@heroui/react');
  return {
    ...actual,
    Tooltip: ({
      children,
      content,
    }: {
      children: React.ReactNode;
      content: React.ReactNode;
    }) => (
      <div data-testid="datesince-tooltip-wrapper">
        <span data-testid="datesince-trigger">{children}</span>
        <span data-testid="datesince-tooltip-content">{content}</span>
      </div>
    ),
  };
});

describe('DateSince', () => {
  const fixedDate = new Date('2025-02-24T12:00:00Z');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(fixedDate);
    mockFormatDistance.mockReset();
    mockFormatRelative.mockReset();
    mockDifferenceInCalendarDays.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('uses fallback locale when router.locale is undefined', () => {
    vi.mocked(useRouter).mockReturnValue({ locale: undefined } as any);
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('less than a minute ago');
    const date = new Date(fixedDate.getTime() - 30 * 1000);

    render(<DateSince date={date} />);

    expect(screen.getByText('less than a minute ago')).toBeInTheDocument();
  });

  it('renders formatDistance result when date is same calendar day', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('less than a minute ago');
    const date = new Date(fixedDate.getTime() - 30 * 1000);

    render(<DateSince date={date} />);

    expect(screen.getByText('less than a minute ago')).toBeInTheDocument();
  });

  it('renders "N minutes ago" when date is same day and formatDistance returns it', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('5 minutes ago');
    const date = new Date(fixedDate.getTime() - 5 * 60 * 1000);

    render(<DateSince date={date} />);

    expect(screen.getByText('5 minutes ago')).toBeInTheDocument();
  });

  it('renders "about N hours ago" when date is same day', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('about 2 hours ago');
    const date = new Date(fixedDate.getTime() - 2 * 60 * 60 * 1000);

    render(<DateSince date={date} />);

    expect(screen.getByText('about 2 hours ago')).toBeInTheDocument();
  });

  it('renders formatRelative result when date is 1 calendar day ago', () => {
    mockDifferenceInCalendarDays.mockReturnValue(1);
    mockFormatRelative.mockReturnValue('yesterday at 2:30 PM');
    const date = new Date(fixedDate.getTime() - 25 * 60 * 60 * 1000);

    render(<DateSince date={date} />);

    expect(screen.getByText('yesterday at 2:30 PM')).toBeInTheDocument();
  });

  it('renders absolute date/time when date is more than 1 calendar day ago', () => {
    mockDifferenceInCalendarDays.mockReturnValue(3);
    const date = new Date('2025-02-21T10:00:00Z');

    render(<DateSince date={date} />);

    expect(screen.getByTestId('datesince-trigger')).toHaveTextContent(/2025/);
  });

  it('shows tooltip with absolute date/time for same-day date', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('5 minutes ago');
    const date = new Date(fixedDate.getTime() - 5 * 60 * 1000);

    render(<DateSince date={date} />);

    const tooltipContent = screen.getByTestId('datesince-tooltip-content');
    expect(tooltipContent).toBeInTheDocument();
    expect(tooltipContent.textContent?.length).toBeGreaterThan(0);
  });

  it('accepts date as number timestamp', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('less than a minute ago');
    const ts = fixedDate.getTime() - 30 * 1000;

    render(<DateSince date={ts} />);

    expect(screen.getByText('less than a minute ago')).toBeInTheDocument();
  });

  it('accepts date as ISO string', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('less than a minute ago');
    const iso = new Date(fixedDate.getTime() - 30 * 1000).toISOString();

    render(<DateSince date={iso} />);

    expect(screen.getByText('less than a minute ago')).toBeInTheDocument();
  });

  it('applies className to the span', () => {
    mockDifferenceInCalendarDays.mockReturnValue(0);
    mockFormatDistance.mockReturnValue('less than a minute ago');
    const date = new Date(fixedDate.getTime() - 30 * 1000);

    render(<DateSince date={date} className="text-default-500" />);

    const trigger = screen.getByTestId('datesince-trigger');
    expect(trigger.querySelector('.text-default-500')).toBeInTheDocument();
  });
});
