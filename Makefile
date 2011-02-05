all :
	python setup.py build

install :
	python setup.py install

clean :
	rm -rf build
	rm -f unit-tests/test_*.py.log

distclean : clean
	rm -rf test-env

install-test-env : test-env all
	test-env/bin/python setup.py install

.PHONY: unit-tests

unit-tests : test-env install-test-env
	@for test in unit-tests/*.py; do test-env/bin/python $$test -v; done

.PHONY: load-tests

load-tests : test-env install-test-env
	@echo Usage: test-env/bin/python load-tests/test_load_test_??.py

test-env :
	virtualenv test-env
