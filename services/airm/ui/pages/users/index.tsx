// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab, Tabs, useDisclosure } from '@heroui/react';

import { GetServerSideProps } from 'next';
import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { getUsers, getInvitedUsers } from '@/services/server/users';

import { authOptions } from '@/utils/server/auth';

import { InvitedUsersResponse, UsersResponse } from '@/types/users';

import { ActiveUsersTab, InvitedUsersTab } from '@/components/features/users';
import InviteUserModal from '@/components/features/users/InviteUserModal';
import { useAccessControl } from '@/hooks/useAccessControl';

interface Props {
  users: UsersResponse;
  invitedUsers: InvitedUsersResponse;
}

const UsersPage = ({ users, invitedUsers }: Props) => {
  const { t } = useTranslation('users');
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const { isInviteEnabled } = useAccessControl();
  return (
    <>
      <div className="inline-flex flex-col w-full h-full max-h-full">
        <Tabs
          aria-label="Users tabs"
          variant="underlined"
          color="primary"
          classNames={{
            panel: !isInviteEnabled && 'py-0',
            tabList: isInviteEnabled ? 'mt-8' : 'hidden',
          }}
        >
          <Tab key="active" title={t('tabs.active')}>
            <ActiveUsersTab initialData={users} onInviteUserClick={onOpen} />
          </Tab>
          {isInviteEnabled && (
            <Tab key="invited" title={t('tabs.invited')}>
              <InvitedUsersTab
                initialData={invitedUsers}
                onInviteUserClick={onOpen}
              />
            </Tab>
          )}
        </Tabs>

        <InviteUserModal
          usersInitialData={users}
          invitedUsersInitialData={invitedUsers}
          isOpen={isOpen}
          onOpenChange={onOpenChange}
        />
      </div>
    </>
  );
};

export default UsersPage;

export const getServerSideProps: GetServerSideProps<Props> = async (
  context,
) => {
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

  try {
    const usersData = await getUsers(session.accessToken);
    const invitedUsersResponse = await getInvitedUsers(
      session?.accessToken as string,
    );

    return {
      props: {
        ...(await serverSideTranslations(context.locale ?? 'en', [
          'common',
          'users',
        ])),
        invitedUsers: invitedUsersResponse,
        users: usersData,
      },
    };
  } catch (error) {
    console.error('Error checking access management status:', error);

    // On error, redirect to dashboard
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
};
