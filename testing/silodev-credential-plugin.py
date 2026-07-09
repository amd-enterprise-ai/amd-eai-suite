#!/usr/bin/env python3

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
"""kubectl exec credential plugin for silodev passthrough mode.

Reads an offline OIDC refresh_token from a file (mounted from a per-job
Secret) and exchanges it for a fresh id_token via Keycloak's refresh-token
grant. Returns the result in the ExecCredential format kubectl expects.

This replaces kubectl-oidc_login for the silodev passthrough case. kubelogin's
token-cache filename is a hash that includes --password, which would force
the password into the pod just so the pod's kubelogin computes the same hash
as silodev's local invocation. By using a plain refresh-token grant via this
plugin we keep the password on the laptop and ship only the offline
refresh_token (which has no SSO-session-max ceiling and a 30-day idle TTL).

stdlib-only — no need to install requests/httpx into the image.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
from datetime import datetime, timedelta, timezone
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _die(msg: str) -> NoReturn:
    sys.stderr.write(f"silodev-credential-plugin: {msg}\n")
    sys.exit(1)


def main() -> None:
    refresh_token_file = os.environ.get("SILODEV_OIDC_REFRESH_TOKEN_FILE", "")
    issuer = os.environ.get("SILODEV_OIDC_ISSUER_URL", "")
    client_id = os.environ.get("SILODEV_OIDC_CLIENT_ID", "")
    client_secret = os.environ.get("SILODEV_OIDC_CLIENT_SECRET", "")
    skip_tls = os.environ.get("SILODEV_OIDC_SKIP_TLS_VERIFY", "false").lower() == "true"

    if not refresh_token_file or not issuer or not client_id:
        _die(
            "missing required env vars "
            "(SILODEV_OIDC_REFRESH_TOKEN_FILE, SILODEV_OIDC_ISSUER_URL, SILODEV_OIDC_CLIENT_ID)"
        )

    try:
        with open(refresh_token_file) as f:
            refresh_token = f.read().strip()
    except OSError as e:
        _die(f"failed to read refresh_token file {refresh_token_file}: {e}")

    if not refresh_token:
        _die(f"refresh_token file is empty: {refresh_token_file}")

    form = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        # Request the OpenID scope so Keycloak includes an id_token in the refresh
        # response — kubectl's OIDC auth needs the id_token, and a bare refresh
        # grant can otherwise return only an access_token.
        "scope": "openid",
    }
    # Public OIDC clients reject an empty client_secret with invalid_client; only
    # send it when one is configured.
    if client_secret:
        form["client_secret"] = client_secret
    body = urlencode(form).encode()

    # NB: this runs as a kubectl exec credential plugin, invoked on every kubectl
    # call. Keep stderr clean — anything emitted here pollutes the stderr that
    # callers (and tests) capture from kubectl, so we do not warn on skip_tls.
    if skip_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = None
    req = Request(
        f"{issuer.rstrip('/')}/protocol/openid-connect/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, context=ctx, timeout=30) as resp:
            tokens = json.load(resp)
    except HTTPError as e:
        _die(f"token refresh failed: HTTP {e.code} {e.reason} — {e.read().decode(errors='replace')[:300]}")
    except URLError as e:
        _die(f"token refresh network error: {e.reason}")
    except Exception as e:  # noqa: BLE001
        _die(f"token refresh failed: {e}")

    id_token = tokens.get("id_token")
    expires_in = int(tokens.get("expires_in") or 300)
    if not id_token:
        _die(f"no id_token in response: {json.dumps(tokens)[:300]}")

    # Subtract a small slack so kubectl refreshes before the API server starts
    # rejecting borderline-expired tokens.
    exp = datetime.now(timezone.utc) + timedelta(seconds=max(30, expires_in - 30))
    json.dump(
        {
            "kind": "ExecCredential",
            "apiVersion": "client.authentication.k8s.io/v1",
            "status": {
                "expirationTimestamp": exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "token": id_token,
            },
        },
        sys.stdout,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
