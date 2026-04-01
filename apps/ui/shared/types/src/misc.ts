// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface SortedBy {
  id: string;
  desc: boolean;
}

export type ToSnakeCase<T extends string> = T extends `${infer A}${infer B}`
  ? `${A extends Capitalize<A> ? '_' : ''}${Lowercase<A>}${ToSnakeCase<B>}`
  : T;

export type SnakeCaseKeys<T> = {
  [K in keyof T as ToSnakeCase<string & K>]: T[K];
};
