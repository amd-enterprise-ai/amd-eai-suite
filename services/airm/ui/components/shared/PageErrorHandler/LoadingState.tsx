// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Spinner } from '@heroui/react';

import { useTranslation } from 'next-i18next';

const LoadingState: React.FC = () => {
  const { t } = useTranslation('common');
  return (
    <div className="w-full h-full flex justify-center items-center">
      <div className="text-center">
        <Spinner size="md" color="default" />
        <p className="text-default-500">{t('charts.loading')}</p>
      </div>
    </div>
  );
};

export default LoadingState;
