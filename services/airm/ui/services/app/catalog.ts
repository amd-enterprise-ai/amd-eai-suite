// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import { CatalogItem, CatalogItemDeployment } from '@/types/catalog';

export const getCatalogItems = async (): Promise<CatalogItem[]> => {
  const url = '/api/catalog';

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch catalog items: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return await response.json();
};

export const getCatalogItemById = async (id: string): Promise<CatalogItem> => {
  const url = `/api/catalog/${id}`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch catalog item: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return await response.json();
};

export const deployCatalogItem = async (
  item: CatalogItemDeployment,
  projectId: string,
): Promise<{
  id: string;
}> => {
  const displayNameQuery = item.displayName
    ? `&displayName=${item.displayName}`
    : '';
  const url = `/api/catalog/deploy?type=${item.type}&template=${item.template}&projectId=${projectId}${displayNameQuery}`;

  if (!item.image || item.image === '') {
    delete item.image;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(item),
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to deploy catalog item: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return await response.json();
};
