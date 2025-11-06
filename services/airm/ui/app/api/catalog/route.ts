// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';
import { CatalogItemType } from '@/types/enums/catalog';

export async function GET(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/charts?type=${CatalogItemType.WORKSPACE}`;
    const data = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(data);
  } catch (error) {
    return handleError(error);
  }
}
