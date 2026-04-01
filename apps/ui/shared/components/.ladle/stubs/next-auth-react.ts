// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Stub for next-auth/react in Ladle environment.

export const useSession = () => ({ data: null, status: 'unauthenticated' });
export const signIn = () => Promise.resolve();
export const signOut = () => Promise.resolve();
export const SessionProvider = ({ children }: { children: React.ReactNode }) =>
  children;
