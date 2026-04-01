// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab, Tabs, useDisclosure } from '@heroui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useState } from 'react';

import { GetServerSidePropsContext } from 'next';
import { getServerSession } from 'next-auth';
import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { deleteModel, finetuneModel } from '@/lib/app/models';
import { getFinetunableModels } from '@/lib/app/models';
import { useProject } from '@/contexts/ProjectContext';

import { authOptions } from '@amdenterpriseai/utils/server';

import { CatalogItem } from '@amdenterpriseai/types';
import { Model, ModelFinetuneParams } from '@amdenterpriseai/types';
import { PageBreadcrumbs } from '@amdenterpriseai/types';

import { DeployWorkloadDrawer } from '@/components/features/catalog/DeployWorkloadDrawer';
import DeployedModels from '@/components/features/models/DeployedModels';
import AIMCatalog from '@/components/features/models/AIMCatalog';
import CustomModels from '@/components/features/models/CustomModels';
import DeleteModelModal from '@/components/features/models/DeleteModelModal';
import FinetuneDrawer from '@/components/features/models/FinetuneDrawer';
import { RelevantDocs } from '@amdenterpriseai/components';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import { toCamelCase } from '@amdenterpriseai/utils/app';

enum ModelTab {
  AimCatalog = 'aim-catalog',
  CustomModels = 'custom-models',
  DeployedModels = 'deployed-models',
}

interface Props {
  pageBreadcrumb?: PageBreadcrumbs;
}

const ModelsPage: React.FC<Props> = ({ pageBreadcrumb }) => {
  const { t } = useTranslation('models');
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();
  const { activeProject } = useProject();

  const [currentCatalogItem, setCurrentCatalogItem] = useState<
    CatalogItem | undefined
  >(undefined);
  const [currentModelForModal, setCurrentModelForModal] = useState<
    Model | undefined
  >(undefined);
  const [currentModelForDeletion, setCurrentModelForDeletion] = useState<
    Model | undefined
  >(undefined);

  const finetuneDisclosure = useDisclosure();
  const deployDisclosure = useDisclosure();
  const deleteDisclosure = useDisclosure();

  const { data: finetunableModelsResponse } = useQuery({
    queryKey: ['models', 'finetunable'],
    queryFn: (): Promise<string[]> => getFinetunableModels(),
  });

  const finetuneModelMutation = useMutation({
    mutationFn: async (variables: {
      id: string;
      params: ModelFinetuneParams;
    }) => {
      if (!activeProject) {
        throw new Error('No active project selected');
      }
      return finetuneModel(variables.id, variables.params, activeProject);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'models'],
      });
      toast.success(
        t(
          'customModels.list.actions.finetune.notification.success',
          'Adapter fine-tuning started',
        ),
      );
      finetuneDisclosure.onClose();
    },
    onError: (error) => {
      toast.error(
        t(
          'customModels.list.actions.finetune.notification.error',
          'Error fine-tuning model',
        ),
      );
      console.error('Error fine-tuning model:', error);
    },
  });

  const deleteModelMutation = useMutation({
    mutationFn: async (variables: { id: string }) => {
      if (!activeProject) {
        throw new Error('No active project selected');
      }

      return new Promise<void>(async (resolve, reject) => {
        try {
          resolve(await deleteModel(variables.id, activeProject));
        } catch (error: unknown) {
          if (error instanceof APIRequestError) {
            reject(error.message);
          } else {
            reject(error);
          }
        }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'models'],
      });
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'workloads'],
      });
      toast.success(
        t(
          'customModels.list.actions.delete.notification.success',
          'Model deleted successfully',
        ),
      );
      deleteDisclosure.onClose();
    },
    onError: (error: string) => {
      toast.error(
        error ||
          t(
            'customModels.list.actions.delete.notification.error',
            'Error deleting model',
          ),
      );
      console.error('Error deleting model:', error);
    },
  });

  const handleOpenFinetuneModal = useCallback(
    (model?: Model) => {
      setCurrentModelForModal(model);
      finetuneDisclosure.onOpen();
    },
    [finetuneDisclosure],
  );

  const handleOpenDeployModal = useCallback(
    (catalogItem: CatalogItem) => {
      setCurrentCatalogItem(catalogItem);
      deployDisclosure.onOpen();
    },
    [deployDisclosure],
  );

  const handleOpenDeleteModal = useCallback(
    (model: Model) => {
      setCurrentModelForDeletion(model);
      deleteDisclosure.onOpen();
    },
    [deleteDisclosure],
  );

  const selectedTab = router.query.tab as string;

  const handleTabChange = useCallback(
    (key: React.Key) => {
      router.push(`/models/${key}`, undefined, { shallow: true });
    },
    [router],
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
            <CustomModels
              onOpenDeployModal={handleOpenDeployModal}
              onOpenFinetuneModal={handleOpenFinetuneModal}
              onOpenDeleteModal={handleOpenDeleteModal}
              finetunableModels={finetunableModelsResponse || []}
            />
          </Tab>
          <Tab key={ModelTab.DeployedModels} title={t('tabs.deployedModels')}>
            <DeployedModels />
          </Tab>
        </Tabs>
      </div>

      <FinetuneDrawer
        isOpen={finetuneDisclosure.isOpen}
        onOpenChange={finetuneDisclosure.onOpenChange}
        model={currentModelForModal}
        finetunableModels={finetunableModelsResponse || []}
        onConfirmAction={({
          id,
          params,
        }: {
          id: string;
          params: ModelFinetuneParams;
        }) => {
          const modelIdToFinetune = currentModelForModal?.id || id;
          finetuneModelMutation.mutate({ id: modelIdToFinetune, params });
        }}
      />

      {currentCatalogItem && (
        <DeployWorkloadDrawer
          enableResourceAllocation={false}
          isModelDeployment={true}
          isOpen={deployDisclosure.isOpen}
          onClose={deployDisclosure.onClose}
          onDeployed={() => {
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'workloads'],
            });
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'models'],
            });
          }}
          onDeploying={() => {
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'workloads'],
            });
          }}
          catalogItem={currentCatalogItem}
        />
      )}

      <DeleteModelModal
        isOpen={deleteDisclosure.isOpen}
        onOpenChange={deleteDisclosure.onOpenChange}
        model={currentModelForDeletion}
        onConfirmAction={({ id }: { id: string }) => {
          deleteModelMutation.mutate({ id });
        }}
      />
      <RelevantDocs page="models" />
    </div>
  );
};

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const { req, res, query } = context;
  const locale = context.locale || 'en';

  const session = await getServerSession(req, res, authOptions);

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

  const translations = await serverSideTranslations(locale, [
    'catalog',
    'common',
    'models',
    'sharedComponents',
    'workloads',
    'autoscaling',
  ]);

  const tab = query?.tab as string | undefined;

  if (!tab || !Object.values(ModelTab).includes(tab as ModelTab)) {
    return {
      redirect: {
        destination: `/models/${ModelTab.AimCatalog}`,
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
