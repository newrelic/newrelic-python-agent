#!/bin/sh

# Generate a private key and a self-signed certificate.

CERTS_DIR='/etc/squid3/certs'
CONFIG='/etc/squid3/openssl.cnf'

# Get domain name from config file.
# Domain is used to name self-signed cert file.
DOMAIN=$(grep commonName $CONFIG | cut -d'=' -f 2 | tr -d ' ')

# Generate private key.
openssl genrsa -out $CERTS_DIR/private.pem 1024

# Generate cert signing request.
openssl req -new \
    -key $CERTS_DIR/private.pem \
    -out $CERTS_DIR/proxy.csr \
    -config $CONFIG

# Generate self-signed cert.
openssl x509 -req \
    -days 365 \
    -signkey $CERTS_DIR/private.pem \
    -in $CERTS_DIR/proxy.csr \
    -out $CERTS_DIR/$DOMAIN.crt \
    -extensions v3_req \
    -extfile $CONFIG

# Delete signing request.
rm $CERTS_DIR/proxy.csr
