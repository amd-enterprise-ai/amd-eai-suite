// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import {
  generateMockProjectSecrets,
  generateMockSecrets,
} from '@/__mocks__/utils/secrets-mock';
import {
  doesProjectSecretDataNeedToBeRefreshed,
  doesSecretDataNeedToBeRefreshed,
  isDuplicateSecret,
} from '@/utils/secrets';
import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
} from '@/types/enums/secrets';

describe('doesSecretDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesSecretDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if an entry has status Pending', () => {
    const secrets = generateMockSecrets(2);
    secrets[0].status = SecretStatus.PENDING;
    expect(doesSecretDataNeedToBeRefreshed(secrets)).toBe(true);
  });
  it('should return true if an entry has status Deleting', () => {
    const secrets = generateMockSecrets(2);
    secrets[0].status = SecretStatus.DELETING;
    expect(doesSecretDataNeedToBeRefreshed(secrets)).toBe(true);
  });

  it('should return true if an entry has status Partially Synced', () => {
    const secrets = generateMockSecrets(2);
    secrets[0].status = SecretStatus.PARTIALLY_SYNCED;
    expect(doesSecretDataNeedToBeRefreshed(secrets)).toBe(true);
  });

  it('should return false if no entry has status Pending, Deleting or Partially Synced', () => {
    const secrets = generateMockSecrets(1);
    secrets[0].status = SecretStatus.SYNCED;
    expect(doesSecretDataNeedToBeRefreshed(secrets)).toBe(false);
  });
});

describe('doesProjectSecretDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesProjectSecretDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if an entry has status Pending', () => {
    const secrets = generateMockProjectSecrets(2);
    secrets[0].status = ProjectSecretStatus.PENDING;
    expect(doesProjectSecretDataNeedToBeRefreshed(secrets)).toBe(true);
  });
  it('should return true if an entry has status Deleting', () => {
    const secrets = generateMockProjectSecrets(2);
    secrets[0].status = ProjectSecretStatus.DELETING;
    expect(doesProjectSecretDataNeedToBeRefreshed(secrets)).toBe(true);
  });

  it('should return false if no entry has status Pending or Deleting', () => {
    const secrets = generateMockProjectSecrets(1);
    secrets[0].status = ProjectSecretStatus.SYNCED;
    expect(doesProjectSecretDataNeedToBeRefreshed(secrets)).toBe(false);
  });
});

describe('isDuplicateSecret', () => {
  describe('Organization scope (no project provided)', () => {
    it('should return true when organization secret with same name and type exists', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.ORGANIZATION;

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(true);
    });

    it('should return false when organization secret has same name but different type', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.ORGANIZATION;

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(false);
    });

    it('should return false when organization secret has different name but same type', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'other-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.ORGANIZATION;

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(false);
    });

    it('should return false when only project-scoped secrets exist', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, 'project-1');

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(false);
    });

    it('should return false when secrets array is empty', () => {
      expect(
        isDuplicateSecret(
          [],
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(false);
    });

    it('should return true when multiple org secrets exist and one matches', () => {
      const secrets = generateMockSecrets(3);
      secrets[0].name = 'secret-1';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.ORGANIZATION;
      secrets[1].name = 'my-secret';
      secrets[1].type = SecretType.EXTERNAL_SECRET;
      secrets[1].scope = SecretScope.ORGANIZATION;
      secrets[2].name = 'secret-3';
      secrets[2].type = SecretType.KUBERNETES_SECRET;
      secrets[2].scope = SecretScope.ORGANIZATION;

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.ORGANIZATION,
        ),
      ).toBe(true);
    });
  });

  describe('Project scope (project provided)', () => {
    const projectId = 'project-1';

    it('should return true when project secret with same name and type exists in same project', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.KUBERNETES_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, projectId);

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(true);
    });

    it('should return false when project secret has same name and type but in different project', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.KUBERNETES_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, 'project-2');

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });

    it('should return false when project secret has same name but different type in same project', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, projectId);

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });

    it('should return false when project secret has different name but same type in same project', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'other-secret';
      secrets[0].type = SecretType.KUBERNETES_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, projectId);

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });

    it('should return false when only organization-scoped secrets exist', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.EXTERNAL_SECRET;
      secrets[0].scope = SecretScope.ORGANIZATION;

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });

    it('should return false when project secret has empty projectSecrets array', () => {
      const secrets = generateMockSecrets(1);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.KUBERNETES_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = [];

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });

    it('should return true when multiple project secrets exist and one matches same project', () => {
      const secrets = generateMockSecrets(3);
      secrets[0].name = 'my-secret';
      secrets[0].type = SecretType.KUBERNETES_SECRET;
      secrets[0].scope = SecretScope.PROJECT;
      secrets[0].projectSecrets = generateMockProjectSecrets(1, 'project-2');
      secrets[1].name = 'my-secret';
      secrets[1].type = SecretType.KUBERNETES_SECRET;
      secrets[1].scope = SecretScope.PROJECT;
      secrets[1].projectSecrets = generateMockProjectSecrets(1, projectId);
      secrets[2].name = 'other-secret';
      secrets[2].type = SecretType.KUBERNETES_SECRET;
      secrets[2].scope = SecretScope.PROJECT;
      secrets[2].projectSecrets = generateMockProjectSecrets(1, projectId);

      expect(
        isDuplicateSecret(
          secrets,
          'my-secret',
          SecretType.KUBERNETES_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(true);
    });

    it('should return false when secrets array is empty', () => {
      expect(
        isDuplicateSecret(
          [],
          'my-secret',
          SecretType.EXTERNAL_SECRET,
          SecretScope.PROJECT,
          projectId,
        ),
      ).toBe(false);
    });
  });
});
