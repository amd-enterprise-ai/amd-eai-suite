// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getServerSession } from 'next-auth';
import { NextRequest, NextResponse } from 'next/server';

import { authOptions } from './auth';
import getLogger from './logger';

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
  if (!session?.accessToken) {
    throw new RouteError(
      401,
      'You must be signed in to view the protected content on this page.',
    );
  } else if (userRole && !session.user.roles.includes(userRole)) {
    throw new RouteError(
      403,
      'You do not have permission to access this page.',
    );
  } else {
    return session;
  }
}

export function handleError(error: any) {
  /*
    Handle error and return a NextResponse with a proper status code and error message.
    If error has a userMessage property, it will be used as the error message. Otherwise the message
    from the error object is used. Unexpected errors (non-RouteError or 5xx RouteError) are also
    logged via logger.error.
  */
  if (!(error instanceof RouteError) || error.status >= 500) {
    logger.error(error);
  }

  const err = error as {
    status?: number;
    message?: string;
    userMessage?: string;
  };
  const status =
    typeof err.status === 'number' && Number.isFinite(err.status)
      ? err.status
      : 500;
  const rawMessage = typeof err.message === 'string' ? err.message : '';

  let parsed: unknown;
  if (rawMessage) {
    try {
      parsed = JSON.parse(rawMessage);
    } catch {
      parsed = undefined;
    }
  } else {
    parsed = undefined;
  }

  if (
    parsed &&
    typeof parsed === 'object' &&
    parsed !== null &&
    !Array.isArray(parsed)
  ) {
    const o = parsed as Record<string, unknown>;
    const flattened =
      (typeof o.detail === 'string' && o.detail.length > 0
        ? o.detail
        : typeof o.error === 'string' && o.error.length > 0
          ? o.error
          : undefined) ||
      err.userMessage ||
      (status >= 500 ? 'Internal server error' : 'Request failed');
    return NextResponse.json({ ...o, error: flattened }, { status });
  }

  return NextResponse.json(
    {
      error:
        err.userMessage ||
        rawMessage ||
        (status >= 500 ? 'Internal server error' : 'Request failed'),
    },
    { status },
  );
}

export async function proxyRequest(
  req: NextRequest,
  url: string,
  accessToken: string,
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
    // Avoid following 3xx to an HTML login or marketing page: a 200 HTML body
    // would fail JSON.parse and surface as a misleading BFF 502.
    redirect: 'manual',
  });

  if (response.ok) {
    if (response.status === 204) {
      return { status: 204 };
    }
    const responseText = await response.text();
    const trimmed = responseText.trim().replace(/^\uFEFF/, '');
    if (!trimmed) {
      return {};
    }
    try {
      return JSON.parse(trimmed);
    } catch {
      const looksLikeHtml =
        /^<!DOCTYPE\b/i.test(trimmed) || /^<html\b/i.test(trimmed);
      throw new RouteError(
        502,
        looksLikeHtml
          ? 'Upstream returned HTML instead of JSON (often a redirect to a login page). Verify the expected API base URL (server-side env) and that the session token is valid.'
          : 'Upstream returned a non-JSON response body.',
      );
    }
  } else {
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('Location');
      const userMessage = `Upstream returned HTTP ${response.status} (redirect) instead of a JSON API response. Verify the expected API base URL (server-side env) and the session token.`;
      const logMessage = location
        ? `${userMessage} Location: ${location}`
        : userMessage;
      throw new RouteError(502, logMessage, userMessage);
    }
    const error = await response.text();
    throw new RouteError(response.status, error);
  }
}
