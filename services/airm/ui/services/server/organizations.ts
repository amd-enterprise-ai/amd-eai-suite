// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';

import { Organization } from '@/types/organization';

export async function getCurrentUserOrganizationDetails(
  token: string,
): Promise<Organization> {
  try {
    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/organization`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(
        `Error fetching organization details: ${await getErrorMessage(response)}`,
      );
    }

    const data = await response.json();
    return convertSnakeToCamel(data) as Organization;
  } catch (error) {
    console.error('Error fetching current user organization details:', error);
    throw error;
  }
}
