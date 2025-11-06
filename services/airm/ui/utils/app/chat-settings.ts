// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DEFAULT_SETTINGS, InferenceSettings } from '@/types/models';

const STORAGE_KEY = 'chatSettings';

export const getChatSettings = (): InferenceSettings => {
  let settings: InferenceSettings = { ...DEFAULT_SETTINGS };

  if (typeof localStorage !== 'undefined') {
    const settingsJson = localStorage.getItem(STORAGE_KEY);
    if (settingsJson) {
      try {
        let savedSettings = JSON.parse(settingsJson) as InferenceSettings;
        settings = Object.assign(settings, savedSettings);
      } catch (e) {
        console.error(e);
      }
    }
  }

  settings.ragEnabled = false;
  settings.collectionId = undefined;
  return settings;
};

export const saveChatSettings = (settings: InferenceSettings) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
};
