FROM python-base

RUN pip install devpi-server eventlet

EXPOSE 3141
ENTRYPOINT ["devpi-server"]
CMD ["--host", "0.0.0.0"]
