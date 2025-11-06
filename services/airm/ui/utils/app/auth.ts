// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { signOut } from 'next-auth/react';

export const logout = async (): Promise<void> => {
  const response = await fetch('/api/auth/logout', { method: 'POST' });
  const { path: redirectUrl } = await response.json();

  await signOut({ redirect: false });
  // Adding a 100ms delay to ensure that the signOut operation has propagated properly
  // before redirecting the user to the new location.
  await new Promise((res) => setTimeout(res, 100));
  window.location = redirectUrl;
};
