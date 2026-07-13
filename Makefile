# Makefile for the Century Superforecaster model.
# Runs the simulation and builds the sensitivity charts.
# Override any default on the command line, e.g.  make run N=20000
#                                            or  make graphics ARGS="--only sobol"

PYTHON ?= python3
N      ?= 800000
RUNDIR ?= runs
ARGS   ?=

.DEFAULT_GOAL := help

.PHONY: help run run-quick graphics graphics-quick sobol check check-full calibrate calibrate-levers clean

help:
	@echo "Century Superforecaster - available targets:"
	@echo "  make run             full model run (N=$(N)), JSON saved under $(RUNDIR)/"
	@echo "  make run-quick       fast model run (N=20000), printed to the screen"
	@echo "  make graphics        build all three sensitivity charts in notes/ (~3 min)"
	@echo "  make graphics-quick  build the charts fast at low resolution (~30 s)"
	@echo "  make sobol           write the numeric sensitivity table to notes/sobol.md"
	@echo "  make check           quick regression check against the saved results"
	@echo "  make check-full      full regression check (N=800000, slow)"
	@echo "  make calibrate       reweight the ensemble against the outside-view anchors"
	@echo "  make calibrate-levers reweight against the lever-feasibility anchors (third view)"
	@echo "  make clean           delete the generated charts and run files"
	@echo ""
	@echo "Defaults: N=$(N), RUNDIR=$(RUNDIR). Pass flags with ARGS, e.g. make graphics ARGS=\"--only pd\""

run:
	@mkdir -p $(RUNDIR)
	$(PYTHON) century_sim.py $(N) > $(RUNDIR)/run-$(N)-seed431.json
	@echo "wrote $(RUNDIR)/run-$(N)-seed431.json"

run-quick:
	$(PYTHON) century_sim.py 20000

graphics:
	$(PYTHON) plot_sensitivity.py $(ARGS)

graphics-quick:
	$(PYTHON) plot_sensitivity.py --quick $(ARGS)

sobol:
	$(PYTHON) sobol_century.py --notes

check:
	$(PYTHON) check_century.py --quick

check-full:
	$(PYTHON) check_century.py

calibrate:
	$(PYTHON) calibrate_century.py

calibrate-levers:
	$(PYTHON) calibrate_century.py --levers

clean:
	rm -f notes/sensitivity_*.png
	rm -rf $(RUNDIR)
	@echo "removed the sensitivity charts and $(RUNDIR)/"
