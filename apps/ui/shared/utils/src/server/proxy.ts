// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getToken } from 'next-auth/jwt';
import { NextRequest, NextResponse } from 'next/server';

const SIGN_IN_PATH = '/api/auth/signin';
const NEXT_AUTH_API_PREFIX = '/api/auth';

export async function proxy(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith(NEXT_AUTH_API_PREFIX)) {
    return NextResponse.next();
  }

  const token = await getToken({ req: request });

  if (token?.email && token?.accessToken) {
    return NextResponse.next();
  }

  const signInUrl = new URL(SIGN_IN_PATH, request.url);
  const callbackUrl = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  signInUrl.searchParams.set('callbackUrl', callbackUrl);
  return NextResponse.redirect(signInUrl);
}
