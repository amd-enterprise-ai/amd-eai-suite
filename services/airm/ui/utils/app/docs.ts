// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const DOCS_BASE_URL = 'https://enterprise-ai.docs.amd.com/en/latest';
export const DocWorkbenchBaseURI = '/workbench';
export const DocResourceManagerBaseURI = '/resource-manager';

// Keep more specific paths first to ensure they match correctly.
// For example `/catalog/some-thing´ should come before `/catalog`.
const PageToDocumentationPath: Record<string, string> = {
  '/api-keys': `${DocWorkbenchBaseURI}/api-keys.html`,
  '/chat': `${DocWorkbenchBaseURI}/inference/chat.html`,
  '/datasets': `${DocWorkbenchBaseURI}/training/datasets.html`,
  '/models': `${DocWorkbenchBaseURI}/models.html`,
  '/workbench-secrets': `${DocResourceManagerBaseURI}/secrets/overview.html`,
  '/workloads': `${DocWorkbenchBaseURI}/workloads.html`,
  '/workspaces': `${DocWorkbenchBaseURI}/workspaces/overview.html`,
  '/clusters': `${DocResourceManagerBaseURI}/clusters/overview.html`,
  '/projects': `${DocResourceManagerBaseURI}/projects/project-dashboard.html`,
  '/secrets': `${DocResourceManagerBaseURI}/secrets/overview.html`,
  '/storage': `${DocResourceManagerBaseURI}/storage/overview.html`,
  '/users': `${DocResourceManagerBaseURI}/users/manage-users.html`,
};

/**
 * Returns the documentation link for a given page based on its relative path.
 * @param relativePath The path to map to documentation.
 * @returns Documentation link for the given page or the base documentation URL
 */
export const getDocumentationLink = (relativePath: string | null): string => {
  if (!relativePath) return DOCS_BASE_URL;

  let path = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;
  const match = Object.keys(PageToDocumentationPath).find((key) =>
    path.startsWith(key),
  );
  if (match) {
    return `${DOCS_BASE_URL}${PageToDocumentationPath[match]}`;
  }

  return DOCS_BASE_URL;
};
