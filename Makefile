BINDIR = compilers/parts/python-2.6/bin
PYTHON = $(BINDIR)/python
VIRTUALENV = $(BINDIR)/virtualenv

all :
	$(PYTHON) setup.py build

install :
	$(PYTHON) setup.py install

clean :
	rm -rf build
	rm -f unit-tests/test_*.py.log

distclean : clean
	rm -rf test-env

install-testing : test-env all
	test-env/bin/python setup.py install

.PHONY: unit-tests

unit-tests : test-env install-testing
	@for test in unit-tests/*.py; do test-env/bin/python $$test -v; done

.PHONY: load-tests

load-tests : test-env install-testing
	@echo Usage: test-env/bin/python load-tests/test_load_test_??.py

test-env :
	$(VIRTUALENV) test-env
