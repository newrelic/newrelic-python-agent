FROM python-base

RUN pip install devpi eventlet

# Build a virtualenv for each python version

RUN mkdir /venvs
RUN virtualenv /venvs/py26 -p /usr/bin/python2.6
RUN virtualenv /venvs/py27 -p /usr/bin/python2.7
RUN virtualenv /venvs/py33 -p /usr/bin/python3.3
RUN virtualenv /venvs/pypy -p /usr/local/bin/pypy

# Add script to cache source packages

ADD seed_packages.sh /root/seed_packages.sh
RUN chmod 755 /root/seed_packages.sh

# Add lists of packages to cache

ADD package-lists /root/package-lists/

# Run script to cache source packages

RUN devpi-server --start && \
    /root/seed_packages.sh

# Add script to build wheels

ADD build_wheels.sh /root/build_wheels.sh
RUN chmod 755 /root/build_wheels.sh

# RUN script to build wheels

RUN devpi-server --start && \
    /root/build_wheels.sh

EXPOSE 3141
ENTRYPOINT ["devpi-server"]
CMD ["--host", "0.0.0.0"]
