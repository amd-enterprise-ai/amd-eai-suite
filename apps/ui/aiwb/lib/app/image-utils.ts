// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ContentItem } from '@/types/chat';

// The server proxy accepts up to 100 MB per request (next.config.js proxyClientMaxBodySize).
// Base64 encoding inflates binary size by ~1.37x, so a single image is capped at 20 MB to
// leave room for multiple images and JSON overhead within the request body limit.
export const MAX_IMAGE_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

// Total raw size budget across all attached images. At ~1.37x base64 inflation,
// 70 MB raw encodes to ~96 MB, staying under the 100 MB proxy limit with JSON overhead.
export const MAX_TOTAL_ATTACHMENT_SIZE = 70 * 1024 * 1024; // 70 MB

const SUPPORTED_IMAGE_FORMATS = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
];

/**
 * Converts a File object to a base64-encoded data URL
 * @param file - The image file to convert
 * @returns A promise that resolves to the base64 data URL
 */
export const fileToBase64DataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      resolve(reader.result as string);
    };

    reader.onerror = () => {
      reject(reader.error ?? new Error('Failed to read file as data URL'));
    };

    reader.readAsDataURL(file);
  });
};

/**
 * Validates if a file is a supported image format
 * @param file - The file to validate
 * @returns True if the file is a supported image
 */
export const isValidImageFile = (file: File): boolean => {
  return (
    SUPPORTED_IMAGE_FORMATS.includes(file.type) &&
    file.size > 0 &&
    file.size <= MAX_IMAGE_FILE_SIZE
  );
};

/**
 * Checks if a file's MIME type is a supported image format
 * @param file - The file to check
 * @returns True if the file type is a supported image format
 */
export const isSupportedImageFormat = (file: File): boolean => {
  return SUPPORTED_IMAGE_FORMATS.includes(file.type) && file.size > 0;
};

/**
 * Checks if a file exceeds the maximum allowed image size
 * @param file - The file to check
 * @returns True if the file is too large
 */
export const isImageFileTooLarge = (file: File): boolean => {
  return file.size > MAX_IMAGE_FILE_SIZE;
};

/**
 * Gets a human-readable file size
 * @param bytes - The number of bytes
 * @returns A formatted file size string
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Extracts text content from a message content (string or array)
 * @param content - The message content (string or ContentItem[])
 * @returns The extracted text content
 */
export const extractTextContent = (content: string | ContentItem[]): string => {
  if (typeof content === 'string') {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .filter((item) => item.type === 'text')
      .map((item) => (item.type === 'text' ? item.text : ''))
      .join('\n');
  }

  return '';
};
