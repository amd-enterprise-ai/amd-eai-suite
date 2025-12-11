// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getServerSession } from 'next-auth';
import { NextRequest, NextResponse } from 'next/server';

import { authOptions } from '@/utils/server/auth';
import getLogger from '@/utils/server/logger';

import { convertSnakeToCamel } from '../app/api-helpers';

const logger = getLogger();

export class RouteError extends Error {
  status: number;
  userMessage: string | undefined;

  constructor(status: number, message: string, userMessage?: string) {
    super(message);
    this.status = status;
    this.userMessage = userMessage;
  }
}

export async function authenticateRoute(userRole?: string) {
  /*
    Authenticate route, check user permission if applicable and return
    session object if successful.
  */

  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken) {
    throw new RouteError(
      401,
      'You must be signed in to view the protected content on this page.',
    );
  } else if (userRole && !session.user.roles.includes(userRole)) {
    throw new RouteError(
      403,
      'You do not have permission to access this page.',
    );
  } else if (!session?.accessToken) {
    throw new RouteError(500, 'Access token is missing.');
  } else {
    return session;
  }
}

export function handleError(error: any) {
  /*
    Handle error and return a NextResponse with a proper status code and error message.
    If error has a userMessage property, it will be used as the error message and the actual message is
    logged to the console. Otherwise a message from the error object is used.
  */
  logger.error(error);

  let jsonErrorMessage: { detail?: string } | undefined;
  try {
    jsonErrorMessage = JSON.parse(error.message);
  } catch (e) {
    // do nothing
  }
  return NextResponse.json(
    { error: jsonErrorMessage?.detail || error.userMessage || error.message },
    { status: error.status || 500 },
  );
}

export async function proxyRequest(
  req: NextRequest,
  url: string,
  accessToken: string,
  preserveValuesFor: string[] = [],
) {
  /*
    Proxy request from Next.JS API to a provided URL. This function preserves
    the original request method, body and query parameters. In case of an error, a
    RouteError is thrown with the status code and error message from the proxied server.
  */

  const method = req.method;
  let body: string | undefined;
  let finalUrl = url;
  const searchParams = req.nextUrl.searchParams;
  const paramString = searchParams.toString();

  if (finalUrl.includes('?')) {
    finalUrl = `${finalUrl}&${paramString}`;
  } else {
    finalUrl = `${finalUrl}?${paramString}`;
  }

  if (
    method === 'POST' ||
    method === 'PUT' ||
    method === 'DELETE' ||
    method === 'PATCH'
  ) {
    try {
      body = JSON.stringify(await req.json());
    } catch (error) {}
  }

  const response = await fetch(finalUrl, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    method,
    body,
  });

  if (response.ok) {
    if (response.status === 204) {
      return { status: 204 };
    } else {
      const body = await response.json();
      // Some nested objects should not be converted to camel case.
      return convertSnakeToCamel(body, preserveValuesFor);
    }
  } else {
    const error = await response.text();
    throw new RouteError(response.status, error);
  }
}
