// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { HeroUIProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';

import { appWithTranslation } from 'next-i18next';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { AppProps } from 'next/app';

import AppLayout from '@/components/layouts/AppLayout';
import PageErrorHandler from '@/components/shared/PageErrorHandler/PageErrorHandler';
import SystemToastContainer from '@/components/shared/SystemToastContainer/SystemToastContainer';
import { ProjectProvider } from '@/contexts/ProjectContext';

import '@/styles/globals.css';
import '@/styles/toastify.css';

function App({ Component, pageProps: { session, ...pageProps } }: AppProps) {
  const queryClient = new QueryClient();

  return (
    <SessionProvider session={session} refetchInterval={10 * 60}>
      <QueryClientProvider client={queryClient}>
        <ProjectProvider>
          <HeroUIProvider disableRipple>
            <NextThemesProvider
              disableTransitionOnChange
              attribute="class"
              defaultTheme="dark"
            >
              <SystemToastContainer />
              <AppLayout pageBreadcrumb={pageProps?.pageBreadcrumb}>
                <PageErrorHandler>
                  <Component {...pageProps} />
                </PageErrorHandler>
              </AppLayout>
            </NextThemesProvider>
          </HeroUIProvider>
        </ProjectProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}

export default appWithTranslation(App);
