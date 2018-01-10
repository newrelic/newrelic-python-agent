FROM python-base

RUN mkdir /venvs && \
    mkdir /cache && \
    virtualenv /venvs/py26 -p /usr/bin/python2.6 && \
    virtualenv /venvs/py27 -p /usr/bin/python2.7 && \
    virtualenv /venvs/py33 -p /usr/bin/python3.3 && \
    virtualenv /venvs/py34 -p /usr/bin/python3.4 && \
    virtualenv /venvs/py35 -p /usr/bin/python3.5 && \
    virtualenv /venvs/py36 -p /usr/bin/python3.6 && \
    virtualenv /venvs/pypy -p /usr/local/bin/pypy && \
    virtualenv /venvs/pypy3 -p /usr/local/bin/pypy3 && \
    mkdir /downloads && \
    chown -R guest.users /cache && \
    chown -R guest.users /downloads && \
    chown -R guest.users /venvs


COPY build.sh /home/guest

COPY package-lists /home/guest/package-lists/

RUN chown -R guest.users /home/guest && chmod +x /home/guest/build.sh

RUN su guest -c /home/guest/build.sh && chown -R guest.users /cache
