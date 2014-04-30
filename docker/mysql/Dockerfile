FROM ubuntu:12.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install -y mysql-server

# Listen on all addresses
RUN printf "[mysqld]\nbind-address = 0.0.0.0" > /etc/mysql/conf.d/packnsend.cnf

# Username, database name, and password are all set to 'python_agent'
RUN mysqld_safe & \
	sleep 5 && \
	mysql -uroot -e "CREATE USER 'python_agent'@'%' IDENTIFIED BY 'python_agent'"  && \
	mysql -uroot -e "GRANT ALL PRIVILEGES ON *.* TO 'python_agent'@'%' WITH GRANT OPTION"  && \
	mysql -uroot -e "CREATE DATABASE python_agent"

EXPOSE 3306
CMD ["mysqld_safe"]
