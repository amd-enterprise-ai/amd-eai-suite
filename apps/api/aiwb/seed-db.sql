-- Copyright © Advanced Micro Devices, Inc., or its affiliates.
--
-- SPDX-License-Identifier: MIT

-- Insert test dataset for fine-tuning
INSERT INTO datasets (
    id,
    namespace,
    name,
    description,
    path,
    type,
    created_at,
    updated_at,
    created_by,
    updated_by
) VALUES (
    'a1b2c3d4-5678-90ab-cdef-fedcba987654',
    'workbench',
    'Sample Fine-tuning Dataset',
    'A sample JSONL dataset for testing LLM fine-tuning workflows',
    'workbench/datasets/sample-finetuning.jsonl',
    'Fine-tuning',
    TIMESTAMP '2025-12-19 10:00:00+00',
    TIMESTAMP '2025-12-19 10:00:00+00',
    'system',
    'system'
) ON CONFLICT DO NOTHING;

-- Insert test workload for logs and metrics testing
INSERT INTO workloads (
    id,
    name,
    display_name,
    namespace,
    type,
    status,
    chart_id,
    model_id,
    dataset_id,
    user_inputs,
    output,
    manifest,
    created_at,
    updated_at,
    created_by,
    updated_by
)
SELECT
    '550e8400-e29b-41d4-a716-446655440000'::UUID,
    'test-workload-inference',
    'Test Inference Workload',
    'workbench',
    'INFERENCE',
    'running',
    (SELECT id FROM charts WHERE type = 'INFERENCE' LIMIT 1),
    NULL,
    NULL,
    '{}'::jsonb,
    '{}'::jsonb,
    '',
    TIMESTAMP '2025-12-19 10:00:00+00',
    TIMESTAMP '2025-12-19 10:00:00+00',
    'system',
    'system'
WHERE EXISTS (SELECT 1 FROM charts WHERE type = 'INFERENCE')
ON CONFLICT DO NOTHING;

-- Insert second test workload for testing multiple workloads
INSERT INTO workloads (
    id,
    name,
    display_name,
    namespace,
    type,
    status,
    chart_id,
    model_id,
    dataset_id,
    user_inputs,
    output,
    manifest,
    created_at,
    updated_at,
    created_by,
    updated_by
)
SELECT
    '660e8400-e29b-41d4-a716-446655440001'::UUID,
    'test-workload-finetuning',
    'Test Fine-tuning Workload',
    'workbench',
    'FINE_TUNING',
    'running',
    (SELECT id FROM charts WHERE type = 'FINE_TUNING' LIMIT 1),
    NULL,
    NULL,
    '{}'::jsonb,
    '{}'::jsonb,
    '',
    TIMESTAMP '2025-12-19 10:00:00+00',
    TIMESTAMP '2025-12-19 10:00:00+00',
    'system',
    'system'
WHERE EXISTS (SELECT 1 FROM charts WHERE type = 'FINE_TUNING')
ON CONFLICT DO NOTHING;

-- Insert third test workload for testing multiple workloads
INSERT INTO workloads (
    id,
    name,
    display_name,
    namespace,
    type,
    status,
    chart_id,
    model_id,
    dataset_id,
    user_inputs,
    output,
    manifest,
    created_at,
    updated_at,
    created_by,
    updated_by
)
SELECT
    '770e8400-e29b-41d4-a716-446655440002'::UUID,
    'test-workload-workspace',
    'Test Workspace Workload',
    'workbench',
    'WORKSPACE',
    'running',
    (SELECT id FROM charts WHERE type = 'WORKSPACE' LIMIT 1),
    NULL,
    NULL,
    '{}'::jsonb,
    '{}'::jsonb,
    '',
    TIMESTAMP '2025-12-19 10:00:00+00',
    TIMESTAMP '2025-12-19 10:00:00+00',
    'system',
    'system'
WHERE EXISTS (SELECT 1 FROM charts WHERE type = 'WORKSPACE')
ON CONFLICT DO NOTHING;
