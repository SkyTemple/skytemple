# Makefile for generating files.
# Does NOT install the Python package or dependencies.
# Make sure to install those first and also checkout the submodules.

.PHONY: clean all
.DEFAULT_GOAL: all

rwildcard=$(foreach d,$(wildcard $(1:=/*)),$(call rwildcard,$d,$2) $(filter $(subst *,%,$2),$d))
ALL_BLP=$(call rwildcard,skytemple,*.blp)
ALL_UI=$(ALL_BLP:.blp=.ui)
ALL_PO=$(call rwildcard,skytemple,*.po)
ALL_MO=$(ALL_PO:.po=.mo)

%.ui: %.blp
	./blueprint-compiler/blueprint-compiler.py compile --output "$@" "$<"

%.mo: %.po
	msgfmt -o "$@" "$<"

all: $(ALL_UI) $(ALL_MO)

clean:
	find skytemple -name "*.mo" -type f -delete
	# TODO: To be enabled once done with migration: find skytemple -name "*.ui" -type f -delete
