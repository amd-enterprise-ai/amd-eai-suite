// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FieldErrors, FieldValues } from 'react-hook-form';

import {
  type DependencyMap,
  selectiveZodResolver,
} from '@/components/shared/ManagedForm/selectiveZodResolver';

import { z } from 'zod';

// Helper type to assert that errors object has the expected structure
type AssertedErrors<T extends FieldValues> = FieldErrors<T> &
  Record<string, any>;

// Helper function to safely access errors
const getErrors = <T extends FieldValues>(
  errors: {} | FieldErrors<T>,
): AssertedErrors<T> => {
  return errors as AssertedErrors<T>;
};

describe('selectiveZodResolver', () => {
  const basicSchema = z.object({
    username: z.string().min(3, 'Username must be at least 3 characters'),
    email: z.string().email('Invalid email format'),
    age: z.number().min(18, 'Must be at least 18'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  });

  const schemaWithRefine = basicSchema.refine(
    (data) => data.password === data.confirmPassword,
    {
      message: "Passwords don't match",
      path: ['confirmPassword'],
    },
  );

  const validFormData = {
    username: 'testuser',
    email: 'test@example.com',
    age: 25,
    password: 'password123',
    confirmPassword: 'password123',
  };

  const invalidFormData = {
    username: 'ab', // too short
    email: 'invalid-email',
    age: 16, // too young
    password: '123', // too short
    confirmPassword: 'different',
  };

  const createMockResolverOptions = (names?: string[]) => ({
    names: names as any,
    criteriaMode: 'firstError' as const,
    fields: {},
    shouldUseNativeValidation: false,
  });

  const createMockContext = () => ({
    abort: new AbortController(),
  });

  describe('Basic validation', () => {
    it('should validate successfully with valid data', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions();
      const context = createMockContext();

      const result = await resolver(validFormData, context, options);

      expect(result.errors).toEqual({});
      expect(result.values).toEqual(expect.objectContaining(validFormData));
    });

    it('should return errors for invalid data', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions();
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(errors.email).toEqual({
        message: 'Invalid email format',
        type: 'invalid_string',
      });
      expect(errors.age).toEqual({
        message: 'Must be at least 18',
        type: 'too_small',
      });
      expect(errors.password).toEqual({
        message: 'Password must be at least 8 characters',
        type: 'too_small',
      });
      expect(result.values).toEqual({});
    });
  });

  describe('Selective validation', () => {
    it('should validate only specified fields when names are provided', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      // Should only validate username field
      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      // Should not validate other fields
      expect(errors.email).toBeUndefined();
      expect(errors.age).toBeUndefined();
      expect(errors.password).toBeUndefined();
      expect(result.values).toEqual({});
    });

    it('should validate multiple specified fields', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions(['username', 'email']);
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(errors.email).toEqual({
        message: 'Invalid email format',
        type: 'invalid_string',
      });
      // Should not validate unspecified fields
      expect(errors.age).toBeUndefined();
      expect(errors.password).toBeUndefined();
      expect(result.values).toEqual({});
    });

    it('should validate only valid fields when some are valid and some are invalid', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions(['username', 'email']);
      const context = createMockContext();

      const mixedData = {
        ...validFormData,
        username: 'ab', // invalid
      };

      const result = await resolver(mixedData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(errors.email).toBeUndefined(); // Valid field should not have errors
      expect(result.values).toEqual({});
    });
  });

  describe('Dependency map functionality', () => {
    it('should validate dependent fields when base field changes', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword'],
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['password']);
      const context = createMockContext();

      const dataWithMismatchedPasswords = {
        ...validFormData,
        password: 'newpassword123',
        confirmPassword: 'oldpassword123',
      };

      const result = await resolver(
        dataWithMismatchedPasswords,
        context,
        options,
      );
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.confirmPassword).toEqual({
        message: "Passwords don't match",
        type: 'custom',
      });
      expect(result.values).toEqual({});
    });

    it('should handle multiple dependencies for a single field', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword', 'username'], // username added as artificial dependency
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['password']);
      const context = createMockContext();

      const dataWithInvalidDependencies = {
        ...validFormData,
        password: 'newpassword123',
        confirmPassword: 'mismatch',
        username: 'ab', // invalid
      };

      const result = await resolver(
        dataWithInvalidDependencies,
        context,
        options,
      );
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.confirmPassword).toEqual({
        message: "Passwords don't match",
        type: 'custom',
      });
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(result.values).toEqual({});
    });

    it('should handle multiple fields with dependencies', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword'],
        username: ['email'],
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['password', 'username']);
      const context = createMockContext();

      const dataWithMultipleIssues = {
        ...validFormData,
        password: 'newpassword123',
        confirmPassword: 'mismatch',
        username: 'ab',
        email: 'invalid-email',
      };

      const result = await resolver(dataWithMultipleIssues, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.confirmPassword).toEqual({
        message: "Passwords don't match",
        type: 'custom',
      });
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(errors.email).toEqual({
        message: 'Invalid email format',
        type: 'invalid_string',
      });
      expect(result.values).toEqual({});
    });

    it('should not validate dependencies when base field is not in validation scope', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword'],
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['username']); // Only username, not password
      const context = createMockContext();

      const dataWithMismatchedPasswords = {
        ...validFormData,
        username: 'ab', // invalid
        password: 'newpassword123',
        confirmPassword: 'oldpassword123',
      };

      const result = await resolver(
        dataWithMismatchedPasswords,
        context,
        options,
      );
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      // Should not validate password/confirmPassword since password is not in scope
      expect(errors.confirmPassword).toBeUndefined();
      expect(result.values).toEqual({});
    });
  });

  describe('Edge cases', () => {
    it('should handle empty dependency map', async () => {
      const resolver = selectiveZodResolver(basicSchema, {});
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(result.values).toEqual({});
    });

    it('should handle undefined dependency map', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(result.values).toEqual({});
    });

    it('should handle fields with no dependencies defined', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword'],
      };
      const resolver = selectiveZodResolver(basicSchema, dependencyMap);
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username must be at least 3 characters',
        type: 'too_small',
      });
      expect(result.values).toEqual({});
    });

    it('should handle empty field names array', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions([]);
      const context = createMockContext();

      const result = await resolver(validFormData, context, options);

      // Should validate no fields and return success
      expect(result.errors).toEqual({});
      expect(result.values).toEqual(expect.objectContaining(validFormData));
    });

    it('should handle undefined field names (fallback to all fields)', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions(); // names is undefined
      const context = createMockContext();

      const result = await resolver(invalidFormData, context, options);
      const errors = getErrors(result.errors);

      // Should validate all fields
      expect(result.errors).toBeDefined();
      expect(errors.username).toBeDefined();
      expect(errors.email).toBeDefined();
      expect(errors.age).toBeDefined();
      expect(errors.password).toBeDefined();
      expect(result.values).toEqual({});
    });

    it('should handle circular dependencies gracefully', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword'],
        confirmPassword: ['password'],
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['password']);
      const context = createMockContext();

      const dataWithMismatchedPasswords = {
        ...validFormData,
        password: 'newpassword123',
        confirmPassword: 'oldpassword123',
      };

      const result = await resolver(
        dataWithMismatchedPasswords,
        context,
        options,
      );
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.confirmPassword).toEqual({
        message: "Passwords don't match",
        type: 'custom',
      });
      expect(result.values).toEqual({});
    });

    it('should handle non-existent fields in dependency map', async () => {
      const dependencyMap: DependencyMap = {
        password: ['confirmPassword', 'nonExistentField'],
      };
      const resolver = selectiveZodResolver(schemaWithRefine, dependencyMap);
      const options = createMockResolverOptions(['password']);
      const context = createMockContext();

      const result = await resolver(validFormData, context, options);

      // Should still work despite non-existent field
      expect(result.errors).toEqual({});
      expect(result.values).toEqual(expect.objectContaining(validFormData));
    });
  });

  describe('Async validation', () => {
    const asyncSchema = z.object({
      username: z
        .string()
        .min(3)
        .refine(
          async (value) => {
            // Simulate async validation (e.g., checking username availability)
            await new Promise((resolve) => setTimeout(resolve, 10));
            return value !== 'taken';
          },
          {
            message: 'Username is already taken',
          },
        ),
      email: z.string().email(),
    });

    it('should handle async validation successfully', async () => {
      const resolver = selectiveZodResolver(asyncSchema);
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const validData = {
        username: 'available',
        email: 'test@example.com',
      };

      const result = await resolver(validData, context, options);

      expect(result.errors).toEqual({});
      expect(result.values).toEqual(expect.objectContaining(validData));
    });

    it('should handle async validation errors', async () => {
      const resolver = selectiveZodResolver(asyncSchema);
      const options = createMockResolverOptions(['username']);
      const context = createMockContext();

      const invalidData = {
        username: 'taken',
        email: 'test@example.com',
      };

      const result = await resolver(invalidData, context, options);
      const errors = getErrors(result.errors);

      expect(result.errors).toBeDefined();
      expect(errors.username).toEqual({
        message: 'Username is already taken',
        type: 'custom',
      });
      expect(result.values).toEqual({});
    });

    it('should handle abort controller for async validation', async () => {
      const resolver = selectiveZodResolver(asyncSchema);
      const options = createMockResolverOptions(['username']);
      const abortController = new AbortController();
      const context = { abort: abortController };

      const validData = {
        username: 'available',
        email: 'test@example.com',
      };

      // Start validation
      const resultPromise = resolver(validData, context, options);

      // Abort after a short delay
      setTimeout(() => abortController.abort(), 5);

      // Should still complete (our mock doesn't actually respect abort signal)
      const result = await resultPromise;
      expect(result.errors).toEqual({});
    });
  });

  describe('TypeScript type safety', () => {
    it('should maintain type safety for schema inference', async () => {
      type ExpectedType = {
        username: string;
        email: string;
        age: number;
        password: string;
        confirmPassword: string;
      };

      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions();
      const context = createMockContext();

      const result = await resolver(validFormData, context, options);

      // Type should be inferred correctly
      const typedResult: {
        values: ExpectedType | {};
        errors: any;
      } = result;

      expect(typedResult).toBeDefined();
    });
  });

  describe('Error handling', () => {
    it('should handle malformed data gracefully', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions();
      const context = createMockContext();

      const malformedData = {
        username: null,
        email: undefined,
        age: 'not-a-number',
        password: 123,
        confirmPassword: {},
      } as any;

      const result = await resolver(malformedData, context, options);

      expect(result.errors).toBeDefined();
      expect(result.values).toEqual({});
    });

    it('should handle empty values object', async () => {
      const resolver = selectiveZodResolver(basicSchema);
      const options = createMockResolverOptions();
      const context = createMockContext();

      const emptyData = {
        username: '',
        email: '',
        age: 0,
        password: '',
        confirmPassword: '',
      };

      const result = await resolver(emptyData, context, options);

      expect(result.errors).toBeDefined();
      expect(result.values).toEqual({});
    });
  });
});
