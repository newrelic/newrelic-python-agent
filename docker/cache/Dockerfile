FROM python-base

RUN mkdir /venvs && \
    mkdir /cache && \
    mkdir /downloads && \
    chown -R guest.users /cache && \
    chown -R guest.users /downloads && \
    chown -R guest.users /venvs


COPY build.sh /home/guest

COPY package-lists /home/guest/package-lists/

RUN chown -R guest.users /home/guest && chmod +x /home/guest/build.sh

RUN su guest -c /home/guest/build.sh && chown -R guest.users /cache && chown -R guest.users /venvs
