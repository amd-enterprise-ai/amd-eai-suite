// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Organization } from '@amdenterpriseai/types';

export const mockOrganization: Organization = {
  smtpEnabled: true,
  idpLinked: false,
};

export const mockOrganizationAccessDisabled: Organization = {
  smtpEnabled: false,
  idpLinked: false,
};

export const mockOrganizationIdpLinked: Organization = {
  smtpEnabled: true,
  idpLinked: true,
};

export const mockOrganizationIdpLinkedSmtpDisabled: Organization = {
  smtpEnabled: false,
  idpLinked: true,
};
