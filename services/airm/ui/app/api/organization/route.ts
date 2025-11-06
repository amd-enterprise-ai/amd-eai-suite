// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getServerSession } from 'next-auth';
import { NextResponse } from 'next/server';

import { getCurrentUserOrganizationDetails } from '@/services/server/organizations';

import { authOptions } from '@/utils/server/auth';
import { handleError } from '@/utils/server/route';

import { Organization } from '@/types/organization';

export async function GET() {
  const session = await getServerSession(authOptions);

  if (!session || !session.accessToken) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const organizationDetails: Organization =
      await getCurrentUserOrganizationDetails(session.accessToken as string);
    return NextResponse.json(organizationDetails, { status: 200 });
  } catch (error) {
    return handleError(error);
  }
}
