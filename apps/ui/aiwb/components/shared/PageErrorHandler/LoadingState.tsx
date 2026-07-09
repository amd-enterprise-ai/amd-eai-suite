// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { PageLoader } from '@/components/shared/PageLoader';

export const LoadingState: React.FC = () => {
  const { t } = useTranslation('common');
  return (
    <PageLoader label={t('pageLoader.loading')} className="w-full h-full" />
  );
};

export default LoadingState;
