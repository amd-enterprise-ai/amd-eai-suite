// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { authOptions } from '@/utils/server/auth';

import ApiKeysTable from '@/components/features/api-keys/ApiKeysTable';
import CreateApiKey from '@/components/features/api-keys/CreateApiKey';
import { ActionButton } from '@/components/shared/Buttons';

import { useProject } from '@/contexts/ProjectContext';

const ApiKeysPage: React.FC = () => {
  const { t } = useTranslation('api-keys');
  const { activeProject } = useProject();

  const {
    isOpen: isCreateFormOpen,
    onOpenChange: onCreateFormOpenChange,
    onClose: onCreateFormClose,
  } = useDisclosure();

  return (
    <div className="flex flex-col w-full">
      <ApiKeysTable
        projectId={activeProject!}
        createButton={
          <ActionButton primary onPress={onCreateFormOpenChange}>
            {t('list.actions.create.title')}
          </ActionButton>
        }
      />
      <CreateApiKey
        isOpen={isCreateFormOpen}
        projectId={activeProject!}
        onClose={onCreateFormClose}
      />
    </div>
  );
};

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

  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'api-keys'])),
    },
  };
}

export default ApiKeysPage;
