.PHONY: help spec-audit

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

spec-audit:  ## Flag specs whose deliverables shipped but status didn't
	python plugin/hooks/spec_audit.py
