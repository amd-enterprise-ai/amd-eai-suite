// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { HeroUIProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';

import { appWithTranslation } from 'next-i18next';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { AppProps } from 'next/app';

import nextI18NextConfig from '../next-i18next.config.js';

import { AppLayout } from '@amdenterpriseai/layouts';
import { airmMenuItems } from '@amdenterpriseai/utils/app';
import { SystemToastContainer } from '@amdenterpriseai/components';

import '@/styles/globals.css';
import '@/styles/toastify.css';

function App({ Component, pageProps: { session, ...pageProps } }: AppProps) {
  const queryClient = new QueryClient();

  return (
    <SessionProvider session={session} refetchInterval={10 * 60}>
      <QueryClientProvider client={queryClient}>
        <HeroUIProvider disableRipple>
          <NextThemesProvider
            disableTransitionOnChange
            attribute="class"
            defaultTheme="dark"
          >
            <SystemToastContainer />
            <AppLayout
              pageBreadcrumb={pageProps?.pageBreadcrumb}
              menuItems={airmMenuItems}
              appTitle={'sections.resourceManagement.title'}
            >
              <Component {...pageProps} />
            </AppLayout>
          </NextThemesProvider>
        </HeroUIProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}

export default appWithTranslation(App, nextI18NextConfig);
