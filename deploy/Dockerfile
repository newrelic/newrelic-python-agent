FROM python:3.6

# uid=997(jenkins) gid=994(jenkins) groups=994(jenkins),993(docker)
RUN groupadd -g 994 jenkins && useradd -u 997 -g 994 jenkins

RUN pip install twine awscli
