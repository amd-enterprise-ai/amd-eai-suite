# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Robot Framework library for dataset upload operations that require in-memory data generation."""

import io

import requests as req
import urllib3

# Suppress InsecureRequestWarning for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def generate_oversized_jsonl(size_mb: int = 101) -> io.BytesIO:
    """Generate an in-memory JSONL payload exceeding the given size in MB.

    Uses a repeated JSONL line pattern to build a BytesIO object without
    touching disk. Each line is valid JSONL for the Fine-tuning dataset type.
    """
    line = (
        b'{"messages": [{"role": "user", "content": "' + b"x" * 1000 + b'"}, {"role": "assistant", "content": "ok"}]}\n'
    )
    target_bytes = size_mb * 1024 * 1024
    data = io.BytesIO()
    while data.tell() < target_bytes:
        data.write(line)
    data.seek(0)
    return data


def send_oversized_dataset_upload(
    endpoint: str, access_token: str, name: str, size_mb: int = 101, verify: bool = True
) -> req.Response:
    """Upload an oversized dataset using in-memory generated JSONL data.

    Sends a multipart POST request with the generated payload directly,
    bypassing Robot Framework's file-based upload keywords.
    """
    data = generate_oversized_jsonl(size_mb)
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"jsonl": ("data.jsonl", data, "application/octet-stream")}
    form_data = {
        "name": name,
        "description": "Oversized dataset for testing size limit",
        "type": "Fine-tuning",
    }
    response = req.post(endpoint, headers=headers, data=form_data, files=files, verify=verify, timeout=120)
    return response
