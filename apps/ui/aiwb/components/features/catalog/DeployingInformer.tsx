// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardFooter, CardHeader, Divider } from '@heroui/react';
import { IconExternalLink } from '@tabler/icons-react';
import { ActionButton } from '@amdenterpriseai/components';
import type { TFunction } from 'next-i18next';
import { useCallback } from 'react';

interface Props {
  name: string;
  isDeployed: boolean;
  workloadId: string;
  workloadData: any;
  t: TFunction;
}

const DeployingInformer = (props: Props) => {
  const { name, isDeployed, workloadId, workloadData, t } = props;
  const handleLaunch = useCallback((): void => {
    if (!workloadId) return;
    const workloadURL = workloadData?.endpoints?.external;
    if (workloadURL) window.open(workloadURL, '_blank');
  }, [workloadId, workloadData]);

  return (
    <div className="flex flex-col gap-4 mt-4">
      <Card radius="md" shadow="sm">
        <CardHeader className="text-lg font-semibold">{name}</CardHeader>
        <Divider />
        <CardBody className="text-md text-gray-500">
          {!isDeployed
            ? t('deployModal.deploymentStatus.deployingMessage')
            : t('deployModal.deploymentStatus.readyMessage')}
        </CardBody>
        <Divider />
        <CardFooter>
          <ActionButton
            primary
            icon={<IconExternalLink size={16} stroke={2} />}
            onPress={handleLaunch}
            isLoading={!isDeployed}
          >
            {isDeployed
              ? t('deployModal.deploymentStatus.launchButtonReady')
              : t('deployModal.deploymentStatus.launchButtonPending')}
          </ActionButton>
        </CardFooter>
      </Card>
    </div>
  );
};

export default DeployingInformer;
