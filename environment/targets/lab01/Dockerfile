FROM httpd:2.4@sha256:c842ac797bd1fe8b3cd26d002ac9d948aa2814097544600600b35aef42e6785a

ENV DEBIAN_FRONTEND=noninteractive

COPY ./public-html/ /usr/local/apache2/htdocs/
RUN  chown -R www-data:www-data /usr/local/apache2/htdocs/

# Install the Lab 01 services and a process supervisor.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ethtool exim4 iproute2 iputils-ping net-tools netcat-traditional openssh-server python3 supervisor \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home alice && \
    echo 'alice:alice' | chpasswd && \
    printf '\nPasswordAuthentication yes\nPermitRootLogin no\nAllowUsers alice\n' >> /etc/ssh/sshd_config

# Copy Exim4 configuration
COPY conf/update-exim4.conf.conf /etc/exim4/update-exim4.conf.conf
COPY conf/exim4 /etc/default/exim4 
RUN update-exim4.conf

# Copy Python script
COPY scripts/ /usr/local/bin/

# Supervisor config starts and monitors every long-running service.
COPY conf/supervisord.conf /etc/supervisor/supervisord.conf
COPY scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Expose ports
EXPOSE 21 22 25 80 1337 2121

# Start services
CMD ["/usr/local/bin/start.sh"]
