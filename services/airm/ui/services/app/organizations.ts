// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import { Organization } from '@/types/organization';

export async function fetchOrganization(): Promise<Organization> {
  const response = await fetch('/api/organization');

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch organization information: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const organization = await response.json();

  return organization as Organization;
}
