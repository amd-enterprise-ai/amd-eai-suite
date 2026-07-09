// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import {
  formValuesToProfileOverrides,
  formValuesToProfilePatch,
  imageRefToFamilyTag,
  parseRuntimeYamlMapping,
  profileOverridesToFormValues,
  profileOverridesToOnboardBody,
  RuntimeProfileYamlError,
} from '@/lib/app/runtimeProfileMappers';
import type { AimImageFamily, ClusterAccelerator } from '@/types/cluster';
import { AUTOMATIC_IMAGE_FAMILY_ID } from '@/types/runtime-profile';

const imageFamilies: AimImageFamily[] = [
  {
    familyId: AUTOMATIC_IMAGE_FAMILY_ID,
    displayName: 'Automatic',
    repository: null,
    tags: [],
  },
  {
    familyId: 'aim-base',
    displayName: 'aim-base',
    repository: 'amdenterpriseai/aim-base',
    tags: ['0.11'],
  },
];

const accelerators: ClusterAccelerator[] = [
  { deviceId: '74a1', productName: 'AMD Instinct MI300X', allocatableCount: 8 },
];

const previewFields = {
  repoId: 'org/model',
  revision: 'main',
  sha: 'abc',
  displayName: 'My model',
  tags: [],
};

describe('parseRuntimeYamlMapping', () => {
  it('returns a mapping for valid key/value YAML', () => {
    expect(parseRuntimeYamlMapping('foo: bar', 'engineArgsYaml')).toEqual({
      foo: 'bar',
    });
  });

  it('rejects top-level YAML that parses to a Date (timestamps are not plain maps)', () => {
    expect(() =>
      parseRuntimeYamlMapping(
        '!!timestamp 2001-12-15T02:59:43.1Z',
        'engineArgsYaml',
      ),
    ).toThrow(RuntimeProfileYamlError);
  });

  it('rejects top-level sequences', () => {
    expect(() => parseRuntimeYamlMapping('- a: 1', 'envVarsYaml')).toThrow(
      RuntimeProfileYamlError,
    );
  });
});

describe('runtimeProfileMappers', () => {
  it('builds profile overrides from form values', () => {
    expect(
      formValuesToProfileOverrides(
        {
          containerImage: 'aim-base',
          containerVersion: '0.11',
          acceleratorType: 'gpu',
          accelerator: '74a1',
          acceleratorCount: 2,
          modelPrecision: 'bf16',
          engineArgsYaml: 'foo: bar',
          envVarsYaml: 'VLLM_ROCM_USE_AITER: 1',
        },
        imageFamilies,
      ),
    ).toEqual({
      imageFamilyId: 'aim-base',
      image: 'amdenterpriseai/aim-base:0.11',
      acceleratorType: 'gpu',
      acceleratorModel: '74a1',
      acceleratorCount: 2,
      precision: 'bf16',
      engineArgsYaml: 'foo: bar',
      envVarsYaml: 'VLLM_ROCM_USE_AITER: 1',
    });
  });

  it('always sends precision and the canonical accelerator model on the default path', () => {
    const body = profileOverridesToOnboardBody(
      formValuesToProfileOverrides(
        {
          containerImage: 'aim-base',
          containerVersion: '0.11',
          acceleratorType: 'gpu',
          accelerator: '74a1',
          acceleratorCount: 1,
          modelPrecision: 'bf16',
          engineArgsYaml: '',
          envVarsYaml: '',
        },
        imageFamilies,
      ),
      previewFields,
      imageFamilies,
      accelerators,
    );
    expect(body.image).toBe('amdenterpriseai/aim-base:0.11');
    // bf16 must reach aim-engine (not be stripped), and the device id 74a1 must
    // be translated to the canonical MI300X so the emitted profile is not stuck
    // NotAvailable.
    expect(body.customProfile).toEqual({
      imageFamilyId: 'aim-base',
      acceleratorType: 'gpu',
      acceleratorModel: 'MI300X',
      acceleratorCount: 1,
      precision: 'bf16',
    });
  });

  it('resolves the device id to the canonical accelerator model for non-default precision', () => {
    const body = profileOverridesToOnboardBody(
      formValuesToProfileOverrides(
        {
          containerImage: 'aim-base',
          containerVersion: '0.11',
          acceleratorType: 'gpu',
          accelerator: '74a1',
          acceleratorCount: 1,
          modelPrecision: 'fp16',
          engineArgsYaml: '',
          envVarsYaml: '',
        },
        imageFamilies,
      ),
      previewFields,
      imageFamilies,
      accelerators,
    );
    expect(body.customProfile?.acceleratorModel).toBe('MI300X');
    expect(body.customProfile?.precision).toBe('fp16');
  });

  it('parses engine args and env var YAML into canonical engineArgs/engineEnv', () => {
    const body = profileOverridesToOnboardBody(
      formValuesToProfileOverrides(
        {
          containerImage: 'aim-base',
          containerVersion: '0.11',
          acceleratorType: 'gpu',
          accelerator: '74a1',
          acceleratorCount: 1,
          modelPrecision: 'bf16',
          engineArgsYaml: 'max-model-len: 4096\nattention-backend: TRITON_ATTN',
          envVarsYaml: 'VLLM_ROCM_USE_AITER: 1',
        },
        imageFamilies,
      ),
      previewFields,
      imageFamilies,
      accelerators,
    );
    expect(body.customProfile?.engineArgs).toEqual({
      'max-model-len': 4096,
      'attention-backend': 'TRITON_ATTN',
    });
    expect(body.customProfile?.engineEnv).toEqual([
      { name: 'VLLM_ROCM_USE_AITER', value: '1' },
    ]);
  });

  it('passes an unknown accelerator value through unchanged', () => {
    const body = profileOverridesToOnboardBody(
      formValuesToProfileOverrides(
        {
          containerImage: 'aim-base',
          containerVersion: '0.11',
          acceleratorType: 'gpu',
          accelerator: 'MI325X',
          acceleratorCount: 1,
          modelPrecision: 'bf16',
          engineArgsYaml: '',
          envVarsYaml: '',
        },
        imageFamilies,
      ),
      previewFields,
      imageFamilies,
      accelerators,
    );
    expect(body.customProfile?.acceleratorModel).toBe('MI325X');
  });
});

