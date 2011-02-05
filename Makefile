all :
	python setup.py build

install :
	python setup.py install

clean :
	rm -rf build
	rm -f unit-tests/test_*.py.log

distclean : clean
	rm -rf test-env

.PHONY: unit-tests

unit-tests : test-env
	test-env/bin/python setup.py install
	@for test in unit-tests/*.py; do test-env/bin/python $$test -v; done

.PHONY: load-tests

load-tests : test-env
	test-env/bin/python setup.py install
	@echo Usage: test-env/bin/python load-tests/test_load_test_??.py

test-env :
	virtualenv test-env
