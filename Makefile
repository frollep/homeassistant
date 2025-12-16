PYTHON ?= python

.PHONY: probe
probe:
	@echo "Running Tibber probe (requires TIBBER_TOKEN in environment)..."
	$(PYTHON) tools/tibber_probe.py