describe('imageRefToFamilyTag', () => {
  it('maps a repo:tag ref back to its catalog family and tag', () => {
    expect(
      imageRefToFamilyTag('amdenterpriseai/aim-base:0.11', imageFamilies),
    ).toEqual({ familyId: 'aim-base', tag: '0.11' });
  });

  it('returns the tag without a family when no catalog repo matches', () => {
    expect(
      imageRefToFamilyTag('docker.io/other/img:1.2.3', imageFamilies),
    ).toEqual({ familyId: undefined, tag: '1.2.3' });
  });

  it('handles refs that omit a tag', () => {
    expect(
      imageRefToFamilyTag('amdenterpriseai/aim-base', imageFamilies),
    ).toEqual({ familyId: 'aim-base', tag: undefined });
  });

  it('does not treat a registry port as a tag', () => {
    expect(
      imageRefToFamilyTag('registry:5000/team/img', imageFamilies),
    ).toEqual({ familyId: undefined, tag: undefined });
  });

  it('parses digest refs without treating sha256 colon as a tag separator', () => {
    const digest =
      'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
    expect(
      imageRefToFamilyTag(`amdenterpriseai/aim-base@${digest}`, imageFamilies),
    ).toEqual({ familyId: 'aim-base', tag: undefined });
    expect(
      imageRefToFamilyTag(`registry:5000/team/img@${digest}`, imageFamilies),
    ).toEqual({ familyId: undefined, tag: undefined });
  });

  it('parses repo:tag@digest refs using only the name:tag portion', () => {
    const digest =
      'sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
    expect(
      imageRefToFamilyTag(
        `amdenterpriseai/aim-base:0.11@${digest}`,
        imageFamilies,
      ),
    ).toEqual({ familyId: 'aim-base', tag: '0.11' });
  });

  it('returns an empty object for blank input', () => {
    expect(imageRefToFamilyTag(undefined, imageFamilies)).toEqual({});
    expect(imageRefToFamilyTag('', imageFamilies)).toEqual({});
  });
});

