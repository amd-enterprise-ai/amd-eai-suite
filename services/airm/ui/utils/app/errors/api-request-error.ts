// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export class APIRequestError extends Error {
  statusCode: number;
  constructor(message: string | undefined, statusCode: number) {
    super(message);
    this.name = 'APIRequestError';
    this.statusCode = statusCode;
  }
}

export default APIRequestError;
