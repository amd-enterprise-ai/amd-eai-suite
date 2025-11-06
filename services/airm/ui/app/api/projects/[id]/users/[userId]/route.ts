// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { deleteUserFromProject } from '@/services/server/projects';

import { authenticateRoute, handleError } from '@/utils/server/route';

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; userId: string }> },
) {
  try {
    const { accessToken } = await authenticateRoute();

    const { id: projectId, userId } = await params;

    await deleteUserFromProject(userId, projectId, req, accessToken as string);

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return handleError(error);
  }
}
