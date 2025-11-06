// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, Divider, Tab, Tabs } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import { getCluster as fetchCluster } from '@/services/app/clusters';
import { fetchProject } from '@/services/app/projects';
import { getCluster } from '@/services/server/clusters';
import { getProject } from '@/services/server/projects';

import {
  getProjectDashboardUrl,
  getProjectEditUrl,
} from '@/utils/app/projects';
import { authOptions } from '@/utils/server/auth';

import { Cluster } from '@/types/clusters';

import { ProjectWithMembers } from '@/types/projects';

import DeleteProject from '@/components/features/projects/DeleteProject';
import ReducedWidthLayout from '@/components/layouts/ReducedWidthLayout';

import {
  InvitedUsers,
  Members,
  ProjectSecrets,
  ProjectStorages,
} from '@/components/features/projects';
import { useAccessControl } from '@/hooks/useAccessControl';
import { IconChevronLeft } from '@tabler/icons-react';
import { getProjectSecrets, getSecrets } from '@/services/server/secrets';
import { getProjectStorages, getStorages } from '@/services/server/storages';
import {
  ProjectSecretsResponse,
  ProjectSecretWithParentSecret,
  Secret,
  SecretsResponse,
} from '@/types/secrets';
import { ProjectStorageWithParentStorage, Storage } from '@/types/storages';
import ProjectQuotaForm from '@/components/features/projects/ProjectQuotaForm';
import ProjectBasicInfoForm from '@/components/features/projects/ProjectBasicInfoForm';
import { fetchProjectSecrets, fetchSecrets } from '@/services/app/secrets';

const tranlationKeySet = 'projects';

interface Props {
  project: ProjectWithMembers;
  cluster: Cluster;
}

interface Props {
  project: ProjectWithMembers;
  cluster: Cluster;
  projectSecrets: ProjectSecretWithParentSecret[];
  projectStorages: ProjectStorageWithParentStorage[];
  secrets: Secret[];
  storages: Storage[];
}

const ProjectEditPage: React.FC<Props> = ({
  project,
  cluster,
  projectSecrets,
  projectStorages,
  secrets,
  storages,
}) => {
  const router = useRouter();
  const { id } = router.query;
  const { t } = useTranslation(tranlationKeySet);
  const { isInviteEnabled } = useAccessControl();
  const { push } = useRouter();

  const { data: projectData } = useQuery<ProjectWithMembers>({
    queryKey: ['project'],
    queryFn: () => fetchProject(id as string),
    initialData: project,
  });

  const { data: clusterData } = useQuery<Cluster>({
    queryKey: ['cluster'],
    queryFn: () => fetchCluster(cluster.id as string),
    initialData: cluster,
  });

  const { data: secretsData } = useQuery<SecretsResponse>({
    queryKey: ['secrets'],
    queryFn: () => fetchSecrets(),
    initialData: {
      secrets,
    },
  });

  const { data: projectSecretsData } = useQuery<ProjectSecretsResponse>({
    queryKey: ['projectSecrets', project.id],
    queryFn: () => fetchProjectSecrets(project.id as string),
    initialData: {
      projectSecrets,
    },
  });

  return (
    <div className="flex gap-8 mt-8">
      <div className="flex-1 min-w-0">
        <div className="flex gap-3 items-center">
          <Button
            size="sm"
            isIconOnly
            onPress={() => push(`/projects/${project.id}`)}
          >
            <IconChevronLeft size={16} />
          </Button>
          <h2>{t('settings.title')}</h2>
        </div>

        <Tabs
          placement={'top'}
          aria-label={t('tab.title')}
          variant="underlined"
          classNames={{
            tabWrapper: 'w-full mt-8',
            panel: 'overflow-y-scroll h-full w-full mt-4',
            tabList: 'overflow-hidden',
            tab: 'overflow-hidden',
          }}
          color="primary"
        >
          <Tab key="quota" title={t('tab.quota.title')}>
            <ReducedWidthLayout padded={false}>
              <ProjectQuotaForm project={projectData} cluster={clusterData} />
            </ReducedWidthLayout>
          </Tab>
          <Tab key="secrets" title={t('tab.secrets.title')}>
            <ProjectSecrets
              projectSecrets={projectSecretsData.projectSecrets}
              project={projectData}
              secrets={secretsData.secrets}
            />
          </Tab>
          <Tab key="storages" title={t('tab.storages.title')}>
            <ProjectStorages
              project={projectData}
              projectStorages={projectStorages}
              secrets={secrets}
              storages={storages}
            />
          </Tab>
          <Tab key="users" title={t('tab.users.title')}>
            <Members project={projectData} />
            {isInviteEnabled && <InvitedUsers project={projectData} />}
          </Tab>
          <Tab key="general" title={t('tab.general.title')}>
            <ReducedWidthLayout padded={false} className="flex flex-col gap-8">
              <ProjectBasicInfoForm
                project={projectData}
                cluster={clusterData}
              />
              <section id="delete-project" className="scroll-mt-6">
                <h2 className="text-lg text-danger font-semibold mb-3">
                  {t('settings.form.deleteProject.title')}
                </h2>
                <Divider />
                <div className="flex flex-col gap-6 my-3">
                  <DeleteProject project={projectData} />
                </div>
              </section>
            </ReducedWidthLayout>
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};

export default ProjectEditPage;

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

  try {
    const project = await getProject(
      context.params.id,
      session?.accessToken as string,
    );
    const clusterResponse = await getCluster(
      project.clusterId,
      session?.accessToken as string,
    );

    const projectSecrets = await getProjectSecrets(
      session?.accessToken as string,
      context.params.id,
    );

    const secrets = await getSecrets(session?.accessToken as string);

    const storages = await getStorages(session?.accessToken as string);

    const projectStorages = await getProjectStorages(
      session?.accessToken as string,
      context.params.id,
    );

    const translations = await serverSideTranslations(locale, [
      'common',
      'projects',
      'users',
      'secrets',
      'storages',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.['projects']
            ?.title,
        href: '/projects',
      },
      {
        title: `${project.name}`,
        href: getProjectDashboardUrl(context.params.id),
      },
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.['projects']
            ?.settings.navigation,
        href: getProjectEditUrl(context.params.id),
      },
    ];

    return {
      props: {
        ...translations,
        cluster: clusterResponse,
        project,
        pageBreadcrumb: breadcrumb,
        secrets: secrets?.secrets || [],
        storages: storages?.storages || [],
        projectSecrets: projectSecrets?.projectSecrets || [],
        projectStorages: projectStorages?.projectStorages || [],
      },
    };
  } catch (error) {
    console.error('Project not found: ' + error);
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
}
