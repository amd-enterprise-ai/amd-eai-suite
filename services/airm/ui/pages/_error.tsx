// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextPageContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import ErrorMessage from '@/components/shared/PageErrorHandler/ErrorMessage';

interface Props {
  error: string;
}

function Error({ error }: Props) {
  return <ErrorMessage code="service" message={error} />;
}

export async function getStaticProps({ locale, err }: NextPageContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', ['common'])),
      error: err?.message || 'An unknown error occurred',
    },
  };
}

export default Error;
