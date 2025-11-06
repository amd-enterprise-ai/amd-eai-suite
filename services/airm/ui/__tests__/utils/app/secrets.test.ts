// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  generateMockProjectSecrets,
  generateMockSecrets,
} from '@/__mocks__/utils/secrets-mock';
import { ProjectSecretStatus, SecretStatus } from '@/types/enums/secrets';
import {
  doesProjectSecretDataNeedToBeRefreshed,
  doesSecretDataNeedToBeRefreshed,
} from '@/utils/app/secrets';

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
