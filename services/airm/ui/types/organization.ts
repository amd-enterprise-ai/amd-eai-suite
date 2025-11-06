// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface Organization {
  id: string;
  name: string;
  domains: string[];
  idpLinked: boolean;
  smtpEnabled: boolean;
}
