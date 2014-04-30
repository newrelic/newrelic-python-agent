FROM ubuntu:12.04

RUN apt-get update
RUN apt-get install -y postgresql-9.1

# Switch to user postgres, since root can't connect to the DB.
USER postgres

# Start postgresql and create the python_agent user and database.
# Do this in one command, since postgresql will not stay running
# between separate RUN commands.
#
# TODO: Think more about user name and password
#
RUN /etc/init.d/postgresql start && \
	/usr/bin/psql --command "CREATE USER python_agent with SUPERUSER PASSWORD 'python_agent';" && \
	/usr/bin/createdb -O python_agent python_agent

# Adjust PostgreSQL configuration so that remote connections to the
# database are possible.
RUN echo "host all  all    0.0.0.0/0  md5" >> /etc/postgresql/9.1/main/pg_hba.conf
RUN echo "listen_addresses='*'" >> /etc/postgresql/9.1/main/postgresql.conf

EXPOSE 5432
CMD ["/usr/lib/postgresql/9.1/bin/postgres", "-D", "/var/lib/postgresql/9.1/main", "-c", "config_file=/etc/postgresql/9.1/main/postgresql.conf"]
