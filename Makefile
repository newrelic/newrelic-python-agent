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

test-env :
	virtualenv test-env
