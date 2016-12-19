FROM python-base

RUN pip install devpi-server==4.2.0 && \
    pip install devpi-client==2.7.0 && \
    # Build a virtualenv for each python version \
    mkdir /venvs && \
    virtualenv /venvs/py26 -p /usr/bin/python2.6 && \
    virtualenv /venvs/py27 -p /usr/bin/python2.7 && \
    virtualenv /venvs/py33 -p /usr/bin/python3.3 && \
    virtualenv /venvs/py34 -p /usr/bin/python3.4 && \
    virtualenv /venvs/py35 -p /usr/bin/python3.5 && \
    virtualenv /venvs/pypy -p /usr/local/bin/pypy

# Add script to cache source packages

ADD seed_packages.sh /root/seed_packages.sh

# Add lists of packages to cache

ADD package-lists /root/package-lists/

# Add script to build wheels

ADD build_wheels.sh /root/build_wheels.sh

RUN chmod 755 /root/seed_packages.sh && \
    devpi-server --init --start && \
    /root/seed_packages.sh --mirror-cache-expiry 4294967295 && \
    chmod 755 /root/build_wheels.sh && \
    # RUN script to build wheels \
    /root/build_wheels.sh

EXPOSE 3141
ENTRYPOINT ["devpi-server"]
CMD ["--host", "0.0.0.0", "--mirror-cache-expiry", "4294967295"]
