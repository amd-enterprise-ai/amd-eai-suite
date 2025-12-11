// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { EXTENSION_MIME_TYPES } from './constants';

/**
 * Validates if a MIME type is acceptable for a given file extension
 */
const validateMimeTypeForExtension = (
  mimeType: string,
  extension: string,
): boolean => {
  const acceptableMimeTypes = EXTENSION_MIME_TYPES[extension.toLowerCase()];

  if (!acceptableMimeTypes) return false;

  // Allow empty MIME type (some browsers don't always provide it)
  if (!mimeType) return true;

  return acceptableMimeTypes.includes(mimeType);
};

/**
 * Unified validation function for both drag events and actual files
 */
export const validateFileInput = (
  input: DataTransfer | File[],
  multiple: boolean,
  accept?: string,
): boolean => {
  let items: Array<{ type: string; name?: string }>;

  if (input instanceof DataTransfer) {
    if (!input.types?.includes('Files')) return false;
    if (!input.items || input.items.length === 0) return true;

    const fileItems = Array.from(input.items).filter(
      (item) => item.kind === 'file',
    );
    items = fileItems.map((item) => ({ type: item.type }));
  } else {
    items = input.map((file) => ({ type: file.type, name: file.name }));
  }

  if (!multiple && items.length > 1) return false;
  if (!accept) return true;

  const acceptedTypes = accept.split(',').map((type) => type.trim());

  return items.every((item) => {
    return acceptedTypes.some((acceptedType) => {
      if (acceptedType.startsWith('.')) {
        const hasCorrectMimeType = validateMimeTypeForExtension(
          item.type,
          acceptedType,
        );

        if (!item.name) return hasCorrectMimeType;

        const hasCorrectExtension = item.name
          .toLowerCase()
          .endsWith(acceptedType.toLowerCase());

        return hasCorrectExtension && hasCorrectMimeType;
      }

      if (acceptedType.includes('*')) {
        const baseType = acceptedType.split('/')[0];
        return item.type.startsWith(baseType);
      }

      return item.type === acceptedType;
    });
  });
};

export const createFileList = (files: File[]): FileList => {
  const dt = new DataTransfer();
  files.forEach((file) => {
    dt.items.add(file);
  });
  return dt.files;
};

export const getTotalFileSizeInBytes = (files: File[]): number =>
  files.reduce((total, file) => total + file.size, 0);
