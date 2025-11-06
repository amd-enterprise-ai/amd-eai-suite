// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getProjects } from '@/services/server/projects';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const projects = await getProjects(accessToken as string);

    return NextResponse.json(projects);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects`;
    const json = await proxyRequest(request, url, accessToken as string);
    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}
