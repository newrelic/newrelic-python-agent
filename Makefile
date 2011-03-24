BINDIR = python-tools/parts/python-2.6/bin
PYTHON = $(BINDIR)/python
VIRTUALENV = $(BINDIR)/virtualenv

all : php_agent config.h
	$(PYTHON) setup.py build

install :
	$(PYTHON) setup.py install

clean :
	rm -rf build
	rm -f unit-tests/test_*.py.log
	$(RM) config.log config.status
	rm -rf autom4te.cache
	$(RM) config.h

distclean : clean
	rm -rf test-env
	-(cd php_agent && git clean -fdx)

realclean : distclean
	rm -rf php_agent

php_agent :
	git clone repo.newrelic.com:/git/php_agent.git

config.h :
	./configure

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
