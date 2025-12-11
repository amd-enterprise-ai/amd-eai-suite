// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { FilterComponentType } from '@/types/enums/filters';
import { FilterValueMap } from '@/types/filters';

import ActionsToolbar from '@/components/shared/Toolbar/ActionsToolbar';

interface Props {
  isInProjects?: boolean;
  onFilterChange: (filters: FilterValueMap) => void;
  actionButton?: React.ReactNode;
  onRefresh: () => void;
}

export const StoragesListFilter: React.FC<Props> = ({
  onFilterChange,
  actionButton,
  onRefresh,
}) => {
  const { t } = useTranslation('storages');

  const filterConfig = useMemo(() => {
    const config: any = {
      search: {
        name: 'search',
        label: t('list.filter.search.label'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
    };

    return config;
  }, [t]);

  return (
    <ActionsToolbar
      filterConfig={filterConfig}
      onFilterChange={onFilterChange}
      endContent={actionButton}
      onRefresh={onRefresh}
    />
  );
};

export default StoragesListFilter;
