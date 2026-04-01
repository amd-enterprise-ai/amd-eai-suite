# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class SecretUseCase(StrEnum):
    """Use case classification for secrets."""

    HUGGING_FACE = "HuggingFace"
    IMAGE_PULL_SECRET = "ImagePullSecret"
    S3 = "S3"
    DB = "Database"
    GENERIC = "Generic"

    @classmethod
    # TODO: Remove this once all labels are updated to use the correct prefix (SDA-3014)
    def _missing_(cls, value: object) -> "SecretUseCase | None":
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None
