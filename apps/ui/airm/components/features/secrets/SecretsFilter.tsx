// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import {
  FilterComponentType,
  SecretScope,
  SecretType,
} from '@amdenterpriseai/types';
import { FilterValueMap } from '@amdenterpriseai/types';

import { ActionsToolbar } from '@amdenterpriseai/components';

interface Props {
  onFilterChange: (filters: FilterValueMap) => void;
  actionButton: React.ReactNode;
  onRefresh: () => void;
}

export const SecretsFilter: React.FC<Props> = ({
  onFilterChange,
  actionButton,
  onRefresh,
}) => {
  const { t } = useTranslation('secrets');

  const filterConfig = useMemo(() => {
    const config: any = {
      search: {
        name: 'search',
        label: t('list.filter.search.label'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      type: {
        name: 'type',
        label: t('list.filter.type.label'),
        placeholder: t('list.filter.type.placeholder'),
        type: FilterComponentType.SELECT,
        fields: Object.values(SecretType).map((type) => ({
          key: type,
          label: t(`list.filter.type.options.${type}`),
        })),
      },
      scope: {
        name: 'scope',
        label: t('list.filter.scope.label'),
        placeholder: t('list.filter.scope.placeholder'),
        type: FilterComponentType.SELECT,
        fields: Object.values(SecretScope).map((scope) => ({
          key: scope,
          label: t(`list.filter.scope.options.${scope}`),
        })),
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

export default SecretsFilter;
