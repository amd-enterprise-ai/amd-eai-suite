// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { convertCamelToSnake } from '@amdenterpriseai/utils/app';
import { authenticateRoute, handleError } from '@amdenterpriseai/utils/server';

import { CatalogItemDeployment } from '@amdenterpriseai/types';

export async function POST(req: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();
    // workload type path segment, e.g. workspaces
    const type = req.nextUrl.searchParams.get('type') || '';

    const searchParams = req.nextUrl.searchParams;
    const projectId = (searchParams.get('projectId') as string) || '';

    // workload template path segment, e.g. vscode
    const template = req.nextUrl.searchParams.get('template') || '';
    const displayNameQuery = searchParams.get('displayName')
      ? `&display_name=${searchParams.get('displayName')}`
      : '';
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/${type}/${template}?project_id=${projectId}${displayNameQuery}`;
    const body: CatalogItemDeployment = await req.json();

    const response = await fetch(baseUrl, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      method: 'POST',
      body: JSON.stringify(convertCamelToSnake(body)),
    });

    const json = await response.json();

    const status = response.status;
    if (status !== 200) {
      throw new Error(`Failed to deploy catalog item: ${JSON.stringify(json)}`);
    }

    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
