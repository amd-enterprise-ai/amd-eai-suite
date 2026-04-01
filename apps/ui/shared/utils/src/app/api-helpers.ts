// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { camelCase, isArray, isObject, snakeCase, transform } from 'lodash';

export function convertSnakeToCamel(
  obj: Record<string, any>,
  preserveValuesFor: string[] = [],
) {
  return transform(obj, (acc: any, value, key, target) => {
    const camelKey = isArray(target) ? key : camelCase(key);
    acc[camelKey] =
      isObject(value) && !preserveValuesFor.includes(key)
        ? convertSnakeToCamel(value, preserveValuesFor)
        : value;
  });
}

export function convertCamelToSnakeParams(
  params: Record<string, any>,
): URLSearchParams {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      const snakeKey = snakeCase(key);
      searchParams.append(snakeKey, String(value));
    }
  });

  return searchParams;
}

export function convertCamelToSnake(
  params: Record<string, any>,
): Record<string, any> {
  const result: Record<string, any> = {};

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      const snakeKey = snakeCase(key);
      // Recursively convert nested objects
      if (isObject(value) && !isArray(value)) {
        result[snakeKey] = convertCamelToSnake(value);
      }
      // Recursively convert objects inside arrays
      else if (isArray(value)) {
        result[snakeKey] = value.map((item) =>
          isObject(item) && !isArray(item) ? convertCamelToSnake(item) : item,
        );
      } else {
        result[snakeKey] = value;
      }
    }
  });

  return result;
}

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