describe('profileOverridesToFormValues', () => {
  it('falls back to catalog defaults when overrides omit runtime knobs', () => {
    expect(
      profileOverridesToFormValues(
        { image: 'amdenterpriseai/aim-base:0.11' },
        imageFamilies,
        accelerators,
      ),
    ).toEqual({
      containerImage: 'aim-base',
      containerVersion: '0.11',
      acceleratorType: 'gpu',
      accelerator: '74a1',
      acceleratorCount: 1,
      modelPrecision: 'bf16',
      engineArgsYaml: '',
      envVarsYaml: '',
    });
  });

  it('round-trips persisted runtime overrides, mapping model->device and engineArgs->yaml', () => {
    expect(
      profileOverridesToFormValues(
        {
          image: 'amdenterpriseai/aim-base:0.11',
          imageFamilyId: 'aim-base',
          acceleratorType: 'gpu',
          acceleratorModel: 'MI300X',
          acceleratorCount: 4,
          precision: 'fp8',
          engineArgs: { 'max-model-len': 4096 },
          engineEnv: { VLLM_ROCM_USE_AITER: '1' },
        },
        imageFamilies,
        accelerators,
      ),
    ).toEqual({
      containerImage: 'aim-base',
      containerVersion: '0.11',
      acceleratorType: 'gpu',
      accelerator: '74a1',
      acceleratorCount: 4,
      modelPrecision: 'fp8',
      engineArgsYaml: 'max-model-len: 4096',
      envVarsYaml: 'VLLM_ROCM_USE_AITER: "1"',
    });
  });

  it('falls back to legacy engineArgsYaml/envVarsYaml fields for older imports', () => {
    const values = profileOverridesToFormValues(
      {
        acceleratorModel: '74a1',
        engineArgsYaml: 'foo: bar',
        envVarsYaml: 'BAZ: 1',
      },
      imageFamilies,
      accelerators,
    );
    expect(values.engineArgsYaml).toBe('foo: bar');
    expect(values.envVarsYaml).toBe('BAZ: 1');
    expect(values.accelerator).toBe('74a1');
  });

  it('uses catalog defaults when overrides are null', () => {
    const values = profileOverridesToFormValues(
      null,
      imageFamilies,
      accelerators,
    );
    expect(values.containerImage).toBe('aim-base');
    expect(values.containerVersion).toBe('0.11');
    expect(values.accelerator).toBe('74a1');
  });
});

describe('formValuesToProfilePatch', () => {
  const baseValues = {
    containerImage: 'aim-base',
    containerVersion: '0.11',
    acceleratorType: 'gpu',
    accelerator: '74a1',
    acceleratorCount: 2,
    modelPrecision: 'fp16',
    engineArgsYaml: '',
    envVarsYaml: '',
  };

  it('emits the complete profile, nulling cleared engine args/env fields', () => {
    const { image, customProfile } = formValuesToProfilePatch(
      baseValues,
      imageFamilies,
      accelerators,
    );
    expect(image).toBe('amdenterpriseai/aim-base:0.11');
    expect(customProfile).toEqual({
      imageFamilyId: 'aim-base',
      acceleratorType: 'gpu',
      acceleratorModel: 'MI300X',
      acceleratorCount: 2,
      precision: 'fp16',
      engineArgs: null,
      engineEnv: null,
    });
  });

  it('parses engine args/env YAML into canonical fields when provided', () => {
    const { customProfile } = formValuesToProfilePatch(
      {
        ...baseValues,
        engineArgsYaml: '  max-model-len: 8192  ',
        envVarsYaml: 'VLLM_ROCM_USE_AITER: 1',
      },
      imageFamilies,
      accelerators,
    );
    expect(customProfile.engineArgs).toEqual({ 'max-model-len': 8192 });
    expect(customProfile.engineEnv).toEqual([
      { name: 'VLLM_ROCM_USE_AITER', value: '1' },
    ]);
  });

  it('never carries the image inside customProfile', () => {
    const { customProfile } = formValuesToProfilePatch(
      baseValues,
      imageFamilies,
      accelerators,
    );
    expect(customProfile).not.toHaveProperty('image');
  });

  it('coerces accelerator count from string (form state can be string before zod)', () => {
    const { customProfile } = formValuesToProfilePatch(
      { ...baseValues, acceleratorCount: '4' },
      imageFamilies,
      accelerators,
    );
    expect(customProfile.acceleratorCount).toBe(4);
  });
});
