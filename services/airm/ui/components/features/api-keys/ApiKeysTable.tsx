// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import { IconEdit, IconTrash } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deleteApiKey, fetchProjectApiKeys } from '@/services/app/api-keys';

import { getFilteredData } from '@/utils/app/data-table';
import { APIRequestError } from '@/utils/app/errors';
import { displayTimestamp } from '@/utils/app/strings';

import { ApiKey } from '@/types/api-keys';
import { TableColumns } from '@/types/data-table/table';
import { ApiKeysTableField } from '@/types/enums/api-keys-table-fields';
import { FilterComponentType } from '@/types/enums/filters';
import { SortDirection } from '@/types/enums/sort-direction';
import { ClientSideDataFilter } from '@/types/filters';

import CreateApiKey from '@/components/features/api-keys/CreateApiKey';
import DeleteApiKeyModal from '@/components/features/api-keys/DeleteApiKeyModal';
import { ClientSideDataTable } from '@/components/shared/DataTable';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

interface Props {
  projectId: string;
  createButton?: React.ReactNode;
}

const columns: TableColumns<ApiKeysTableField | null> = [
  {
    key: ApiKeysTableField.NAME,
    sortable: true,
  },
  {
    key: ApiKeysTableField.SECRET_KEY,
    sortable: false,
  },
  {
    key: ApiKeysTableField.CREATED_AT,
    sortable: true,
  },
  {
    key: ApiKeysTableField.CREATED_BY,
    sortable: true,
  },
];

const API_KEYS_QUERY_KEY = 'project-api-keys';

export const ApiKeysTable: React.FC<Props> = ({ projectId, createButton }) => {
  const { t } = useTranslation('api-keys');
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const [apiKeySelected, setApiKeySelected] = useState<ApiKey | undefined>();
  const [filters, setFilters] = useState<ClientSideDataFilter<ApiKey>[]>([]);

  const {
    isOpen: isDeleteApiKeyModalOpen,
    onOpen: onDeleteApiKeyModalOpen,
    onOpenChange,
  } = useDisclosure();

  const {
    isOpen: isEditApiKeyModalOpen,
    onOpen: onEditApiKeyModalOpen,
    onClose: onEditApiKeyModalClose,
  } = useDisclosure();

  const { mutate: deleteApiKeyMutation } = useMutation({
    mutationFn: ({
      projectId,
      apiKeyId,
    }: {
      projectId: string;
      apiKeyId: string;
    }) => deleteApiKey(projectId, apiKeyId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [API_KEYS_QUERY_KEY, projectId],
      });
      toast.success(t('list.actions.delete.notification.success'));
    },
    onError: (error) => {
      toast.error(
        t('list.actions.delete.notification.error'),
        error as APIRequestError,
      );
    },
  });

  const {
    data: apiKeysData,
    isFetching: isApiKeysLoading,
    refetch: refetchApiKeys,
    dataUpdatedAt: apiKeysUpdatedAt,
  } = useQuery({
    queryKey: [API_KEYS_QUERY_KEY, projectId],
    queryFn: () => fetchProjectApiKeys(projectId),
    enabled: !!projectId,
  });

  const filteredApiKeys = useMemo(
    () => getFilteredData(apiKeysData?.data ?? [], filters),
    [apiKeysData?.data, filters],
  );

  const customRenderers: Partial<
    Record<ApiKeysTableField, (item: ApiKey) => React.ReactNode | string>
  > = {
    [ApiKeysTableField.SECRET_KEY]: (item) => (
      <code className="text-sm font-mono">{item.truncatedKey}</code>
    ),
    [ApiKeysTableField.CREATED_AT]: (item) => {
      if (item.createdAt) {
        return displayTimestamp(new Date(item.createdAt));
      }
      return '-';
    },
  };

  const rowActions = () => [
    {
      key: 'edit',
      label: t('list.actions.edit.title'),
      color: 'default',
      startContent: <IconEdit />,
      onPress: (apiKey: ApiKey) => {
        setApiKeySelected(apiKey);
        onEditApiKeyModalOpen();
      },
    },
    {
      key: 'delete',
      label: t('list.actions.delete.title'),
      color: 'danger',
      startContent: <IconTrash />,
      onPress: (apiKey: ApiKey) => {
        setApiKeySelected(apiKey);
        onDeleteApiKeyModalOpen();
      },
    },
  ];

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        label: t('list.filters.search.placeholder'),
        placeholder: t('list.filters.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
    }),
    [t],
  );

  const handleFilterChange = (newFilters: Record<string, any>) => {
    const clientFilters: ClientSideDataFilter<ApiKey>[] = [];

    if (
      newFilters?.search &&
      newFilters.search.length > 0 &&
      !(newFilters.search.length === 1 && newFilters.search[0] === '')
    ) {
      clientFilters.push({
        field: 'name',
        values: newFilters.search,
      });
    }

    setFilters(clientFilters);
  };

  return (
    <div>
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refetchApiKeys}
        updatedTimestamp={apiKeysUpdatedAt}
        isRefreshing={isApiKeysLoading}
        endContent={createButton}
      />
      <ClientSideDataTable
        data={filteredApiKeys}
        columns={columns}
        customRenderers={customRenderers}
        defaultSortByField={ApiKeysTableField.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        rowActions={rowActions}
        translation={t}
        idKey="id"
        translationKeyPrefix="apiKeys"
        isLoading={isApiKeysLoading}
      />
      <DeleteApiKeyModal
        isOpen={isDeleteApiKeyModalOpen}
        onOpenChange={onOpenChange}
        apiKey={apiKeySelected}
        onConfirmAction={(apiKey) =>
          deleteApiKeyMutation({ projectId, apiKeyId: apiKey.id })
        }
      />
      <CreateApiKey
        isOpen={isEditApiKeyModalOpen}
        projectId={projectId}
        apiKey={apiKeySelected}
        onClose={onEditApiKeyModalClose}
      />
    </div>
  );
};

export default ApiKeysTable;
