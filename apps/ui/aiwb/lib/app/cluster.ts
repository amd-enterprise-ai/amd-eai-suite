// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import type {
  AimImageFamily,
  ClusterAccelerator,
  ListResponse,
} from '@/types/cluster';

async function fetchClusterCatalog<T>(
  path: string,
  resourceLabel: string,
): Promise<T> {
  const response = await fetch(path, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch ${resourceLabel}: ${errorMessage}`,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export const getClusterResources = async () => {
  const response = await fetch(`/api/resources`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch cluster resources: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getAimImages = async (): Promise<ListResponse<AimImageFamily>> => {
  return fetchClusterCatalog<ListResponse<AimImageFamily>>(
    '/api/cluster/aim-images',
    'aim-engine image families',
  );
};

export const getClusterAccelerators = async (): Promise<
  ListResponse<ClusterAccelerator>
> => {
  return fetchClusterCatalog<ListResponse<ClusterAccelerator>>(
    '/api/cluster/accelerators',
    'cluster accelerators',
  );
};
