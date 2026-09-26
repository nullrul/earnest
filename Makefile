SUBPROJECTS := packages/earnest

.PHONY: all build install lint test package deploy clean lint-file

all: install build lint test

# Delegate to all sub-projects
build install lint test:
	@for dir in $(SUBPROJECTS); do \
		echo "=== $$dir: $@ ==="; \
		$(MAKE) -C $$dir $@; \
	done

# Package distributable artifacts
package:
	$(MAKE) -C packages/earnest package

# Deploy infrastructure
deploy:
	@echo 'No deployable sub-projects'

clean:
	@for dir in $(SUBPROJECTS); do \
		$(MAKE) -C $$dir clean 2>/dev/null || true; \
	done

# One-file lint for the PostToolUse hook: dispatch on extension, format/autofix.
# Path comes in via the LINT_FILE env var (never a make var) and is always quoted.
lint-file:
	@case "$$LINT_FILE" in \
		*.py) uv run --project packages/earnest --all-extras ruff format -- "$$LINT_FILE" && uv run --project packages/earnest --all-extras ruff check --fix -- "$$LINT_FILE" ;; \
		*.md) pnpm dlx markdownlint-cli2 --fix -- "$$LINT_FILE" ;; \
		*.yml|*.yaml) yamllint -c .yamllint.yml -- "$$LINT_FILE" ;; \
		*.sh) bash -n -- "$$LINT_FILE" ;; \
		*) ;; \
	esac

# Run a target for a single sub-project: make packages/foo.lint
%.build %.install %.lint %.test %.package %.deploy:
	$(MAKE) -C $(firstword $(subst ., ,$*)) $(lastword $(subst ., ,$*))
