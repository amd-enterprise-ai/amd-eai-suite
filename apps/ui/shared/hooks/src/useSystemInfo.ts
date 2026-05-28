// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback } from 'react';

type Platform = 'Windows' | 'Mac' | 'Linux' | 'Unknown';

const UNKNOWN = 'Unknown';

function detectPlatform(userAgent: string): Platform {
  const ua = userAgent.toLowerCase();
  if (ua.includes('win')) return 'Windows';
  if (ua.includes('mac')) return 'Mac';
  if (ua.includes('linux') || ua.includes('x11')) return 'Linux';
  return UNKNOWN;
}

// Order matters: Edge and Opera UAs also contain "Chrome", and Chrome UAs
// also contain "Safari", so more specific matchers must come first.
const BROWSER_MATCHERS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'Edge', pattern: /Edg(?:e|A|iOS)?\/(\d+)/ },
  { name: 'Opera', pattern: /(?:OPR|Opera)\/(\d+)/ },
  { name: 'Firefox', pattern: /Firefox\/(\d+)/ },
  { name: 'Chrome', pattern: /Chrome\/(\d+)/ },
  { name: 'Safari', pattern: /Version\/(\d+).*Safari/ },
];

function detectBrowser(userAgent: string): string {
  for (const { name, pattern } of BROWSER_MATCHERS) {
    const match = userAgent.match(pattern);
    if (match) return `${name} ${match[1]}`;
  }
  return UNKNOWN;
}

function collectSystemInfo(): string[] {
  if (typeof window === 'undefined') return [];
  const version = process.env.NEXT_PUBLIC_BUILD_VERSION || UNKNOWN;
  const platform = detectPlatform(navigator.userAgent);
  const browser = detectBrowser(navigator.userAgent);
  return [
    `Version: ${version}`,
    `Platform: ${platform}`,
    `Browser: ${browser}`,
    `URL: ${window.location.href}`,
  ];
}

/**
 * Returns a stable getter that produces a formatted list of "Label: value"
 * lines describing the current runtime: build version, OS platform, browser,
 * and current URL.
 *
 * The returned array is designed to be spread directly into a
 * `createMailtoLink` body so a support email can include diagnostic context.
 *
 * SSR-safe: the getter returns an empty array on the server. On the client
 * it reads live values from `navigator` / `window` at call time, so callers
 * always see up-to-date info (e.g. current URL after client-side navigation)
 * without any race against `useEffect`.
 */
export const useSystemInfo = (): (() => string[]) =>
  useCallback(() => collectSystemInfo(), []);
