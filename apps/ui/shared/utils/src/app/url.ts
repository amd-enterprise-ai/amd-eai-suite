// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

const SUPPORT_EMAIL = 'amd-eai-support@amd.com';

/**
 * Returns true if the string is a valid URL with http or https scheme.
 * Use when validating user- or env-supplied URLs for safe use in links
 * or redirects (e.g. to reject javascript:, data:, etc.).
 */
export function isHttpUrl(url: string): boolean {
  const trimmed = url.trim();
  if (!trimmed) return false;
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Strips trailing slashes from a URL string.
 * Useful when concatenating a base URL with a path segment to avoid double slashes.
 */
export function stripTrailingSlashes(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

export type MailtoBody = string | string[];

export interface CreateMailtoLinkArgs {
  subject?: string;
  body?: MailtoBody;
}

/**
 * Builds a `mailto:` link targeting the support email, with optional
 * subject and body. When `body` is an array of strings, entries are joined
 * with line breaks so callers can compose multi-line messages easily.
 */
export function createMailtoLink(args: CreateMailtoLinkArgs = {}): string {
  const { subject, body } = args;
  const params: string[] = [];
  if (subject) {
    params.push(`subject=${encodeURIComponent(subject)}`);
  }
  if (body !== undefined) {
    const text = Array.isArray(body) ? body.join('\n') : body;
    if (text) {
      params.push(`body=${encodeURIComponent(text)}`);
    }
  }
  const query = params.length > 0 ? `?${params.join('&')}` : '';
  return `mailto:${SUPPORT_EMAIL}${query}`;
}
