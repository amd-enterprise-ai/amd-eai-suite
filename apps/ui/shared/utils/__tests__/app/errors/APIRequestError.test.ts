// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { describe, expect, it } from 'vitest';

describe('APIRequestError', () => {
  it('should create an instance of APIRequestError with message and statusCode', () => {
    const message = 'Failed to get resource: Resource not found';
    const statusCode = 404;
    const error = new APIRequestError(message, statusCode);

    expect(error).toBeInstanceOf(APIRequestError);
    expect(error.message).toBe(message);
    expect(error.statusCode).toBe(statusCode);
    expect(error.name).toBe('APIRequestError');
  });

  it('should have a default name of "APIRequestError"', () => {
    const error = new APIRequestError('Server error', 500);

    expect(error.name).toBe('APIRequestError');
  });

  it('should preserve error message', () => {
    const message = 'Failed to get workload: Connection timeout';
    const error = new APIRequestError(message, 500);

    expect(error.message).toBe(message);
  });

  it('should be an instance of Error', () => {
    const error = new APIRequestError('Bad request', 400);

    expect(error).toBeInstanceOf(Error);
  });

  it('should preserve statusCode for different status codes', () => {
    const statusCodes = [200, 400, 401, 403, 404, 500, 502, 503];

    statusCodes.forEach((statusCode) => {
      const error = new APIRequestError(`Error ${statusCode}`, statusCode);
      expect(error.statusCode).toBe(statusCode);
    });
  });
});
