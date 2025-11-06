// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { getSecrets, getProjectSecrets } from './secrets';
import { getProjects } from './projects';

import { SecretsResponse, ProjectSecretsResponse } from '@/types/secrets';

export const getWorkbenchSecrets = async (
  accessToken: string,
  projectId: string,
): Promise<SecretsResponse> => {
  // Get project-scoped secrets for the specific project
  // This endpoint already has proper RBAC - user can only access projects they have permission to
  try {
    const projectSecretsResponse: ProjectSecretsResponse =
      await getProjectSecrets(accessToken, projectId);

    // Convert ProjectSecretsResponse to SecretsResponse format
    // Reconstruct Secret objects with projectSecrets array
    const secrets =
      projectSecretsResponse.projectSecrets?.map((ps) => ({
        ...ps.secret,
        projectSecrets: [ps], // Include the project assignment info
      })) || [];

    return {
      secrets,
    };
  } catch (error) {
    throw new Error(
      `Failed to get workbench secrets for project: ${error instanceof Error ? error.message : 'Unknown error'}`,
    );
  }
};
