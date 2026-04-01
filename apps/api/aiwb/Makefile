# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

.PHONY: docker-up
docker-up:
	docker compose up -d
dc-up: docker-up

.PHONY: docker-down
docker-down:
	docker compose down -v
dc-down: docker-down

.PHONY: docker-reset
docker-reset:
	$(MAKE) docker-down
	$(MAKE) docker-up
dc-reset: docker-reset

.PHONY: run
run:
	uv run dev
dev: run

.PHONY: init
init:
	uv sync --group dev
	cd ../api_common && uv sync --group dev
	cd ../workloads_manager && uv sync --group dev && uv run wm init
	$(MAKE) docker-up

.PHONY: reset
reset:
	$(MAKE) docker-down
	$(MAKE) init
	$(MAKE) run

.PHONY: test
test:
	uv run pytest

# Docker image tag
.PHONY: tag
tag:
	@echo $(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short=7 HEAD)

.DEFAULT_GOAL := run
