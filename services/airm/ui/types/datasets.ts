// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum DatasetType {
  Evaluation = 'Evaluation',
  Finetuning = 'Fine-tuning',
}

export interface Dataset {
  id: string;
  name: string;
  path: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  type: string;
  description: string;
}

export type DatasetsResponse = {
  datasets: Dataset[];
};

export interface UploadDatasetFormData {
  name: string;
  description?: string;
  datasetType: string;
  file: File;
}

export interface UploadDatasetParams {
  name: string;
  description: string;
  datasetType: DatasetType;
  file: File;
}
