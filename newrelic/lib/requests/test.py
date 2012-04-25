from requests import async


rs = []

for i in range(2):
    rs.append(async.get('http://kennethreitz.com'))

for r in async.map(rs):
    print len(r.content)