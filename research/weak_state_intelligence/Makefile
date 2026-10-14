PY = python3 -I
.PHONY: test validate risk-set ucdp link pilot-frame pilot gates all register
# make register ZIP=/path/handoff.zip DIR=/path/extracted   (data stays outside Git)
register:    ; $(PY) src/register_handoff.py $(ZIP) $(DIR)
test:        ; $(PY) -m unittest discover -s tests
validate:    ; $(PY) src/validate_ledgers.py
risk-set:    ; $(PY) src/build_risk_set.py
ucdp:        ; $(PY) src/ucdp_reconcile.py
link:        ; $(PY) src/sdm_ucdp_link.py
pilot-frame: ; $(PY) src/build_pilot_frame.py
pilot:       ; $(PY) src/draw_pilot.py
gates:       ; $(PY) src/gates.py
all: test validate risk-set ucdp link pilot-frame gates
