FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bind9 bind9-utils bind9-dnsutils dnsutils openssl \
    && rm -rf /var/lib/apt/lists/*

COPY named.conf      /etc/bind/named.conf
COPY home.arpa.zone  /config/home.arpa.zone
COPY entrypoint.sh   /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /etc/bind/keys /etc/bind/zones /var/cache/bind \
    && chown -R root:bind /etc/bind /var/cache/bind \
    && chmod -R 775 /etc/bind /var/cache/bind

EXPOSE 53/udp
EXPOSE 53/tcp

CMD ["/entrypoint.sh"]