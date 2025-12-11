// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

export interface Chart {
  id: string;
  name: string;
  description?: string;
}

/**
 * Retrieves a single chart by ID.
 *
 * @param {string} id - The chart ID
 * @returns {Promise<Chart>} A promise that resolves to a Chart object.
 * @throws {APIRequestError} If the API request fails.
 */
export const getChart = async (id: string): Promise<Chart> => {
  const response = await fetch(`/api/catalog/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get chart: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return await response.json();
};
