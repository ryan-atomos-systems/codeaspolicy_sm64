PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/src:$(PYTHONPATH)

.PHONY: build test lint doctor benchmark dashboard demo first-star first-bowser
build:
	$(PYTHON) scripts/build_native.py --jobs 4
test:
	$(PYTHON) -m unittest discover -s tests -v
lint:
	$(PYTHON) -m ruff check src tests scripts examples
	$(PYTHON) -m ruff format --check src tests scripts examples
doctor:
	$(PYTHON) -m sm64_policy doctor
benchmark:
	$(PYTHON) -m sm64_policy benchmark --output artifacts/run-$$(date +%Y%m%d-%H%M%S)
dashboard:
	$(PYTHON) -m sm64_policy dashboard
demo:
	$(PYTHON) -m sm64_policy benchmark --policies random explore --seeds 0 1 --workers 4 --steps 600 --record-every 1 --width 320 --height 180 --output artifacts/playback-$$(date +%Y%m%d-%H%M%S)
first-star:
	$(PYTHON) -m sm64_policy benchmark --policies first-star --seeds 0 --workers 1 --steps 2400 --frame-skip 1 --record-every 1 --width 640 --height 360 --output artifacts/first-star-$$(date +%Y%m%d-%H%M%S)
first-bowser:
	$(PYTHON) -m sm64_policy benchmark --policies first-bowser --gameplay-mode progression --level 16 --seeds 0 --workers 1 --steps 36000 --frame-skip 1 --timeout 1800 --record-every 3 --width 480 --height 270 --output artifacts/first-bowser-$$(date +%Y%m%d-%H%M%S)
