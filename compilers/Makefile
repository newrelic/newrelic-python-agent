all : setup bin
	bin/buildout -v -c buildout-`uname -s | tr A-Z a-z`.cfg

setup : tools/bin/buildout

virtualenv :
	git clone https://github.com/pypa/virtualenv.git 

tools : virtualenv
	python virtualenv/virtualenv.py tools

tools/bin/buildout : tools
	tools/bin/easy_install zc.buildout

bin: downloads
	tools/bin/buildout init

downloads :
	mkdir $@

clean :
	$(RM) .installed.cfg
	rm -rf parts

distclean : clean
	rm -rf virtualenv tools
	rm -rf bin develop-eggs eggs
	rm -rf downloads
