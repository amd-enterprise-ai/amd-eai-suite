// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { deleteUser, getUser } from '@/services/server/users';

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

export async function GET(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: userId } = await params;
    const users = await getUser(userId, accessToken as string);

    return NextResponse.json(users);
  } catch (error) {
    return handleError(error);
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: userId } = await params;

    await deleteUser(userId, req, accessToken as string);

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();
    const { id: userId } = await params;

    const url = `${process.env.AIRM_API_SERVICE_URL}/v1/users/${userId}`;
    await proxyRequest(req, url, accessToken as string);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}
