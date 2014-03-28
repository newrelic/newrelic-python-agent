FROM ubuntu:precise

MAINTAINER bbytes  "info@beyondbytes.co.in"

# change to test jenkins auto build with amazon SNS
# Make sure that Upstart won't try to start RabbitMQ after apt-get installs it
# https://github.com/dotcloud/docker/issues/446
ADD policy-rc.d /usr/sbin/policy-rc.d
RUN /bin/chmod 755 /usr/sbin/policy-rc.d

# Another way to work around Upstart problems
# https://www.nesono.com/node/368
# RUN dpkg-divert --local --rename --add /sbin/initctl
# RUN ln -s /bin/true /sbin/initctl

# ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y -q install wget

RUN wget http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
RUN apt-key add rabbitmq-signing-key-public.asc

RUN echo "deb http://www.rabbitmq.com/debian/ testing main" > /etc/apt/sources.list.d/rabbitmq.list
RUN apt-get update 
RUN apt-get -y install rabbitmq-server 

# CMD /usr/sbin/rabbitmq-server

ENTRYPOINT ["/usr/sbin/rabbitmq-server"]

USER root

EXPOSE 5672 15672 4369
