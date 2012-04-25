import requests

s = requests.session()
s.verify = True
print s.get('https://kennethreitz.com/')


# print a.history[0].__dict__