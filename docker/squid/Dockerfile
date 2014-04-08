# Dockerfile for Squid3, w/SSL

# Compiling from source by using the Ubuntu source package for Squid
# in the hope that it will be simpler than the standard "./configure; make;
# make install."

# Using Ubuntu 13.10 ("Saucy") as the base image, because libecap2 isn't
# available for Ubuntu 12.04.

FROM stackbrew/ubuntu:saucy

# Add repos for debian source packages

RUN echo "deb-src http://archive.ubuntu.com/ubuntu saucy main" >> /etc/apt/sources.list
RUN echo "deb-src http://archive.ubuntu.com/ubuntu/ saucy-updates main" >> /etc/apt/sources.list
RUN echo "deb-src http://security.ubuntu.com/ubuntu saucy-security main" >> /etc/apt/sources.list
RUN apt-get update

# Install build dependencies

RUN apt-get -y build-dep squid3
RUN apt-get -y install libssl-dev

# Install run dependencies

RUN apt-get -y install apache2 logrotate squid-langpack ca-certificates
RUN apt-get -y install libgssapi-krb5-2 libltdl7 libecap2 libnetfilter-conntrack3

# Download source

RUN mkdir /src
RUN cd /src && apt-get source squid3

# Edit debian/rules to build with SSL

RUN sed -i 's/--enable-ecap/--enable-ecap --enable-ssl --enable-ssl-crtd/' \
    /src/squid3-3.3.8/debian/rules

# Build debs

RUN apt-get -y install devscripts
RUN cd /src/squid3-3.3.8 && debuild -us -uc -b

# Install debs

RUN dpkg -i /src/*.deb

# Install configuration files

ADD squid.conf /etc/squid3/squid.conf
ADD openssl.cnf /etc/squid3/openssl.cnf

# Generate certs

ADD make-certs.sh /usr/local/bin/make-certs.sh
RUN chmod 755 /usr/local/bin/make-certs.sh
RUN mkdir -p /etc/squid3/certs
RUN /usr/local/bin/make-certs.sh


EXPOSE 3128 3129
CMD ["/usr/sbin/squid3", "-N", "-f", "/etc/squid3/squid.conf"]
