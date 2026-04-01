// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  signInLogic,
  logOutUrl,
  authOptions,
} from '@amdenterpriseai/utils/server';
import jsonwebtoken from 'jsonwebtoken';

describe('signInLogic', () => {
  it('should return true for valid keycloak account with verified email', () => {
    const result = signInLogic('keycloak', 'user@example.com', true);
    expect(result).toBe(true);
  });

  it('should return false if account provider is not keycloak', () => {
    const result = signInLogic('github', 'user@example.com', true);
    expect(result).toBe(false);
  });

  it('should return false if profile email is missing', () => {
    const result = signInLogic('keycloak', undefined, true);
    expect(result).toBe(false);
  });

  it('should return false if profile email is not verified', () => {
    const result = signInLogic('keycloak', 'user@example.com', false);
    expect(result).toBe(false);
  });

  it('should return false if all conditions are not met', () => {
    const result = signInLogic(undefined, undefined, false);
    expect(result).toBe(false);
  });

  it('should return false for empty email string', () => {
    const result = signInLogic('keycloak', '', true);
    expect(result).toBe(false);
  });

  it('should return true only when all three conditions are satisfied', () => {
    expect(signInLogic('keycloak', 'user@example.com', true)).toBe(true);
    expect(signInLogic('keycloak', 'user@example.com', false)).toBe(false);
    expect(signInLogic('other', 'user@example.com', true)).toBe(false);
    expect(signInLogic('keycloak', undefined, true)).toBe(false);
  });
});

describe('logOutUrl', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset environment variables before each test
    process.env = { ...originalEnv };
    process.env.NEXTAUTH_URL = 'http://localhost:3000';
    process.env.KEYCLOAK_ID = 'test-client-id';
    process.env.KEYCLOAK_ISSUER = 'http://keycloak:8080/realms/test';
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should generate logout URL with id_token', () => {
    const idToken = 'test-id-token-123';
    const result = logOutUrl(idToken);

    expect(result).toContain('http://keycloak:8080/realms/test');
    expect(result).toContain('/protocol/openid-connect/logout?');
    expect(result).toContain(
      `post_logout_redirect_uri=${encodeURIComponent('http://localhost:3000')}`,
    );
    expect(result).toContain(`id_token_hint=${idToken}`);
  });

  it('should generate logout URL without id_token using client_id', () => {
    const result = logOutUrl();

    expect(result).toContain('http://keycloak:8080/realms/test');
    expect(result).toContain('/protocol/openid-connect/logout?');
    expect(result).toContain(
      `post_logout_redirect_uri=${encodeURIComponent('http://localhost:3000')}`,
    );
    expect(result).toContain(`client_id=test-client-id`);
    expect(result).not.toContain('id_token_hint');
  });

  it('should throw error if NEXTAUTH_URL is not set', () => {
    delete process.env.NEXTAUTH_URL;

    expect(() => logOutUrl()).toThrow('NEXTAUTH_URL or KEYCLOAK_ID is not set');
  });

  it('should throw error if KEYCLOAK_ID is not set', () => {
    delete process.env.KEYCLOAK_ID;

    expect(() => logOutUrl()).toThrow('NEXTAUTH_URL or KEYCLOAK_ID is not set');
  });

  it('should throw error if both NEXTAUTH_URL and KEYCLOAK_ID are not set', () => {
    delete process.env.NEXTAUTH_URL;
    delete process.env.KEYCLOAK_ID;

    expect(() => logOutUrl()).toThrow('NEXTAUTH_URL or KEYCLOAK_ID is not set');
  });

  it('should properly encode redirect URI with special characters', () => {
    process.env.NEXTAUTH_URL = 'https://example.com/app?test=value';

    const result = logOutUrl();

    expect(result).toContain(
      `post_logout_redirect_uri=${encodeURIComponent('https://example.com/app?test=value')}`,
    );
  });

  it('should use KEYCLOAK_ISSUER from environment', () => {
    process.env.KEYCLOAK_ISSUER = 'https://custom.keycloak.com/realms/custom';

    const result = logOutUrl();

    expect(result).toContain('https://custom.keycloak.com/realms/custom');
    expect(result).toContain('/protocol/openid-connect/logout');
  });

  it('should include both post_logout_redirect_uri and id_token_hint when idToken provided', () => {
    const idToken = 'test-token';
    const result = logOutUrl(idToken);

    expect(result).toMatch(/post_logout_redirect_uri=.*&id_token_hint=/);
  });

  it('should include both post_logout_redirect_uri and client_id when no idToken', () => {
    const result = logOutUrl();

    expect(result).toMatch(/post_logout_redirect_uri=.*&client_id=/);
  });
});

