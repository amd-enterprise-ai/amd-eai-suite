// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NoDataDisplay } from '@/components/shared/DataTable';
import { ProjectSecret, Secret } from '@/types/secrets';
import { Tooltip } from '@heroui/react';
import React from 'react';

interface Props {
  secret?: Secret;
}

export const SecretProjectAssignedTo: React.FC<Props> = ({ secret }) => {
  const projectSecretCount = secret?.projectSecrets.length ?? 0;

  if (!secret || !secret?.projectSecrets || projectSecretCount === 0) {
    return <NoDataDisplay />;
  }

  if (projectSecretCount === 1) {
    return <span>{secret.projectSecrets[0]?.projectName}</span>;
  }

  return (
    <Tooltip
      content={
        <ul className="p-2 list-disc list-inside">
          {secret.projectSecrets.map((projectSecret: ProjectSecret) => (
            <li key={projectSecret.id}>{projectSecret.projectName}</li>
          ))}
        </ul>
      }
      placement="top"
    >
      <span className="cursor-pointer underline">{`${projectSecretCount} projects`}</span>
    </Tooltip>
  );
};

export default SecretProjectAssignedTo;
