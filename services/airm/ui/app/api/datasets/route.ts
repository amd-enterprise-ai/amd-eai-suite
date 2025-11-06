// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { convertSnakeToCamel } from '@/utils/app/api-helpers';
import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

import { DatasetType } from '@/types/datasets';

export async function GET(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets`;
    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(convertSnakeToCamel(json));
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    const formData = await req.formData();

    const name = formData.get('name') as string;
    const description = formData.get('description') as string;
    const file = formData.get('file') as File;
    const type = formData.get('type') as DatasetType;

    const projectId = req.nextUrl.searchParams.get('project_id') || '';

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/datasets/upload?project_id=${projectId}`;

    const body = new FormData();
    body.append('name', name);
    body.append('description', description);
    body.append('jsonl', file);
    body.append('type', type);

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'POST',
      body,
    });

    return NextResponse.json(await response.json());
  } catch (error) {
    return handleError(error);
  }
}
