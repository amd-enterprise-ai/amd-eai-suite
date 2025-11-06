// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Accordion, AccordionItem, cn, useDisclosure } from '@heroui/react';
import { IconCircleCheck, IconSearch, IconServer } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { fetchClusters } from '@/services/app/clusters';
import { fetchProjects } from '@/services/app/projects';
import { getClusters } from '@/services/server/clusters';
import { getProjects } from '@/services/server/projects';

import { getFilteredData } from '@/utils/app/data-table';
import { authOptions } from '@/utils/server/auth';

import { Cluster, ClusterBasicInfo, ClustersResponse } from '@/types/clusters';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { FilterComponentType } from '@/types/enums/filters';
import { QuotaStatus } from '@/types/enums/quotas';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import {
  ProjectWithResourceAllocation,
  ProjectsResponse,
} from '@/types/projects';

import CreateProjectModal from '@/components/features/projects/CreateProjectModal';
import { ProjectTable } from '@/components/features/projects';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { ActionButton } from '@/components/shared/Buttons';
import { doesDataNeedToBeRefreshed } from '@/utils/app/projects';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

interface Props {
  clusters: Cluster[];
  projects: ProjectWithResourceAllocation[];
}

type ProjectsPerCluster = {
  cluster: ClusterBasicInfo;
  projects: ProjectWithResourceAllocation[];
};

type MappedProjectsPerCluster = Record<string, ProjectsPerCluster>;

