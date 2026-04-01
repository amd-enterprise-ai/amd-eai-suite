// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Consts for FormFileUpload and it's local components
 */

// Mapping of file extensions to their acceptable MIME types
export const EXTENSION_MIME_TYPES: Record<string, string[]> = {
  '.jsonl': [
    'application/json',
    'text/plain',
    'application/jsonl',
    'application/octet-stream',
  ],
  '.json': ['application/json', 'text/plain'],
  '.txt': ['text/plain'],
  '.csv': ['text/csv', 'application/csv', 'text/plain'],
  '.pdf': ['application/pdf'],
  '.jpg': ['image/jpeg'],
  '.jpeg': ['image/jpeg'],
  '.png': ['image/png'],
  '.gif': ['image/gif'],
  '.webp': ['image/webp'],
  '.svg': ['image/svg+xml'],
  '.xml': ['application/xml', 'text/xml'],
  '.md': ['text/markdown', 'text/plain'],
};
