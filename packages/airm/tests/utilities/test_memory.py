# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.utilities.memory import parse_cpu_value, parse_gpu_vram_memory, parse_k8s_memory


def test_parse_cpu_value_millicores():
    assert parse_cpu_value("100m") == 100
    assert parse_cpu_value("500m") == 500
    assert parse_cpu_value("1000m") == 1000


def test_parse_cpu_value_whole_cores():
    assert parse_cpu_value("1") == 1000
    assert parse_cpu_value("2") == 2000
    assert parse_cpu_value("10") == 10000


def test_parse_cpu_value_decimal_cores():
    assert parse_cpu_value("1.5") == 1500
    assert parse_cpu_value("2.75") == 2750


def test_parse_cpu_value_invalid():
    assert parse_cpu_value("invalid") == 0.0
    assert parse_cpu_value("m") == 0.0


def test_parse_k8s_memory_bytes():
    assert parse_k8s_memory("1024") == 1024


def test_parse_k8s_memory_ki_mi_gi():
    assert parse_k8s_memory("1Ki") == 1024
    assert parse_k8s_memory("1Mi") == 1048576  # 1024^2
    assert parse_k8s_memory("1Gi") == 1073741824  # 1024^3


def test_parse_k8s_memory_k_m_g():
    assert parse_k8s_memory("1K") == 1000
    assert parse_k8s_memory("1M") == 1000000  # 1000^2
    assert parse_k8s_memory("1G") == 1000000000  # 1000^3


def test_parse_k8s_memory_decimal():
    assert parse_k8s_memory("1.5Gi") == 1610612736  # 1.5 * 1024^3
    assert parse_k8s_memory("2.5Mi") == 2621440  # 2.5 * 1024^2


def test_parse_k8s_memory_invalid():
    assert parse_k8s_memory("invalid") == 0


def test_parse_gpu_vram_memory():
    assert parse_gpu_vram_memory("1024") == 1024
    assert parse_gpu_vram_memory("1Ki") == 1024
    assert parse_gpu_vram_memory("1Mi") == 1048576  # 1024^2
    assert parse_gpu_vram_memory("1Gi") == 1073741824  # 1024^3
    assert parse_gpu_vram_memory("1K") == 1024
    assert parse_gpu_vram_memory("1M") == 1048576  # 1024^2
    assert parse_gpu_vram_memory("1G") == 1073741824  # 1024^3
