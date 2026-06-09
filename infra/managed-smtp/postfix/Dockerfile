FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates postfix rsyslog \
    && rm -rf /var/lib/apt/lists/*

COPY main.cf /etc/postfix/main.cf
COPY master.cf /etc/postfix/master.cf
COPY entrypoint.sh /usr/local/bin/managed-smtp-entrypoint

RUN chmod +x /usr/local/bin/managed-smtp-entrypoint

EXPOSE 25 587

CMD ["managed-smtp-entrypoint"]
