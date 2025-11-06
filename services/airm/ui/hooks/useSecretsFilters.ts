// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'next-i18next';

import { FilterComponentType } from '@/types/enums/filters';
import { SecretScope, SecretType } from '@/types/enums/secrets';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Secret } from '@/types/secrets';

interface UseSecretsFiltersConfig {
  includeScope?: boolean;
}

export const useSecretsFilters = ({
  includeScope = true,
}: UseSecretsFiltersConfig = {}) => {
  const { t } = useTranslation('secrets');
  const [filters, setFilters] = useState<ClientSideDataFilter<Secret>[]>([]);

  // Filter change handler
  const handleFilterChange = useCallback(
    (filters: FilterValueMap) => {
      const newFilters: ClientSideDataFilter<Secret>[] = [];

      if (
        filters?.search &&
        filters.search.length > 0 &&
        !(filters.search.length === 1 && filters.search[0] === '')
      ) {
        newFilters.push({
          field: 'name',
          values: filters.search,
        });
      }

      if (filters?.type && filters.type.length > 0) {
        newFilters.push({
          field: 'type',
          values: filters.type,
        });
      }

      if (includeScope && filters?.scope && filters.scope.length > 0) {
        newFilters.push({
          field: 'scope',
          values: filters.scope,
        });
      }

      setFilters(newFilters);
    },
    [includeScope],
  );

  // Filter configuration
  const filterConfig = useMemo(() => {
    const baseConfig = {
      search: {
        name: 'search',
        className: 'w-full',
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
    };

    if (includeScope) {
      return {
        ...baseConfig,
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
    }

    return baseConfig;
  }, [t, includeScope]);

  return {
    filters,
    handleFilterChange,
    filterConfig,
  };
};
