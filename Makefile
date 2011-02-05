all :
	python setup.py build

install :
	python setup.py install

clean :
	rm -rf build
	rm -f unit-tests/test_*.py.log

distclean : clean
	rm -rf testenv

.PHONY: unit-tests

unit-tests : testenv
	testenv/bin/python setup.py install
	@for test in unit-tests/*.py; do testenv/bin/python $$test -v; done

testenv :
	virtualenv testenv
