// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';

import { authOptions } from '@/utils/server/auth';
import { getWorkbenchSecrets } from '@/services/server/workbench-secrets';

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user || !session?.accessToken) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get project ID from query params for project-scoped secrets
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('projectId');

    if (!projectId) {
      return NextResponse.json(
        { error: 'Project ID is required' },
        { status: 400 },
      );
    }

    const secrets = await getWorkbenchSecrets(
      session.accessToken as string,
      projectId,
    );

    return NextResponse.json(secrets);
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to fetch secrets' },
      { status: 500 },
    );
  }
}
