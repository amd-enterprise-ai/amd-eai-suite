// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextResponse } from 'next/server';

import { getInvitedUsers } from '@/services/server/users';

import { authenticateRoute, handleError } from '@/utils/server/route';

// Get rid of annoying DYNAMIC_SERVER_USAGE error, since this route doesnt have a POST/DELETE/PUT endpoint
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const { accessToken } = await authenticateRoute();
    const users = await getInvitedUsers(accessToken as string);

    return NextResponse.json(users);
  } catch (error) {
    return handleError(error);
  }
}
