PY = python3 -I
.PHONY: test validate risk-set ucdp pilot gates all
test:      ; $(PY) -m unittest discover -s tests
validate:  ; $(PY) src/validate_ledgers.py
risk-set:  ; $(PY) src/build_risk_set.py
ucdp:      ; $(PY) src/ucdp_reconcile.py
pilot:     ; $(PY) src/draw_pilot.py
gates:     ; $(PY) src/gates.py
all: test validate risk-set ucdp gates
