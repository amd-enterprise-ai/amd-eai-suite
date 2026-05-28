// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { authOptions } from '@amdenterpriseai/utils/server';

import ApiKeysTable from '@/components/features/api-keys/ApiKeysTable';
import CreateApiKey from '@/components/features/api-keys/CreateApiKey';
import {
  RelevantDocs,
  AiwbDocsPage,
  aiwbDocumentationMapping,
} from '@amdenterpriseai/components';
import { ActionButton } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';

const ApiKeysPage: React.FC & WithDocumentationLink = () => {
  const { t } = useTranslation('api-keys');
  const { activeProject, clusterAuthEnabled } = useProject();

  const {
    isOpen: isCreateFormOpen,
    onOpenChange: onCreateFormOpenChange,
    onClose: onCreateFormClose,
  } = useDisclosure();

  if (!clusterAuthEnabled) {
    return (
      <div className="min-h-full flex flex-col w-full items-center justify-center">
        <p className="text-default-500">{t('list.clusterAuthDisabled')}</p>
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col w-full">
      <div className="flex-1 flex flex-col min-h-0">
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
      <RelevantDocs docs={aiwbDocumentationMapping[AiwbDocsPage.API_KEYS]} />
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
      ...(await serverSideTranslations(locale, [
        'common',
        'api-keys',
        'sharedComponents',
      ])),
    },
  };
}

export default ApiKeysPage;

ApiKeysPage.documentationLink = `${DOCS_WORKBENCH_BASE}/api-keys.html`;
