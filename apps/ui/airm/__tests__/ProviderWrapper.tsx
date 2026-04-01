// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Session } from 'next-auth';
import { SessionProvider } from 'next-auth/react';
import React from 'react';

import { UserRole } from '@amdenterpriseai/types';

export const mockSession: Session = {
  expires: '2099-01-01',
  user: {
    id: 'test-user-id',
    email: 'test@example.com',
    roles: [UserRole.PLATFORM_ADMIN],
  },
  error: 'RefreshAccessTokenError',
};

export const ProviderWrapper = ({
  children,
  queryClient,
  session,
}: {
  children: React.ReactNode;
  queryClient?: QueryClient;
  session?: Session | null;
}) => {
  const [client] = React.useState(
    () =>
      queryClient ??
      new QueryClient({
        defaultOptions: { queries: { retry: false } },
      }),
  );
  return (
    <SessionProvider session={session ?? mockSession}>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </SessionProvider>
  );
};

export default ProviderWrapper;
