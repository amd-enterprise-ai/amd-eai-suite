// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { Organization } from '@amdenterpriseai/types';

export async function fetchOrganization(): Promise<Organization> {
  const response = await fetch('/api/organization');

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch organization information: ${errorMessage}`,
      response.status,
    );
  }

  const organization = await response.json();

  return organization as Organization;
}