const ProjectsPage = ({ clusters, projects }: Props) => {
  const { t } = useTranslation('projects');
  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  const [filters, setFilters] = useState<
    ClientSideDataFilter<ProjectWithResourceAllocation>[]
  >([]);

  const {
    data: projectsData,
    isFetching: isProjectsDataFetching,
    refetch: refreshProjectsData,
    dataUpdatedAt: projectsDataUpdatedAt,
  } = useQuery<ProjectsResponse>({
    queryKey: ['projects'],
    queryFn: fetchProjects,
    initialData: { projects },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesDataNeedToBeRefreshed(query.state.data.projects)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const {
    data: clustersData,
    isFetching: isClustersDataFetching,
    refetch: refreshClustersData,
    dataUpdatedAt: clustersDataUpdatedAt,
  } = useQuery<ClustersResponse>({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
    initialData: { clusters },
  });

  const clusterMap: Record<string, Cluster> = useMemo(() => {
    return clustersData.clusters.reduce(
      (acc, cluster) => {
        acc[cluster.id] = cluster;
        return acc;
      },
      {} as Record<string, Cluster>,
    );
  }, [clustersData.clusters]);

  const processedAndGroupedProjects = useMemo((): MappedProjectsPerCluster => {
    let currentProjects = projectsData.projects;

    // 1. filter by name, status, cluster
    currentProjects = getFilteredData(currentProjects, filters);

    // 2. Group by clusterId
    const groupedByCluster = currentProjects.reduce((acc, project) => {
      const clusterId = project.clusterId;
      if (!clusterId) return acc; // Skip projects without a clusterId

      if (!acc[clusterId]) {
        const clusterInfo = clusterMap[clusterId];

        if (clusterInfo) {
          // Ensure clusterInfo is found before creating the group
          acc[clusterId] = {
            projects: [],
            cluster: clusterInfo as ClusterBasicInfo, // Cast here, assuming it will be valid
          };
        }
      }
      // Add project to group only if the group was successfully created
      if (acc[clusterId]) {
        acc[clusterId].projects.push(project);
      }
      return acc;
    }, {} as MappedProjectsPerCluster);

    return groupedByCluster;
  }, [projectsData, clusterMap, filters]);

  const uniqueClustersForFilter = useMemo((): ClusterBasicInfo[] => {
    if (!clustersData?.clusters) return [];

    return clustersData.clusters.map((c) => ({
      id: c.id,
      name: c.name,
      status: c.status as ClusterStatus,
      lastHeartbeatAt: c.lastHeartbeatAt,
    }));
  }, [clustersData]);

  const handleProjectCreation = () => {
    onOpenChange();
  };

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<ProjectWithResourceAllocation>[] =
      [];
    if (filters.search) {
      newFilters.push({ field: 'name', values: filters.search });
    }
    if (filters.cluster) {
      newFilters.push({
        field: 'clusterId',
        values: filters.cluster,
      });
    }
    if (filters.status) {
      newFilters.push({
        field: 'status',
        values: filters.status,
      });
    }

    setFilters(newFilters);
  }, []);

  const clusterBlocks = Object.keys(processedAndGroupedProjects);

  const defaultExpandedKeys = useMemo(() => {
    return Object.values(processedAndGroupedProjects)
      .filter((group) => group.cluster.status === ClusterStatus.HEALTHY)
      .map((group) => group.cluster.id);
  }, [processedAndGroupedProjects]);

  const NoProjectsPlaceholder = () => (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 py-10">
      <IconSearch size={48} className="mb-4" />
      <p className="text-xl font-semibold">{t('list.empty.title')}</p>
      <p>{t('list.empty.description')}</p>
    </div>
  );

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        className: 'min-w-72',
        label: t('list.filter.label'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      cluster: {
        name: 'cluster',
        label: t('list.filter.cluster.label'),
        icon: <IconServer size={14} />,
        placeholder: t('list.filter.cluster.placeholder'),
        type: FilterComponentType.SELECT,
        fields: uniqueClustersForFilter.map((item) => ({
          key: item.id,
          label: item.name,
        })),
      },
      status: {
        name: 'status',
        label: t('list.filter.status.label'),
        icon: <IconCircleCheck size={14} />,
        placeholder: t('list.filter.status.placeholder'),
        type: FilterComponentType.SELECT,
        fields: Object.values(QuotaStatus).map((status) => ({
          key: status,
          label: t(`status.${status}`),
        })),
      },
    }),
    [t, uniqueClustersForFilter],
  );

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={() => {
          refreshProjectsData();
          refreshClustersData();
        }}
        isRefreshing={isClustersDataFetching || isProjectsDataFetching}
        updatedTimestamp={Math.max(
          projectsDataUpdatedAt,
          clustersDataUpdatedAt,
        )}
        endContent={
          <ActionButton
            primary
            aria-label={t('actions.createProject') || ''}
            onPress={onOpen}
          >
            {t('actions.createProject')}
          </ActionButton>
        }
      />
      {clusterBlocks.length === 0 && filters.length > 0 ? (
        <NoProjectsPlaceholder />
      ) : (
        <Accordion
          selectionMode="multiple"
          defaultSelectedKeys={defaultExpandedKeys}
        >
          {clusterBlocks.map((clusterId) => {
            const clusterGroup = processedAndGroupedProjects[clusterId];
            if (!clusterGroup) return null;

            const { cluster, projects: clusterProjects } = clusterGroup;
            const isClusterUnavailable =
              cluster.status !== ClusterStatus.HEALTHY;

            return (
              <AccordionItem
                classNames={{
                  title: cn({
                    'text-gray-500': isClusterUnavailable,
                  }),
                }}
                title={
                  isClusterUnavailable
                    ? t('list.clusterUnavailable', { name: cluster.name })
                    : cluster.name
                }
                key={clusterId}
              >
                <ProjectTable projects={clusterProjects} />
              </AccordionItem>
            );
          })}
        </Accordion>
      )}

      <CreateProjectModal
        clusters={clustersData.clusters}
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        onProjectCreate={handleProjectCreation}
        projects={projectsData?.projects ?? projects}
      />
    </div>
  );
};

export default ProjectsPage;

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

  const projects = await getProjects(session?.accessToken as string);
  const clusters = await getClusters(session?.accessToken as string);

  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'projects'])),
      clusters: clusters?.clusters || [],
      projects: projects?.projects || [],
    },
  };
}
