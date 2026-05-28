// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Builds a project-prefixed href from a base href.
 * @param href - The base href (e.g., '/models')
 * @param projectPrefix - Optional project prefix to prepend
 * @returns The full href with project prefix (e.g., '/my-project/models')
 */
export function buildProjectHref(href: string, projectPrefix?: string): string {
  if (!projectPrefix) return href;
  const normalizedHref = href.startsWith('/') ? href : `/${href}`;
  return `/${projectPrefix}${normalizedHref}`;
}

/**
 * Strips the project prefix from a pathname for route matching.
 * Handles both direct project paths (e.g., '/my-project/models')
 * and locale-prefixed paths (e.g., '/de/my-project/models').
 *
 * @param pathname - The current pathname
 * @param projectPrefix - The project prefix to strip
 * @param locale - Optional current locale (e.g., 'de')
 * @param defaultLocale - Optional default locale (e.g., 'en')
 * @returns The pathname without the project (and locale) prefix
 */
export function stripProjectPrefix(
  pathname: string | null,
  projectPrefix?: string,
  locale?: string,
  defaultLocale?: string,
): string | null {
  if (!projectPrefix || !pathname) return pathname;
  let pathToProcess = pathname;
  if (
    locale &&
    locale !== defaultLocale &&
    pathname.startsWith(`/${locale}/`)
  ) {
    pathToProcess = pathname.slice(locale.length + 1);
  } else if (locale && locale !== defaultLocale && pathname === `/${locale}`) {
    pathToProcess = '/';
  }
  const prefix = `/${projectPrefix}`;
  if (pathToProcess === prefix || pathToProcess === `${prefix}/`) return '/';
  if (pathToProcess.startsWith(`${prefix}/`)) {
    return pathToProcess.slice(prefix.length);
  }
  return pathToProcess;
}
