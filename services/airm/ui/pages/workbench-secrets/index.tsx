// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { authOptions } from '@/utils/server/auth';

import { SecretsResponse } from '@/types/secrets';

import { WorkbenchSecretsPageContent } from '@/components/features/secrets/WorkbenchSecretsPageContent';

interface Props {
  secrets: SecretsResponse;
}

const WorkbenchSecretsPage: React.FC<Props> = ({ secrets }) => {
  return (
    <WorkbenchSecretsPageContent initialSecrets={secrets || { secrets: [] }} />
  );
};

export default WorkbenchSecretsPage;

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

  // Return empty secrets initially - client will fetch based on selected project
  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'secrets'])),
      secrets: { secrets: [] },
    },
  };
}
