// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';
import { IconChevronLeft } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import {
  getCluster as fetchCluster,
  fetchClusterWorkloadsStatusStats,
} from '@/services/app';
import { getCluster, getClusterWorkloadsStatusStats } from '@/services/server';

import { authOptions } from '@amdenterpriseai/utils/server';

import { Cluster } from '@amdenterpriseai/types';
import { WorkloadStatusStatsResponse } from '@amdenterpriseai/types';

import {
  ClusterWorkloadsStatsCard,
  ClusterWorkloadsTable,
} from '@/components/features/clusters';

interface Props {
  cluster: Cluster;
  workloadsStatusStats: WorkloadStatusStatsResponse;
}

const ClusterWorkloadsPage: React.FC<Props> = ({
  cluster,
  workloadsStatusStats,
}) => {
  const router = useRouter();
  const { id } = router.query;
  const { t } = useTranslation('clusters');
  const { push } = useRouter();

  const { data: clusterData } = useQuery<Cluster>({
    queryKey: ['cluster'],
    queryFn: () => fetchCluster(id as string),
    initialData: cluster,
  });

  const {
    data: clusterWorkloadsStatusStats,
    isLoading: isClusterWorkloadsStatusStatsLoading,
  } = useQuery<WorkloadStatusStatsResponse>({
    queryKey: ['cluster', 'workloads', 'stats'],
    queryFn: () => fetchClusterWorkloadsStatusStats(id as string),
    initialData: workloadsStatusStats,
  });

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <div className="md:py-4 lg:py-6 flex gap-3 items-center">
        <Button
          size="sm"
          isIconOnly
          onPress={() => push(`/clusters/${id}`)}
          aria-label={t('workloads.actions.back')}
        >
          <IconChevronLeft size={16} />
        </Button>
        <h2>{clusterData.name}</h2>
      </div>

      <div className="flex flex-col gap-8">
        <div className="flex grow">
          <div className="w-1/3">
            <ClusterWorkloadsStatsCard
              isLoading={isClusterWorkloadsStatusStatsLoading}
              clusterName={clusterData.name}
              totalWorkloads={clusterWorkloadsStatusStats?.totalWorkloads ?? 0}
              data={clusterWorkloadsStatusStats?.statusCounts ?? []}
            />
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <h3>{t('workloads.title')}</h3>
          <ClusterWorkloadsTable clusterId={id as string} />
        </div>
      </div>
    </div>
  );
};

export default ClusterWorkloadsPage;

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
    const [cluster, workloadsStatusStats] = await Promise.all([
      getCluster(context.params.id, session?.accessToken as string),
      getClusterWorkloadsStatusStats(
        context.params.id,
        session?.accessToken as string,
      ),
    ]);

    const translations = await serverSideTranslations(locale, [
      'common',
      'clusters',
      'workloads',
      'sharedComponents',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.clusters?.title,
        href: '/clusters',
      },
      {
        title: `${cluster.name}`,
        href: `/clusters/${cluster.id}`,
      },
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.clusters
            ?.workloads?.title,
      },
    ];

    return {
      props: {
        ...translations,
        cluster,
        workloadsStatusStats,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('Cluster not found: ' + error);
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
}
