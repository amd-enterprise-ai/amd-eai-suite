// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Stub for next-auth in Ladle — prevents server-side code (openid-client, oidc-token-hash)
// from being bundled into the browser. Only the client-facing exports are shimmed.

import React from 'react';

// next-auth/react exports
export const useSession = () => ({ data: null, status: 'unauthenticated' });
export const signIn = () => Promise.resolve(undefined);
export const signOut = () => Promise.resolve(undefined);
export const getSession = () => Promise.resolve(null);
export const SessionProvider = ({ children }: { children: React.ReactNode }) =>
  children;

// next-auth main exports (type augmentation import is a no-op at runtime)
export default {};
