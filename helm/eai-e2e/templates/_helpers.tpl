# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

{{/*
Construct the keycloak public URL.
Use .Values.keycloak.publicUrl if specified, otherwise construct from known values.
*/}}
{{- define "eai-e2e.keycloakPublicUrl" -}}
{{- if .Values.keycloak.publicUrl -}}
{{ .Values.keycloak.publicUrl }}
{{- else -}}
https://{{ .Values.kgateway.keycloak.prefixValue }}.{{ .Values.appDomain }}
{{- end -}}
{{- end -}}
