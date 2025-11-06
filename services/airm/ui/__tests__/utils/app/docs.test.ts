// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  DOCS_BASE_URL,
  DocResourceManagerBaseURI,
  DocWorkbenchBaseURI,
  getDocumentationLink,
} from '@/utils/app/docs';

describe('getDocumentationLink', () => {
  it('returns the correct link for an exact match', () => {
    expect(getDocumentationLink('/workspaces')).toBe(
      `${DOCS_BASE_URL}${DocWorkbenchBaseURI}/workspaces.html`,
    );
    expect(getDocumentationLink('/users')).toBe(
      `${DOCS_BASE_URL}${DocResourceManagerBaseURI}/users/manage-users.html`,
    );
  });

  it('returns the correct link for a path with no leading slash', () => {
    expect(getDocumentationLink('chat')).toBe(
      `${DOCS_BASE_URL}${DocWorkbenchBaseURI}/inference/chat.html`,
    );
  });

  it('returns the correct link for a subpath', () => {
    expect(getDocumentationLink('/projects/fake-project-id-url')).toBe(
      `${DOCS_BASE_URL}${DocResourceManagerBaseURI}/projects/manage-projects.html`,
    );
  });

  it('returns the base URL if no match is found', () => {
    expect(getDocumentationLink('/unknown')).toBe(DOCS_BASE_URL);
    expect(getDocumentationLink('')).toBe(DOCS_BASE_URL);
    expect(getDocumentationLink(null)).toBe(DOCS_BASE_URL);
  });
});
