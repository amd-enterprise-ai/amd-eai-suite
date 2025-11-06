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
      result[snakeKey] = value;
    }
  });

  return result;
}

export const getErrorMessage = async (response: Response) => {
  try {
    const responseBody = await response.json();
    const errorValue =
      responseBody.error || responseBody.message || response.statusText;

    // If the error is an object, try to extract a meaningful message
    if (typeof errorValue === 'object' && errorValue !== null) {
      // Try to get a message property from the error object
      if ('message' in errorValue && typeof errorValue.message === 'string') {
        return errorValue.message;
      }
      // If it's an array, join the messages
      if (Array.isArray(errorValue)) {
        return errorValue
          .map((e) => (typeof e === 'string' ? e : JSON.stringify(e)))
          .join(', ');
      }
      // Otherwise, stringify the object
      return JSON.stringify(errorValue);
    }

    return String(errorValue);
  } catch (e: any) {
    return e.message || response.statusText;
  }
};

export async function waitForAllPromisesAndCheckStatus(
  promises: Promise<Response>[],
) {
  const responses = await Promise.all(promises);

  const failedResponses = responses.filter((response) => !response.ok);
  if (failedResponses.length > 0) {
    const responseBody = await failedResponses[0].text();
    throw new Error(`Action failed due to ${responseBody}`);
  }
}

export const DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA = 10000;
