FROM python-base

RUN pip install devpi-server eventlet

RUN virtualenv /root/venv/
RUN virtualenv /root/venv-py3 -p /usr/bin/python3.3

ADD seed_packages.sh /root/seed_packages.sh
RUN chmod 755 /root/seed_packages.sh

ADD packages-py2.txt /root/packages-py2.txt
ADD packages-py3.txt /root/packages-py3.txt

RUN devpi-server --start && \
    /root/seed_packages.sh

EXPOSE 3141
ENTRYPOINT ["devpi-server"]
CMD ["--host", "0.0.0.0"]
