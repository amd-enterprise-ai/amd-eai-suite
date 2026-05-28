// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';
import {
  createHuggingFaceSecretRequest,
  isValidHuggingFaceToken,
} from '@/lib/app/huggingface-secret';
import { SecretUseCase } from '@amdenterpriseai/types';

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

  describe('createHuggingFaceSecretRequest', () => {
    it('should create valid secret request without transforming name', () => {
      const name = 'my-test-hf-token';
      const token = 'hf_test1234567890abcdefghijklmnopqr';

      const request = createHuggingFaceSecretRequest(name, token);

      expect(request.name).toBe('my-test-hf-token');
      expect(request.useCase).toBe(SecretUseCase.HUGGING_FACE);
      expect(request.data.token).toBe(
        Buffer.from(token, 'utf-8').toString('base64'),
      );
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
        );
        expect(request.name).toBe(name);
      });
    });
  });
});
