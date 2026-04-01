# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from loguru import logger


def parse_cpu_value(cpu_str: str) -> int:
    if cpu_str.endswith("m"):
        if len(cpu_str) == 1:
            logger.warning("Invalid CPU value: 'm' with no number")
            return 0
        return int(cpu_str[:-1])
    else:
        try:
            return int(float(cpu_str) * 1000)
        except ValueError:
            logger.warning(f"Could not parse CPU value: {cpu_str}")
            return 0


def __parse_memory(value_str: str, units: dict[str, int]) -> int:
    """Generic parser for memory strings with unit suffixes."""
    if value_str.isdigit():
        return int(value_str)

    for suffix, multiplier in units.items():
        if value_str.endswith(suffix):
            try:
                value = float(value_str[: -len(suffix)])
                return int(value * multiplier)
            except ValueError:
                break  # fall through to warning

    try:
        return int(float(value_str))
    except ValueError:
        logger.warning(f"Could not parse memory value: {value_str!r}")
        return 0


def parse_k8s_memory(memory_str: str) -> int:
    if memory_str.isdigit():
        return int(memory_str)

    units = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "Pi": 1024**5,
        "K": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
        "P": 1000**5,
    }

    return __parse_memory(memory_str, units)


# Specialized parser for AMD GPU VRAM labels.
# Unlike standard Kubernetes memory units (Gi, Mi, etc.),
# AMD reports GPU VRAM using G, M, etc. (decimal-style suffixes).
def parse_gpu_vram_memory(vram_str: str) -> int:
    if vram_str.isdigit():
        return int(vram_str)

    units: dict[str, int] = {
        # Binary units (IEC)
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "Pi": 1024**5,
        # AMD VRAM units
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "P": 1024**5,
    }

    return __parse_memory(vram_str, units)
