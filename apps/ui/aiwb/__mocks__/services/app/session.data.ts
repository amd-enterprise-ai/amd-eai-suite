// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const mockSession = {
  user: {
    id: 'test-user-id',
    email: 'test@test.com',
    name: 'Test User',
    roles: ['platform-admin'],
  },
  expires: '2099-12-31',
  error: 'RefreshAccessTokenError' as const,
  accessToken: 'token123',
};
