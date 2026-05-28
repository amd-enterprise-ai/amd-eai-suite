// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const getErrorMessage = async (response: Response): Promise<string> => {
  try {
    const responseBody = await response.json();
    const errorValue =
      responseBody.error ?? responseBody.message ?? response.statusText;

    // Handle APIErrorContent object (with message property)
    if (
      typeof errorValue === 'object' &&
      errorValue !== null &&
      'message' in errorValue
    ) {
      return String(errorValue.message);
    }

    return String(errorValue);
  } catch (e) {
    if (e instanceof Error) {
      return e.message;
    }
    return response.statusText || 'An unknown error occurred';
  }
};

export const DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA = 10000;
