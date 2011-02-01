all :
	python setup.py build

install :
	python setup.py install

clean :
	rm -rf build
	rm -f tests/test_*.py.log

distclean : clean
	rm -rf tests-virtualenv

test : tests-virtualenv
	tests-virtualenv/bin/python setup.py install
	@for test in tests/*.py; do tests-virtualenv/bin/python $$test -v; done

tests-virtualenv :
	virtualenv tests-virtualenv
