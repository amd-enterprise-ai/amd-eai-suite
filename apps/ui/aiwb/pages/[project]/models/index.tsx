// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AiwbDocsPage,
  aiwbDocumentationMapping,
  RelevantDocs,
  Tab,
  Tabs,
} from '@amdenterpriseai/components';
import React, { useCallback } from 'react';

import { GetServerSidePropsContext } from 'next';
import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { useProject } from '@/contexts/ProjectContext';

import { PageBreadcrumbs } from '@amdenterpriseai/types';

import DeployedModels from '@/components/features/models/DeployedModels';
import AIMCatalog from '@/components/features/models/AIMCatalog';
import CustomModels from '@/components/features/models/CustomModels';
import FineTuneModels from '@/components/features/models/FineTuneModels';
import { toCamelCase } from '@amdenterpriseai/utils/app';
import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';

enum ModelTab {
  AimCatalog = 'aim-catalog',
  CustomModels = 'custom-models',
  FineTuneModels = 'fine-tune-models',
  DeployedModels = 'deployed-models',
}

interface Props {
  pageBreadcrumb?: PageBreadcrumbs;
}

const ModelsPage: React.FC<Props> & WithDocumentationLink = ({
  pageBreadcrumb,
}) => {
  const { t } = useTranslation('models');
  const router = useRouter();
  const { projectPath } = useProject();

  const selectedTab = router.query.tab as string;

  const handleTabChange = useCallback(
    (key: React.Key) => {
      router.push(projectPath(`/models/${key}`));
    },
    [router, projectPath],
  );

  return (
    <div className="min-h-full flex flex-col w-full">
      <div className="flex-1 flex flex-col min-h-0">
        <Tabs
          aria-label="Models tabs"
          variant="underlined"
          color="primary"
          className="mt-8"
          selectedKey={selectedTab}
          onSelectionChange={handleTabChange}
        >
          <Tab key={ModelTab.AimCatalog} title={t('tabs.aimCatalog')}>
            <AIMCatalog />
          </Tab>
          <Tab key={ModelTab.CustomModels} title={t('tabs.customModels')}>
            <CustomModels />
          </Tab>
          <Tab key={ModelTab.FineTuneModels} title={t('tabs.fineTuneModels')}>
            <FineTuneModels />
          </Tab>
          <Tab key={ModelTab.DeployedModels} title={t('tabs.deployedModels')}>
            <DeployedModels />
          </Tab>
        </Tabs>
      </div>

      <RelevantDocs docs={aiwbDocumentationMapping[AiwbDocsPage.MODELS]} />
    </div>
  );
};

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const { query } = context;
  const locale = context.locale || 'en';

  const translations = await serverSideTranslations(locale, [
    'catalog',
    'common',
    'models',
    'sharedComponents',
    'workloads',
    'autoscaling',
  ]);

  const tab = query?.tab as string | undefined;
  const project = query?.project as string;

  if (!tab || !Object.values(ModelTab).includes(tab as ModelTab)) {
    return {
      redirect: {
        destination: `/${project}/models/${ModelTab.AimCatalog}`,
        permanent: false,
      },
    };
  }

  const breadcrumb = [
    {
      title:
        translations._nextI18Next?.initialI18nStore?.[locale]?.common?.pages
          ?.models?.title || 'Models',
    },
    {
      title:
        translations._nextI18Next?.initialI18nStore?.[locale]?.common?.pages?.[
          toCamelCase(tab)
        ]?.title || toCamelCase(tab),
    },
  ];

  return {
    props: {
      ...translations,
      pageBreadcrumb: breadcrumb,
    },
  };
}

export default ModelsPage;

ModelsPage.documentationLink = `${DOCS_WORKBENCH_BASE}/models.html`;
