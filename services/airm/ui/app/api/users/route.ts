// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getUsers, inviteUser } from '@/services/server/users';

import { authenticateRoute, handleError } from '@/utils/server/route';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const users = await getUsers(accessToken as string);

    return NextResponse.json(users);
  } catch (error) {
    return handleError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { accessToken } = await authenticateRoute();

    const invitedUser = await inviteUser(request, accessToken as string);

    return NextResponse.json(invitedUser);
  } catch (error) {
    return handleError(error);
  }
}
