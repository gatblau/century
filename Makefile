# Makefile for the Century Superforecaster model.
# Runs the simulation and builds the sensitivity charts.
# Override any default on the command line, e.g.  make run N=20000
#                                            or  make graphics ARGS="--only sobol"

PYTHON ?= python3
N      ?= 800000
RUNDIR ?= runs
ARGS   ?=

.DEFAULT_GOAL := help

.PHONY: help run run-paired run-quick graphics graphics-quick sobol check check-full readable calibrate calibrate-levers clean

help:
	@echo "Century Superforecaster - available targets:"
	@echo "  make run             full model run (N=$(N)), JSON saved under $(RUNDIR)/"
	@echo "  make run-paired      make run, plus the containment-holds companion reading"
	@echo "  make run-quick       fast model run (N=20000), printed to the screen"
	@echo "  make graphics        build all three sensitivity charts in notes/ (~3 min)"
	@echo "  make graphics-quick  build the charts fast at low resolution (~30 s)"
	@echo "  make sobol           write the numeric sensitivity table to notes/sobol.md"
	@echo "  make check           quick regression check against the saved results"
	@echo "  make check-full      full regression check (N=800000, slow)"
	@echo "  make readable        check the documents are still readable by a person"
	@echo "  make calibrate       reweight the ensemble against the outside-view anchors"
	@echo "  make calibrate-levers reweight against the lever-feasibility anchors (third view)"
	@echo "  make clean           delete the generated charts and run files"
	@echo ""
	@echo "Defaults: N=$(N), RUNDIR=$(RUNDIR). Pass flags with ARGS, e.g. make graphics ARGS=\"--only pd\""

run:
	@mkdir -p $(RUNDIR)
	$(PYTHON) century_sim.py $(N) > $(RUNDIR)/run-$(N)-seed431.json
	@echo "wrote $(RUNDIR)/run-$(N)-seed431.json"

# The readiness-erosion magnitude (erode_mag) has no published anchor and the outside-view
# anchors do not discriminate between values, while P(good) is close to linear in it. The
# headline is therefore reported as a PAIR rather than a point (plan-28 §5):
#   "containment decays" - erode_mag drawn from U(0, ERODE_MAX), the sampled default
#   "containment holds"  - erode_mag pinned to 0, the assumption the model made silently
#                          before the correction
# Same worlds and the same seed on both sides. The two are not interchangeable and must not
# be averaged, exactly as with the headline and realistic-bet columns.
#
# The decays side is just a plain run, so this target builds on `run` rather than repeating
# it under a second filename. One reading, one file: run-<N>-seed431.json is always the
# sampled default, and the pin gets the suffix because it is the departure from it.
run-paired: run
	CENTURY_OVERRIDES='{"erode_mag":0}' $(PYTHON) century_sim.py $(N) > $(RUNDIR)/run-$(N)-seed431-containment-holds.json
	@echo "wrote the pair under $(RUNDIR)/:"
	@echo "  run-$(N)-seed431.json                     containment decays, erode_mag ~ U(0, ERODE_MAX)"
	@echo "  run-$(N)-seed431-containment-holds.json   containment holds, erode_mag pinned to 0"

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

# The documents are the product. This checks sentence length, whether every technical word
# is explained somewhere in the document that uses it, and whether each one opens in plain
# language. Budgets live in DOC_PROSE_BUDGETS in check_century.py.
readable:
	$(PYTHON) check_century.py --readability

calibrate:
	$(PYTHON) calibrate_century.py

calibrate-levers:
	$(PYTHON) calibrate_century.py --levers

clean:
	rm -f notes/sensitivity_*.png
	rm -rf $(RUNDIR)
	@echo "removed the sensitivity charts and $(RUNDIR)/"
