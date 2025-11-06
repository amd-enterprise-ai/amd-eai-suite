// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError } from '@/utils/app/errors';

describe('APIRequestError', () => {
  it('should create an instance of APIRequestError with the correct message and statusCode', () => {
    const message = 'An error occurred';
    const statusCode = 404;
    const error = new APIRequestError(message, statusCode);

    expect(error).toBeInstanceOf(APIRequestError);
    expect(error.message).toBe(message);
    expect(error.statusCode).toBe(statusCode);
    expect(error.name).toBe('APIRequestError');
  });

  it('should have a default name of "APIRequestError"', () => {
    const error = new APIRequestError('An error occurred', 500);

    expect(error.name).toBe('APIRequestError');
  });
});