describe('authOptions callbacks', () => {
  const originalEnv = process.env;
  const originalFetch = global.fetch;

  beforeEach(() => {
    process.env = { ...originalEnv };
    process.env.NEXTAUTH_URL = 'http://localhost:3000';
    process.env.KEYCLOAK_ID = 'test-client-id';
    process.env.KEYCLOAK_SECRET = 'test-client-secret';
    process.env.KEYCLOAK_ISSUER = 'http://keycloak:8080/realms/test';
    process.env.KEYCLOAK_ISSUER_INTERNAL_URL =
      'http://keycloak-internal:8080/realms/test';
    process.env.NEXTAUTH_SECRET = 'nextauth-secret';

    global.fetch = vi.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('signIn should return true for valid keycloak profile and not call logout', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const result = await authOptions.callbacks?.signIn?.({
      account: { provider: 'keycloak', id_token: 'id-token' } as any,
      profile: { email: 'user@example.com', email_verified: true } as any,
    } as any);

    expect(result).toBe(true);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('signIn should call logout url when user cannot login', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const result = await authOptions.callbacks?.signIn?.({
      account: { provider: 'keycloak', id_token: 'id-token' } as any,
      profile: { email: 'user@example.com', email_verified: false } as any,
    } as any);

    expect(result).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(logOutUrl('id-token'));
  });

  it('jwt should set token fields on initial sign-in', async () => {
    const baseToken: any = {};
    const account = {
      id_token: 'id-token',
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      expires_at: 1700000000,
    } as any;

    const result = await authOptions.callbacks?.jwt?.({
      token: baseToken,
      account,
      trigger: undefined,
      session: undefined,
    } as any);

    expect(result?.idToken).toBe('id-token');
    expect(result?.accessToken).toBe('access-token');
    expect(result?.refreshToken).toBe('refresh-token');
    expect(result?.accessTokenExpires).toBe(1700000000 * 1000);
    expect(result?.accessTokenExpiresHumanReadable).toBeTruthy();
  });

  it('jwt should refresh token on update trigger', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1700000000000);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue({
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        expires_in: 3600,
      }),
    } as any);

    const result = await authOptions.callbacks?.jwt?.({
      token: { refreshToken: 'old-refresh-token' } as any,
      account: undefined,
      trigger: 'update',
      session: undefined,
    } as any);

    expect(result?.accessToken).toBe('new-access-token');
    expect(result?.refreshToken).toBe('new-refresh-token');
    expect(result?.accessTokenExpires).toBe(1700000000000 + 3600 * 1000);

    nowSpy.mockRestore();
  });

  it('jwt should throw when refresh fails on update trigger', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: vi.fn().mockResolvedValue({ error: 'invalid_grant' }),
    } as any);

    await expect(
      authOptions.callbacks?.jwt?.({
        token: { refreshToken: 'bad-refresh-token' } as any,
        account: undefined,
        trigger: 'update',
        session: undefined,
      } as any),
    ).rejects.toThrow('RefreshTokenExpired');
  });

  it('jwt should return existing token when not expired', async () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1000);

    const token = { accessTokenExpires: 2000 } as any;
    const result = await authOptions.callbacks?.jwt?.({
      token,
      account: undefined,
      trigger: undefined,
      session: undefined,
    } as any);

    expect(result).toBe(token);

    nowSpy.mockRestore();
  });

  it('jwt should refresh token when expired', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(2000);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue({
        access_token: 'refreshed-access-token',
        refresh_token: undefined,
        expires_in: 1800,
      }),
    } as any);

    const token = { accessTokenExpires: 1000, refreshToken: 'refresh' } as any;
    const result = await authOptions.callbacks?.jwt?.({
      token,
      account: undefined,
      trigger: undefined,
      session: undefined,
    } as any);

    expect(result?.accessToken).toBe('refreshed-access-token');
    expect(result?.refreshToken).toBe('refresh');
    expect(result?.accessTokenExpires).toBe(2000 + 1800 * 1000);

    nowSpy.mockRestore();
  });

  it('session should attach roles from access token', async () => {
    const decodeSpy = vi
      .spyOn(jsonwebtoken, 'decode')
      .mockReturnValue({ realm_access: { roles: ['admin', 'user'] } } as any);

    const session = { user: { name: 'Test User', roles: [] } } as any;
    const token = { accessToken: 'access-token', idToken: 'id-token' } as any;

    const result = await authOptions.callbacks?.session?.({
      session,
      user: undefined,
      token,
    } as any);

    expect(result?.user.roles).toEqual(['admin', 'user']);
    expect(result?.accessToken).toBe('access-token');
    expect(result?.idToken).toBe('id-token');

    decodeSpy.mockRestore();
  });
});
