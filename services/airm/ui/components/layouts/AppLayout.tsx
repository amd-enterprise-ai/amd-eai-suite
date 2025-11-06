// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';

import Head from 'next/head';

import { PageBreadcrumbs } from '@/types/navigation';

import { Sidebar } from '@/components/shared/Navigation/Sidebar';
import { AppBar } from '@/components/shared/Toolbar/AppToolbar';

interface Props {
  children: React.ReactNode;
  pageBreadcrumb?: PageBreadcrumbs;
}

const Layout = ({ pageBreadcrumb, children }: Props) => {
  return (
    <>
      <Head>
        <title>AMD Enterprise AI</title>
        <meta name="description" content="AMD Enterprise AI" />
        <meta
          name="viewport"
          content="height=device-height, width=device-width, initial-scale=1, user-scalable=no"
        />
        <link rel="icon" type="image/vnd.microsoft.icon" href="/favicon.ico" />
      </Head>
      <div className="flex overflow-hidden bg-gradient-to-b bg-white dark:bg-default-50">
        <Sidebar />
        <main className="flex flex-col w-full overflow-x-hidden h-screen">
          <AppBar pageBreadcrumb={pageBreadcrumb} />
          <div className="flex-1 md:mb-0 lg:pb-0 max-h-screen overflow-y-auto h-full px-4 md:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </>
  );
};

export default Layout;
