// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

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
  const response = await fetch(`/api/charts/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get chart: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};
