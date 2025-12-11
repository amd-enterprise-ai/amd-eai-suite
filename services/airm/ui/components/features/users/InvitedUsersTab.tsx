// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'next-i18next';
import { useDisclosure } from '@heroui/react';

import useSystemToast from '@/hooks/useSystemToast';
import {
  deleteUser,
  fetchInvitedUsers,
  resendInvitation as resendInvitationAPI,
} from '@/services/app/users';
import { getFilteredData } from '@/utils/app/data-table';
import { APIRequestError } from '@/utils/app/errors';

import { TableColumns } from '@/types/data-table/clientside-table';
import { FilterComponentType } from '@/types/enums/filters';
import { InvitedUserTableField } from '@/types/enums/invited-user-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { InvitedUser, InvitedUsersResponse } from '@/types/users';

import { InviteUserButton } from '@/components/features/users/InviteUserButton';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import { DateDisplay } from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { useAccessControl } from '@/hooks/useAccessControl';

const invitedColumns: TableColumns<InvitedUserTableField | null> = [
  {
    key: InvitedUserTableField.EMAIL,
    sortable: true,
  },
  { key: InvitedUserTableField.INVITED_BY, sortable: true },
  { key: InvitedUserTableField.ROLES, sortable: true },
  { key: InvitedUserTableField.INVITED_AT, sortable: true },
];

interface InvitedUsersTabProps {
  initialData: InvitedUsersResponse;
  onInviteUserClick: () => void;
}

