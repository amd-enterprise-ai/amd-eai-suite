// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIError, APIErrorContent } from '@amdenterpriseai/types';

describe('APIErrorContent', () => {
  it('should accept an object with message property', () => {
    const errorContent: APIErrorContent = {
      message: 'Error message',
    };

    expect(errorContent.message).toBe('Error message');
  });

  it('should allow empty message string', () => {
    const errorContent: APIErrorContent = {
      message: '',
    };

    expect(errorContent.message).toBe('');
  });
});

describe('APIError', () => {
  it('should accept error as a string', () => {
    const apiError: APIError = {
      error: 'Simple string error',
    };

    expect(typeof apiError.error).toBe('string');
    expect(apiError.error).toBe('Simple string error');
  });

  it('should accept error as APIErrorContent object', () => {
    const apiError: APIError = {
      error: {
        message: 'Error message from APIErrorContent',
      },
    };

    expect(typeof apiError.error).toBe('object');
    if (typeof apiError.error === 'object' && 'message' in apiError.error) {
      expect(apiError.error.message).toBe('Error message from APIErrorContent');
    }
  });

  it('should handle both string and object error types', () => {
    const stringError: APIError = {
      error: 'String error',
    };

    const objectError: APIError = {
      error: {
        message: 'Object error',
      },
    };

    expect(typeof stringError.error).toBe('string');
    expect(typeof objectError.error).toBe('object');
  });

  it('should allow type checking with type guards', () => {
    const apiError: APIError = {
      error: {
        message: 'Test message',
      },
    };

    // Type guard to check if error is APIErrorContent
    if (
      typeof apiError.error === 'object' &&
      apiError.error !== null &&
      'message' in apiError.error
    ) {
      expect(apiError.error.message).toBe('Test message');
    }
  });
});
