import urllib, os, sys
url = "https://bitbucket.org/hpk42/tox/raw/default/toxbootstrap.py"
#os.environ['USETOXDEV']="1"  # use tox dev version
d = dict(__file__='toxbootstrap.py')
exec urllib.urlopen(url).read() in d
d['cmdline'](['--recreate'] + sys.argv[1:])