export const InvitedUsersTab = ({
  initialData,
  onInviteUserClick,
}: InvitedUsersTabProps) => {
  const { t: tInvited } = useTranslation('users', { keyPrefix: 'invited' });
  const [filter, setFilter] = useState<ClientSideDataFilter<InvitedUser>[]>([]);
  const { isInviteEnabled } = useAccessControl();
  const { smtpEnabled } = useAccessControl();

  const handleFilterChange = useCallback((filterValues: FilterValueMap) => {
    const invitedFilterableFields: (keyof InvitedUser)[] = ['email'];
    if (
      filterValues.search &&
      !(
        Array.isArray(filterValues.search) &&
        filterValues.search.length === 1 &&
        filterValues.search[0] === ''
      )
    ) {
      setFilter([
        {
          values: filterValues.search,
          compositeFields: invitedFilterableFields.map((field) => ({
            field,
          })),
        },
      ]);
    } else {
      setFilter([]);
    }
  }, []);

  // Modals for invited users
  const {
    isOpen: isCancelInvitationModalOpen,
    onOpen: onCancelInvitationModalOpen,
    onOpenChange: onCancelInvitationModalOpenChange,
  } = useDisclosure();

  const {
    isOpen: isResendInvitationModalOpen,
    onOpen: onResendInvitationModalOpen,
    onOpenChange: onResendInvitationModalOpenChange,
  } = useDisclosure();

  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const [invitationBeingActioned, setInvitationBeingActioned] =
    useState<InvitedUser>();

  // Invited users query
  const {
    data: invitedUsersData,
    isFetching: isInvitedUsersFetching,
    isRefetching: isInvitedUsersRefetching,
    refetch: refetchInvitedUsers,
    dataUpdatedAt: invitedUsersDataUpdatedAt,
  } = useQuery<InvitedUsersResponse>({
    queryKey: ['invited-users'],
    queryFn: fetchInvitedUsers,
    initialData,
  });

  // Mutations for invited users
  const { mutate: cancelInvitation, isPending: isCancelInvitationPending } =
    useMutation({
      mutationFn: deleteUser,
      onSuccess: () => {
        onCancelInvitationModalOpenChange();
        queryClient.invalidateQueries({ queryKey: ['invited-users'] });
        toast.success(tInvited('list.actions.cancel.notification.success'));
      },
      onError: (error) => {
        onCancelInvitationModalOpenChange();
        toast.error(
          tInvited('list.actions.cancel.notification.error'),
          error as APIRequestError,
        );
      },
    });

  const { mutate: resendInvitation, isPending: isResendInvitationPending } =
    useMutation({
      mutationFn: resendInvitationAPI,
      onSuccess: () => {
        onResendInvitationModalOpenChange();
        queryClient.invalidateQueries({ queryKey: ['invited-users'] });
        toast.success(tInvited('list.actions.resend.notification.success'));
      },
      onError: (error) => {
        onResendInvitationModalOpenChange();
        toast.error(
          tInvited('list.actions.resend.notification.error'),
          error as APIRequestError,
        );
      },
    });

  const filteredInvitedUsersData = useMemo(() => {
    if (invitedUsersData?.data) {
      return getFilteredData(invitedUsersData.data, filter);
    }
  }, [filter, invitedUsersData?.data]);

  const invitedUsersCustomRenderers: Partial<
    Record<
      InvitedUserTableField,
      (item: InvitedUser) => React.ReactNode | string
    >
  > = {
    [InvitedUserTableField.ROLES]: (item) => item.role,
    [InvitedUserTableField.INVITED_AT]: (item) => (
      <DateDisplay date={item.invitedAt} />
    ),
  };

  const invitedUsersActions = [
    ...(smtpEnabled
      ? [
          {
            key: 'resend',
            onPress: (i: InvitedUser) => {
              setInvitationBeingActioned(i);
              onResendInvitationModalOpen();
            },
            label: tInvited('list.actions.resend.label'),
          },
        ]
      : []),
    {
      key: 'cancel',
      className: 'text-danger',
      color: 'danger',
      onPress: (i: InvitedUser) => {
        setInvitationBeingActioned(i);
        onCancelInvitationModalOpen();
      },
      label: tInvited('list.actions.cancel.label'),
    },
  ];

  const invitedUsersFilterConfig = {
    search: {
      name: 'search',
      label: tInvited('list.filter.label'),
      placeholder: tInvited('list.filter.placeholder'),
      type: FilterComponentType.TEXT,
    },
  };

  return (
    <>
      <div className="inline-flex flex-col w-full h-full max-h-full">
        <ActionsToolbar
          filterConfig={invitedUsersFilterConfig}
          onFilterChange={handleFilterChange}
          onRefresh={refetchInvitedUsers}
          isRefreshing={isInvitedUsersFetching || isInvitedUsersRefetching}
          updatedTimestamp={invitedUsersDataUpdatedAt}
          endContent={
            isInviteEnabled ? (
              <InviteUserButton
                onClick={onInviteUserClick}
                label={tInvited('actions.addUser')}
              />
            ) : undefined
          }
        />
        {filteredInvitedUsersData && (
          <ClientSideDataTable
            data={filteredInvitedUsersData}
            className="flex-1 overflow-y-auto"
            columns={invitedColumns}
            defaultSortByField={InvitedUserTableField.EMAIL}
            customRenderers={invitedUsersCustomRenderers}
            translation={tInvited}
            idKey="id"
            isFetching={isInvitedUsersFetching || isInvitedUsersRefetching}
            rowActions={invitedUsersActions}
          />
        )}
      </div>

      <ConfirmationModal
        confirmationButtonColor="danger"
        description={tInvited('list.actions.cancel.confirmation.description')}
        title={tInvited('list.actions.cancel.confirmation.title')}
        confirmationButtonText={
          tInvited('list.actions.cancel.confirmation.confirm')!
        }
        isOpen={isCancelInvitationModalOpen}
        loading={isCancelInvitationPending}
        onConfirm={() => cancelInvitation(invitationBeingActioned?.id!)}
        onClose={onCancelInvitationModalOpenChange}
      />
      <ConfirmationModal
        confirmationButtonColor="primary"
        description={tInvited('list.actions.resend.confirmation.description')}
        title={tInvited('list.actions.resend.confirmation.title')}
        confirmationButtonText={
          tInvited('list.actions.resend.confirmation.confirm')!
        }
        isOpen={isResendInvitationModalOpen}
        loading={isResendInvitationPending}
        onConfirm={() => resendInvitation(invitationBeingActioned?.id!)}
        onClose={onResendInvitationModalOpenChange}
      />
    </>
  );
};
