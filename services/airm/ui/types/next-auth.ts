// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// In your type declaration file (e.g., types.d.ts)
import 'next-auth';
import 'next-auth/jwt';

declare module 'next-auth' {
  // Extends the built-in User type
  interface User {
    roles: string[];
  }

  /**
   * Extends the built-in session type
   */
  interface Session {
    idToken?: string;
    accessToken?: string;
    error: 'RefreshAccessTokenError';
    user: User;
  }
}
