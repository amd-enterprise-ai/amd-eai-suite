// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { authOptions } from '@amdenterpriseai/utils/server';
import { WorkbenchSecretsPageContent } from '@/components/features/secrets/WorkbenchSecretsPageContent';
import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';

const WorkbenchSecretsPage: React.FC & WithDocumentationLink = () => {
  return <WorkbenchSecretsPageContent />;
};

export default WorkbenchSecretsPage;

WorkbenchSecretsPage.documentationLink = `${DOCS_WORKBENCH_BASE}/secrets.html`;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'secrets',
        'sharedComponents',
      ])),
    },
  };
}
