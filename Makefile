# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# AI Rules Infrastructure
#
# AGENTS.md is the source of truth for AI coding rules in each directory.
# - Cursor reads AGENTS.md natively (nested directory discovery)
# - Claude Code reads CLAUDE.md (symlinks to AGENTS.md)
# - GitHub Copilot reads .github/copilot-instructions.md (concatenated)
#
# Usage: make ai-rules (auto-runs via pre-commit hook)

.PHONY: ai-rules docs-api help

# Regenerate the published API reference pages from the FastAPI services.
# Exports each spec, filters it to the public allowlist (tools/openapi-docs/
# public-api.yaml), and renders Markdown. Requires `uv`; commit the results.
docs-api:
	@uv run --no-project --with openapi-markdown --with pyyaml python tools/openapi-docs/build.py

ai-rules:
	@echo "Ensuring CLAUDE.md symlinks exist..."
	@for rules_file in $$(find . -name "AGENTS.md" -not -path "*/.*" -not -path "*/node_modules/*"); do \
		dir=$$(dirname "$$rules_file"); \
		if [ -f "$$dir/CLAUDE.md" ] && [ ! -L "$$dir/CLAUDE.md" ]; then \
			echo "  ERROR: $$dir/CLAUDE.md exists as regular file. Remove it manually before creating symlink."; \
			exit 1; \
		elif [ ! -e "$$dir/CLAUDE.md" ] || [ -L "$$dir/CLAUDE.md" ]; then \
			ln -sf AGENTS.md "$$dir/CLAUDE.md"; \
		fi; \
	done
	@echo "  Symlinks up to date."
	@echo "Generating .github/copilot-instructions.md..."
	@mkdir -p .github
	@cat AGENTS.md > .github/copilot-instructions.md
	@echo "" >> .github/copilot-instructions.md
	@echo "---" >> .github/copilot-instructions.md
	@echo "" >> .github/copilot-instructions.md
	@cat apps/api/AGENTS.md >> .github/copilot-instructions.md
	@echo "" >> .github/copilot-instructions.md
	@echo "---" >> .github/copilot-instructions.md
	@echo "" >> .github/copilot-instructions.md
	@cat apps/api/aiwb/AGENTS.md >> .github/copilot-instructions.md
	@echo "  .github/copilot-instructions.md"
	@echo "Generating .github/instructions/e2e.instructions.md..."
	@mkdir -p .github/instructions
	@printf -- '---\napplyTo: "**/specs/**"\n---\n\n' > .github/instructions/e2e.instructions.md
	@cat apps/AGENTS.md >> .github/instructions/e2e.instructions.md
	@echo "  .github/instructions/e2e.instructions.md"
	@echo "Done."

help:
	@echo "Usage:"
	@echo "  make ai-rules   Sync AGENTS.md-derived AI rules files"
	@echo "  make docs-api   Regenerate published API reference from FastAPI specs"

.DEFAULT_GOAL := help
