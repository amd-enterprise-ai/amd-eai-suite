// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Organization } from '@/types/organization';

export const mockOrganization: Organization = {
  id: 'org-1',
  name: 'Test Organization',
  domains: ['example.com'],
  smtpEnabled: true,
  idpLinked: false,
};

export const mockOrganizationAccessDisabled: Organization = {
  id: 'org-2',
  name: 'Test Organization (Access Disabled)',
  domains: ['example.com'],
  smtpEnabled: false,
  idpLinked: false,
};

export const mockOrganizationIdpLinked: Organization = {
  id: 'org-3',
  name: 'Test Organization (IDP Linked)',
  domains: ['example.com'],
  smtpEnabled: true,
  idpLinked: true,
};

export const mockOrganizationIdpLinkedSmtpDisabled: Organization = {
  id: 'org-4',
  name: 'Test Organization (IDP Linked, SMTP Disabled)',
  domains: ['example.com'],
  smtpEnabled: false,
  idpLinked: true,
};
