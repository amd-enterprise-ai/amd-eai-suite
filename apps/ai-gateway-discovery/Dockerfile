# syntax=docker/dockerfile:1
# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . ./
RUN CGO_ENABLED=0 GOOS=linux go build -o controller ./cmd/controller

FROM alpine:3.23

RUN addgroup -S -g 65532 controller && adduser -S -u 65532 -G controller controller

COPY --from=builder /app/controller /controller

USER 65532

ENTRYPOINT ["/controller"]
