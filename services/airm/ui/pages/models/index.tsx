// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab, Tabs, useDisclosure } from '@heroui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import {
  deleteModel,
  finetuneModel,
  getFinetunableModels,
} from '@/services/app/models';
import { useProject } from '@/contexts/ProjectContext';

import { authOptions } from '@/utils/server/auth';

import { CatalogItem } from '@/types/catalog';
import { Model, ModelFinetuneParams } from '@/types/models';

import { DeployWorkloadDrawer } from '@/components/features/catalog/DeployWorkloadDrawer';
import DeployedModels from '@/components/features/models/DeployedModels';
import AIMCatalog from '@/components/features/models/AIMCatalog';
import CustomModels from '@/components/features/models/CustomModels';
import DeleteModelModal from '@/components/features/models/DeleteModelModal';
import FinetuneDrawer from '@/components/features/models/FinetuneDrawer';
import { APIRequestError } from '@/utils/app/errors';

const ModelsPage = () => {
  const { t } = useTranslation('models');
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
    queryKey: ['project', activeProject, 'finetunable-models'],
    queryFn: (): Promise<string[]> => getFinetunableModels(activeProject!),
    enabled: !!activeProject,
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
        queryKey: ['project', activeProject, 'community-models'],
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

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <Tabs
        aria-label="Models tabs"
        variant="underlined"
        color="primary"
        className="mt-8"
      >
        <Tab key="aimCatalog" title={t('tabs.aimCatalog')}>
          <AIMCatalog />
        </Tab>
        <Tab key="customModels" title={t('tabs.customModels')}>
          <CustomModels
            onOpenDeployModal={handleOpenDeployModal}
            onOpenFinetuneModal={handleOpenFinetuneModal}
            onOpenDeleteModal={handleOpenDeleteModal}
            finetunableModels={finetunableModelsResponse || []}
          />
        </Tab>
        <Tab key="deployedModels" title={t('tabs.deployedModels')}>
          <DeployedModels />
        </Tab>
      </Tabs>

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
    </div>
  );
};

export async function getServerSideProps(context: {
  req: any;
  res: any;
  locale: any;
}) {
  const { req, res, locale } = context;

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

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'catalog',
        'common',
        'models',
        'workloads',
      ])),
    },
  };
}

export default ModelsPage;
