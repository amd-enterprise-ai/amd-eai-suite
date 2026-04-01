// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const EXTERNAL_SECRETS_API_GROUP = 'external-secrets.io';
export const EXTERNAL_SECRETS_KIND = 'ExternalSecret';
export const KUBERNETES_SECRETS_VERSION = 'v1';
export const KUBERNETES_SECRETS_KIND = 'Secret';

/** Annotation key for submitter (camelCase as returned by API). */
export const SUBMITTER_ANNOTATION_KEY = 'airmSilogenAiSubmitter';

export const nameRegex = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;
