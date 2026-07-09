# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for the custom models module."""

import os
import re

import httpx

from ..config import AIWB_METADATA_PREFIX, EAI_APPS_METADATA_PREFIX

# HuggingFace lives on a single host; the API base and the set of accepted
# source hostnames both derive from it, so the host string is defined in
# exactly one place. (Weight blobs are fetched via huggingface_hub, which
# resolves its own URLs, so no resolve-base constant is needed.)
HF_HOST = "huggingface.co"
HF_API_BASE = f"https://{HF_HOST}/api/models"

COMPONENT_ID_ANNOTATION = f"{EAI_APPS_METADATA_PREFIX}/component-id"
SOURCE_URI_ANNOTATION = f"{EAI_APPS_METADATA_PREFIX}/source-uri"
REVISION_ANNOTATION = f"{EAI_APPS_METADATA_PREFIX}/revision"

MODEL_DISPLAY_NAME_ANNOTATION = f"{AIWB_METADATA_PREFIX}/model-display-name"
CANONICAL_REPO_ID_ANNOTATION = f"{AIWB_METADATA_PREFIX}/canonical-repo-id"
SOURCE_SHA_ANNOTATION = f"{AIWB_METADATA_PREFIX}/source-sha"
SOURCE_DESCRIPTION_ANNOTATION = f"{AIWB_METADATA_PREFIX}/source-description"
SOURCE_TAGS_ANNOTATION = f"{AIWB_METADATA_PREFIX}/source-tags"

# Workbench-owned annotations tracking the HuggingFace-to-S3 weight import. The
# AIMModel status subresource is owned by aim-engine, so the import pipeline
# records its state in annotations AIWB controls. import-state holds an
# OnboardPhase value (Importing/Ready/Failed); import-error the last failure
# message.
IMPORT_STATE_ANNOTATION = f"{AIWB_METADATA_PREFIX}/import-state"
IMPORT_ERROR_ANNOTATION = f"{AIWB_METADATA_PREFIX}/import-error"

HF_REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=25.0, write=10.0, pool=5.0)

HF_MAX_RESPONSE_BYTES = 1 * 1024 * 1024

# Non-runtime repo files excluded from the HF-to-S3 import (fnmatch globs, matched
# against the full repo path). Deliberately conservative: it drops only documentation,
# licensing, VCS, CI, and media files that inference never loads. It does NOT exclude
# by weight format or extension, so runtime-critical assets a curated allow-list would
# miss — sharded ``*.safetensors.index.json``, ``.bin``/``.pth`` weights, custom
# ``modeling_*.py`` for trust_remote_code models, unusually named tokenizer files —
# are still imported.
WEIGHT_IMPORT_IGNORE_PATTERNS = (
    "*.gitattributes",
    "*.gitignore",
    "*README*.md",
    "*LICENSE*",
    "*LICENCE*",
    ".github/*",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.webp",
    "*.bmp",
    "*.ico",
    "*.mp4",
    "*.mov",
    "*.avi",
    "*.pdf",
)

_HF_HOSTS = frozenset({HF_HOST, f"www.{HF_HOST}"})

_REVISION_MARKERS = frozenset({"tree", "blob", "resolve"})

_REPO_PART_PATTERN = re.compile(r"^(?!\.+$)[A-Za-z0-9._-]+$")

_WEIGHT_EXTENSIONS = frozenset({".safetensors", ".gguf"})
_CONFIG_EXTENSIONS = frozenset({".json", ".txt", ".md", ".model", ".tiktoken", ".py", ".yaml", ".yml"})
_CONFIG_FILENAMES = frozenset({"merges.txt", "vocab.txt", "special_tokens_map.json"})

_INDEX_PATTERN = re.compile(r"\.safetensors\.index\.json$")

# Name of the platform-provisioned Kubernetes Secret that holds MinIO credentials,
# and the key names within it. These are fixed by the Helm chart and must match
# helm/aiwb/values.yaml (minio.credentialsSecretName / accessKeyKey / secretKeyKey).
MINIO_CREDENTIALS_SECRET_NAME = "minio-credentials"
MINIO_CREDENTIALS_ACCESS_KEY_KEY = "minio-access-key"
MINIO_CREDENTIALS_SECRET_KEY_KEY = "minio-secret-key"

# BYOM image override; aim-engine prefers this over ``spec.image`` on AIMProfile.
AIM_DEPLOYMENT_IMAGE_REF_ANNOTATION = "aim.eai.amd.com/deployment-image-ref"

DEFAULT_AIM_DEPLOYMENT_IMAGE_REF = os.getenv("AIM_DEFAULT_DEPLOYMENT_IMAGE_REF", "amdenterpriseai/aim-base:0.11")

# Base-image AIMModel that custom-model onboards derive their profiles from.
# In v1alpha2 a BYOM AIMModel does not carry its own runtime profiles; it
# selects the base profiles emitted by a base-image AIMModel (spec.image points
# at an AIM base image) and overlays identity + weights via spec.profiles.
# That base-image AIMModel is provisioned once by the platform and reused, so
# its name/scope are configuration here, not part of the onboard request.
AIM_BASE_MODEL_NAME = os.getenv("AIM_BASE_MODEL_NAME", "aim-base")
AIM_BASE_MODEL_SCOPE = os.getenv("AIM_BASE_MODEL_SCOPE", "Namespace")

# Poll bounds for waiting on aim-engine to emit the AIMProfile after AIMModel apply.
AIM_PROFILE_WAIT_TIMEOUT_SECONDS = float(os.getenv("AIM_PROFILE_WAIT_TIMEOUT_SECONDS", "60"))
AIM_PROFILE_POLL_INTERVAL_SECONDS = float(os.getenv("AIM_PROFILE_POLL_INTERVAL_SECONDS", "2"))
