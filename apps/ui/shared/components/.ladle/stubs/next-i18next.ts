// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Stub for next-i18next in Ladle environment.
// Returns friendly fallbacks for known keys so components (e.g. StatisticsCard) render readably.
import React, {
  type ComponentType,
  type ElementType,
  type ReactNode,
} from 'react';

const fallbacks: Record<string, string> = {
  'statistics.noData': 'No data',
  'statistics.upperLimitPrefix': 'out of',
};

export const useTranslation = (ns?: string) => ({
  t: (key: string, opts?: Record<string, unknown>) => fallbacks[key] ?? key,
  i18n: {
    language: 'en',
    changeLanguage: () => Promise.resolve(),
  },
  ready: true,
});

type TransProps = {
  children?: ReactNode;
  parent?: ElementType | false;
};

export const Trans = ({ children, parent = 'span' }: TransProps) => {
  if (parent === false) {
    return children ?? null;
  }
  return React.createElement(parent, null, children);
};

export const appWithTranslation = (Component: ComponentType) => Component;
export const serverSideTranslations = () => Promise.resolve({});
