// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextAuthOptions } from 'next-auth';
import { JWT } from 'next-auth/jwt';
import KeycloakProvider from 'next-auth/providers/keycloak';

import getLogger from '@/utils/server/logger';

import jsonwebtoken, { JwtPayload } from 'jsonwebtoken';

const logger = getLogger();

// todo: check these in a different way so we don't have to set them during building the docker image
if (!process.env.NEXTAUTH_SECRET) throw new Error('NEXTAUTH_SECRET is not set');
if (!process.env.KEYCLOAK_ID) throw new Error('KEYCLOAK_ID is not set');
if (!process.env.KEYCLOAK_SECRET) throw new Error('KEYCLOAK_SECRET is not set');
if (!process.env.KEYCLOAK_ISSUER) throw new Error('KEYCLOAK_ISSUER is not set');

let nextAuthSecret = process.env.NEXTAUTH_SECRET;
let keycloakId = process.env.KEYCLOAK_ID;
let keycloakSecret = process.env.KEYCLOAK_SECRET;
let keycloakIssuer = process.env.KEYCLOAK_ISSUER;
let keycloakIssuerInternal =
  process.env.KEYCLOAK_ISSUER_INTERNAL_URL || keycloakIssuer;

/**
 * Takes a token, and returns a new token with updated
 * `accessToken` and `accessTokenExpires`. If an error occurs,
 * returns the old token and an error property
 * v3 docs: https://next-auth.js.org/v3/tutorials/refresh-token-rotation
 * https://authjs.dev/guides/basics/refresh-token-rotation?frameworks=core
 */
async function refreshAccessToken(token: JWT) {
  try {
    // check the environment variables

    const url = keycloakIssuerInternal + '/protocol/openid-connect/token';
    const refreshToken =
      typeof token.refreshToken === 'string' ? token.refreshToken : '';

    const params = new URLSearchParams({
      client_id: keycloakId,
      client_secret: keycloakSecret,
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    });

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
      method: 'POST',
    });

    const refreshedTokens = await response.json();

    if (!response.ok) {
      throw refreshedTokens;
    }

    const expiresAt = Date.now() + refreshedTokens.expires_in * 1000;
    return {
      ...token, // keep the previous token properties
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: expiresAt,
      accessTokenExpiresHumanReadable: new Date(expiresAt).toLocaleString(),
      refreshToken: refreshedTokens.refresh_token ?? token.refreshToken, // Fall back to old refresh token
    };
  } catch (error) {
    console.log(error);

    return {
      ...token,
      error: 'RefreshAccessTokenError',
    };
  }
}

export function signInLogic(
  accountProvider: string | undefined,
  profileEmail: string | undefined,
  profileEmailVerified: boolean,
) {
  if (accountProvider === 'keycloak' && profileEmail && profileEmailVerified) {
    logger.info('signIn account: ' + profileEmail);

    // profile email must be verified.
    return profileEmailVerified;
  }
  return false;
}

export const authOptions: NextAuthOptions = {
  secret: nextAuthSecret,
  session: {
    strategy: 'jwt',
    maxAge: 8 * 60 * 60, // 8 hours
  },
  providers: [
    KeycloakProvider({
      clientId: keycloakId,
      clientSecret: keycloakSecret,
      issuer: keycloakIssuer,
      wellKnown: undefined,
      allowDangerousEmailAccountLinking: true,
      authorization: {
        // Public URL used by user to authenticate
        url: `${keycloakIssuer}/protocol/openid-connect/auth`,
        params: { scope: 'openid profile email organization' },
      },
      // Internal URLs used by ui on k8s.
      // This is done this way because on OCI1 for example, the UI cannot access keycloak
      // on the same URL that the user logs in, due to networking restrictions
      token: `${keycloakIssuerInternal}/protocol/openid-connect/token`,
      userinfo: `${keycloakIssuerInternal}/protocol/openid-connect/userinfo`,
      jwks_endpoint: `${keycloakIssuerInternal}/protocol/openid-connect/certs`,
    }),
  ],
  debug: false,
  theme: {
    colorScheme: 'dark',
    logo: 'https://www.amd.com/content/dam/code/images/header/amd-header-logo.svg',
    brandColor: '#232341',
  },
  callbacks: {
    // restrict access to a certain domain
    async signIn({ account, profile }) {
      const canLogin = signInLogic(
        account?.provider,
        profile?.email,
        // @ts-ignore todo email_verified is not in the type
        profile?.email_verified,
      );

      if (!canLogin) {
        // user cannot login, log them out from keycloak
        logger.warn(
          'signIn account: ' + profile?.email + ' is not allowed to login.',
        );
        const url = logOutUrl(account?.id_token);
        await fetch(url);
      }

      return canLogin;
    },
    // get the id_token from keycloak and add it to the session
    async jwt({ token, account, trigger, session }) {
      if (account) {
        // Initial sign in (account is set)
        const expiresAtHumanReadable = account.expires_at
          ? new Date(account.expires_at * 1000).toLocaleString()
          : '';
        token = Object.assign({}, token, {
          idToken: account.id_token,
          accessToken: account.access_token,
          accessTokenExpires: account.expires_at
            ? account.expires_at * 1000
            : undefined,
          accessTokenExpiresHumanReadable: expiresAtHumanReadable,
          refreshToken: account.refresh_token,
        });
        logger.info(`JWT (expires at ${expiresAtHumanReadable}): `);
        return token;
      } else if (trigger === 'update') {
        const updatedToken: JWT = await refreshAccessToken(token);
        if (updatedToken.error === 'RefreshAccessTokenError') {
          throw new Error('RefreshTokenExpired');
        }
        logger.info('Token refreshed via update trigger');
        return updatedToken;
      } else if (Date.now() < (token.accessTokenExpires as number)) {
        // Return previous token if the access token has not expired yet
        return token;
      } else {
        // Access token has expired, try to update it
        const updatedToken: JWT = await refreshAccessToken(token);
        if (updatedToken.error === 'RefreshAccessTokenError') {
          // If the refresh token has expired, throw an error to sign the user out
          logger.warn('RefreshTokenExpired');
          throw new Error('RefreshTokenExpired');
        }
        logger.info('Token refreshed');
        return updatedToken;
      }
    },
    async session({ session, user, token }) {
      const decoded = jsonwebtoken.decode(
        token.accessToken as string,
      ) as JwtPayload;
      const roles = decoded?.realm_access?.roles || [];

      if (session) {
        session = Object.assign({}, session, {
          idToken: token.idToken,
          accessToken: token.accessToken,
          error: token.error,
          user: { ...session.user, roles },
        });
      }
      return session;
    },
  },
};

export const logOutUrl = (idToken?: string) => {
  const NEXTAUTH_URL = process.env.NEXTAUTH_URL;
  const KEYCLOAK_ID = process.env.KEYCLOAK_ID;
  if (!NEXTAUTH_URL || !KEYCLOAK_ID) {
    throw new Error('NEXTAUTH_URL or KEYCLOAK_ID is not set');
  }

  let path =
    process.env.KEYCLOAK_ISSUER +
    `/protocol/openid-connect/logout?` +
    `post_logout_redirect_uri=${encodeURIComponent(NEXTAUTH_URL)}`;

  if (idToken) {
    path = path + `&id_token_hint=${idToken}`;
  } else {
    path = path + `&client_id=${process.env.KEYCLOAK_ID}`;
  }

  return path;
};
