all :
	python setup.py build

install :
	python setup.py install

clean :
	rm -rf build

distclean : clean
	rm -rf tests-virtualenv

test : tests-virtualenv
	tests-virtualenv/bin/python setup.py install

tests-virtualenv :
	virtualenv tests-virtualenv
