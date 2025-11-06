// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getServerSession } from 'next-auth';

import { describe, expect, it, vi } from 'vitest';

vi.mock('next-auth');

describe('logoutHandler', () => {
  let logout: any;

  beforeEach(async () => {
    // Set the environment variable before importing the module
    vi.stubEnv('NEXTAUTH_SECRET', 'some-random-string');
    vi.stubEnv('NEXTAUTH_URL', 'http://localhost');
    vi.stubEnv('KEYCLOAK_ID', 'keycloak-id');
    vi.stubEnv('KEYCLOAK_SECRET', 'keycloak-secret');
    vi.stubEnv('KEYCLOAK_ISSUER', 'http://keycloak-issuer.com');

    // Dynamically import the module after setting the environment variable
    logout = (await import('@/app/api/auth/logout/route')).POST;
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("should return a 200 status code with a JSON object containing a 'path' property when a valid session exists and all environment variables are set", async () => {
    const res = await logout();

    expect(res.status).toBe(200);
    expect(await res.json()).toStrictEqual({
      path: 'http://keycloak-issuer.com/protocol/openid-connect/logout?post_logout_redirect_uri=http%3A%2F%2Flocalhost&client_id=keycloak-id',
    });
  });

  it("should return a 500 status code with a JSON object containing an 'error' property when NEXTAUTH_URL environment variable is not set", async () => {
    process.env.NEXTAUTH_URL = '';

    const res = await logout();

    expect(res.status).toBe(500);
    expect(await res.json()).toStrictEqual({
      error: 'NEXTAUTH_URL or KEYCLOAK_ID is not set',
    });

    delete process.env.NEXTAUTH_URL;
  });

  it("should return a 200 status code with a JSON object containing a 'path' property when a valid session does not exist and KEYCLOAK_ID environment variable is set", async () => {
    const res = await logout();

    expect(res.status).toBe(200);
    expect(await res.json()).toStrictEqual({
      path: 'http://keycloak-issuer.com/protocol/openid-connect/logout?post_logout_redirect_uri=http%3A%2F%2Flocalhost&client_id=keycloak-id',
    });

    delete process.env.KEYCLOAK_ID;
  });

  it("should return a 500 status code with a JSON object containing an 'error' property when a valid session does not exist and KEYCLOAK_ID environment variable is not set", async () => {
    process.env.KEYCLOAK_ID = '';
    const res = await logout();

    expect(res.status).toBe(500);
    expect(await res.json()).toStrictEqual({
      error: 'NEXTAUTH_URL or KEYCLOAK_ID is not set',
    });
  });

  it("should return a 200 status code with a JSON object containing a 'path' property when a valid session exists and idToken is not set", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce({});
    const res = await logout();

    expect(res.status).toBe(200);
    expect(await res.json()).toStrictEqual({
      path: 'http://keycloak-issuer.com/protocol/openid-connect/logout?post_logout_redirect_uri=http%3A%2F%2Flocalhost&client_id=keycloak-id',
    });
  });

  it("should return a 200 status code with a JSON object containing a 'path' property when a valid session exists and idToken is set", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce({ idToken: 'id-token' });

    const res = await logout();

    expect(res.status).toBe(200);
    expect(await res.json()).toStrictEqual({
      path: 'http://keycloak-issuer.com/protocol/openid-connect/logout?post_logout_redirect_uri=http%3A%2F%2Flocalhost&id_token_hint=id-token',
    });
  });
});
