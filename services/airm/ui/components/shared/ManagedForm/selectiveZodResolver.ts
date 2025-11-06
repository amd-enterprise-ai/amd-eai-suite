// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  FieldErrors,
  FieldValues,
  Resolver,
  ResolverOptions,
} from 'react-hook-form';

import { toNestErrors } from '@hookform/resolvers';
import { ZodEffects, ZodError, ZodObject, ZodRawShape, z } from 'zod';

/** Optional map of extra fields that must be re‑checked when a key changes. */
export type DependencyMap = Record<string, string[]>;

/** Result type for schema validation */
interface ValidationResult<TData = any> {
  success: boolean;
  data?: TData;
  error?: ZodError;
}

/**
 * Type guard to check if a schema is a ZodEffects
 * @param schema The schema to check
 * @returns True if the schema is a ZodEffects instance
 */
const isZodEffects = (
  schema: ZodObject<ZodRawShape> | ZodEffects<ZodObject<ZodRawShape>>,
): schema is ZodEffects<ZodObject<ZodRawShape>> => {
  return schema instanceof ZodEffects;
};

/**
 * Creates a partial schema containing only the specified fields
 * @param schema The full Zod schema
 * @param fieldNames Array of field names to include
 * @returns Partial schema with only the specified fields
 */
const createPartialSchema = (
  schema: ZodObject<ZodRawShape> | ZodEffects<ZodObject<ZodRawShape>>,
  fieldNames: string[],
): ZodObject<ZodRawShape> => {
  const pickObject = createPickObject(fieldNames);

  return isZodEffects(schema)
    ? (() => {
        const underlying = schema._def.schema;
        if (!(underlying instanceof ZodObject)) {
          throw new Error(
            `Expected underlying schema to be a ZodObject, got ${typeof underlying}. ZodEffects must wrap a ZodObject schema.`,
          );
        }
        return underlying.pick(pickObject);
      })()
    : schema.pick(pickObject);
};

/**
 * Validates values against a partial schema
 * @param schema The schema to validate against
 * @param values The values to validate
 * @param fieldNames The field names to filter errors for (only used for ZodEffects)
 * @returns Promise resolving to validation result
 */
const validatePartialSchema = async <TValues extends FieldValues>(
  schema: ZodObject<ZodRawShape> | ZodEffects<ZodObject<ZodRawShape>>,
  values: TValues,
  fieldNames: string[],
): Promise<ValidationResult<TValues>> => {
  if (fieldNames.length === 0) return { success: true, data: values };

  const result = await schema.safeParseAsync(values);

  if (result.success)
    return { success: true, data: (result.data ?? values) as TValues };

  // For ZodEffects, filter errors to relevant fields only
  if (isZodEffects(schema)) {
    const filteredIssues = result.error.issues.filter((issue) => {
      const fieldPath = issue.path.join('.');
      return (
        fieldNames.includes(fieldPath) ||
        fieldNames.some((field: string) => fieldPath.startsWith(`${field}.`))
      );
    });

    return filteredIssues.length > 0
      ? { success: false, error: new ZodError(filteredIssues) }
      : { success: true, data: values };
  }

  // For ZodObject, return all errors
  return { success: false, error: result.error };
};

/**
 * Creates a pick object for Zod schema selection
 * @param fieldNames Array of field names to include in the pick object
 * @returns Object with field names as keys and true as values
 */
const createPickObject = (fieldNames: string[]): Record<string, true> =>
  !fieldNames.length
    ? {}
    : Object.fromEntries(fieldNames.map((fieldName) => [fieldName, true]));

/**
 * Expands field names with their dependencies
 * @param baseFieldNames The initial field names
 * @param dependencyMap Map of field dependencies
 * @returns Expanded array of field names including dependencies
 */
const expandFieldsWithDependencies = (
  baseFieldNames: string[],
  dependencyMap: DependencyMap,
): string[] =>
  !baseFieldNames.length
    ? []
    : Array.from(
        new Set(
          baseFieldNames.flatMap((fieldName: string) => [
            fieldName,
            ...(dependencyMap[fieldName] ?? []),
          ]),
        ),
      );

/**
 * Transforms Zod validation errors into React Hook Form format
 * @param zodError The Zod error to transform
 * @param options The resolver options
 * @returns Transformed errors in React Hook Form format
 */
const transformZodErrors = <TValues extends FieldValues>(
  zodError: ZodError,
  options: ResolverOptions<TValues>,
): FieldErrors<TValues> => {
  const errorObject = zodError.issues.reduce<
    Record<string, { message: string; type: string }>
  >((acc, issue) => {
    const fieldPath = issue.path.join('.');
    if (fieldPath && !acc[fieldPath]) {
      acc[fieldPath] = {
        message: issue.message,
        type: issue.code,
      };
    }
    return acc;
  }, {});

  return toNestErrors(errorObject, options) as FieldErrors<TValues>;
};

/**
 * Creates a selective resolver bound to a concrete Zod schema.
 * This resolver only validates the field(s) that triggered the validation cycle
 * and their declared dependents, instead of running the entire schema on every change.
 *
 * @param schema The full, authoritative Zod schema for the form
 * @param dependencyMap Cross‑field dependency map (optional)
 * @returns A resolver function for React Hook Form
 *
 * @example
 * ```typescript
 * import { useForm } from 'react-hook-form';
 * import { z } from 'zod';
 *
 * const FormSchema = z.object({
 *   username: z
 *     .string()
 *     .min(3)
 *     .refine(async v => isUsernameFree(v), { message: 'Taken' }),
 *   email: z.string().email()
 * });
 *
 * const resolver = selectiveZodResolver(FormSchema);
 * const { register, handleSubmit } = useForm({ resolver });
 * ```
 *
 * @example With dependency map
 * ```typescript
 * const FormSchema = z.object({
 *   password: z.string().min(8),
 *   confirmPassword: z.string()
 * }).refine(data => data.password === data.confirmPassword, {
 *   message: "Passwords don't match",
 *   path: ['confirmPassword']
 * });
 *
 * // When password changes, also validate confirmPassword
 * const dependencyMap = {
 *   password: ['confirmPassword']
 * };
 *
 * const resolver = selectiveZodResolver(FormSchema, dependencyMap);
 * const { register, handleSubmit } = useForm({ resolver });
 * ```
 */
export function selectiveZodResolver<
  TSchema extends ZodObject<ZodRawShape> | ZodEffects<ZodObject<ZodRawShape>>,
>(
  schema: TSchema,
  dependencyMap: DependencyMap = {},
): Resolver<z.infer<TSchema>> {
  return async (values, context, options) => {
    const baseFieldNames = options.names ?? Object.keys(values as object);

    const expandedFieldNames = expandFieldsWithDependencies(
      baseFieldNames,
      dependencyMap,
    );

    const validationResult = await validatePartialSchema(
      isZodEffects(schema)
        ? schema
        : createPartialSchema(schema, expandedFieldNames),
      values,
      expandedFieldNames,
    );

    return {
      values: validationResult.success
        ? { ...values, ...validationResult.data }
        : {},
      errors: validationResult.error
        ? transformZodErrors(validationResult.error, options)
        : {},
    };
  };
}
