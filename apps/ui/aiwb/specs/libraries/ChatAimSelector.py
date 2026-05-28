# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

_MULTIMODAL_TAGS = {"vision", "vision-language", "image-to-text", "image-text-to-text", "multimodal"}


class ChatAimSelector:
    """Keyword library for selecting AIM models by capability."""

    @staticmethod
    def find_multimodal_aim(aims_list):
        """Return the first Ready, non-HF-gated multimodal AIM, or None."""
        for aim in aims_list:
            status = aim.get("status", {})
            if status.get("status") != "Ready":
                continue
            model_meta = status.get("imageMetadata", {}).get("model", {})
            if model_meta.get("hfTokenRequired"):
                continue
            tags = set(model_meta.get("tags") or [])
            if tags & _MULTIMODAL_TAGS:
                return aim
        return None
