// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';
import {
  createHuggingFaceSecretRequest,
  generateHuggingFaceSecretManifest,
  isValidHuggingFaceToken,
  isValidKubernetesSecretName,
} from '@/utils/app/huggingface-secret';
import { SecretScope, SecretType, SecretUseCase } from '@/types/enums/secrets';

describe('Hugging Face Secret Utils', () => {
  describe('isValidHuggingFaceToken', () => {
    it('should validate correct Hugging Face token format', () => {
      const validToken = 'hf_abcdefghijklmnopqrstuvwxyz1234567890';
      expect(isValidHuggingFaceToken(validToken)).toBe(true);
    });

    it('should reject invalid Hugging Face token format', () => {
      expect(isValidHuggingFaceToken('invalid-token')).toBe(false);
      expect(isValidHuggingFaceToken('hf_short')).toBe(false);
      expect(
        isValidHuggingFaceToken('not_hf_token123456789012345678901234567890'),
      ).toBe(false);
      expect(isValidHuggingFaceToken('')).toBe(false);
    });
  });

  describe('generateHuggingFaceSecretManifest', () => {
    it('should generate valid Kubernetes secret manifest', () => {
      const secretName = 'test-hf-token';
      const token = 'hf_test1234567890abcdefghijklmnopqr';

      const manifest = generateHuggingFaceSecretManifest(secretName, token);
      const parsedManifest = JSON.parse(manifest);

      expect(parsedManifest.apiVersion).toBe('v1');
      expect(parsedManifest.kind).toBe('Secret');
      expect(parsedManifest.metadata.name).toBe(secretName);
      expect(parsedManifest.type).toBe('Opaque');
      expect(parsedManifest.data.token).toBe(
        Buffer.from(token, 'utf-8').toString('base64'),
      );
    });
  });

  describe('createHuggingFaceSecretRequest', () => {
    it('should create valid secret request without transforming name', () => {
      const name = 'my-test-hf-token';
      const token = 'hf_test1234567890abcdefghijklmnopqr';
      const projectIds = ['project-1', 'project-2'];

      const request = createHuggingFaceSecretRequest(name, token, projectIds);

      expect(request.name).toBe('my-test-hf-token');
      expect(request.type).toBe(SecretType.KUBERNETES_SECRET);
      expect(request.scope).toBe(SecretScope.PROJECT);
      expect(request.use_case).toBe(SecretUseCase.HUGGING_FACE);
      expect(request.project_ids).toEqual(projectIds);
      expect(request.manifest).toContain('my-test-hf-token');
    });

    it('should use the name as-is without any transformation', () => {
      const testCases = [
        'valid-name',
        'valid.name',
        'valid-name.with-dots',
        'a',
        'name123',
      ];

      testCases.forEach((name) => {
        const request = createHuggingFaceSecretRequest(
          name,
          'hf_test1234567890abcdefghijklmnopqr',
          ['test-project'],
        );
        expect(request.name).toBe(name);
      });
    });
  });

  describe('isValidKubernetesSecretName', () => {
    it('should validate correct Kubernetes secret names', () => {
      const validNames = [
        'valid-name',
        'valid.name',
        'valid-name.with-dots',
        'a',
        'name123',
        '123name',
        'my-hf-token.v2',
      ];

      validNames.forEach((name) => {
        expect(isValidKubernetesSecretName(name)).toBe(true);
      });
    });

    it('should reject invalid Kubernetes secret names', () => {
      const invalidNames = [
        'Invalid-Name', // uppercase
        'invalid_name', // underscore
        'invalid name', // space
        'invalid@name', // special character
        'Token@#$%', // multiple special characters
        '-invalid', // starts with hyphen
        'invalid-', // ends with hyphen
        '.invalid', // starts with dot
        'invalid.', // ends with dot
        '', // empty string
        'UPPERCASE', // all uppercase
      ];

      invalidNames.forEach((name) => {
        expect(isValidKubernetesSecretName(name)).toBe(false);
      });
    });
  });
});
