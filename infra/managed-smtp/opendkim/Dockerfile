FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates opendkim opendkim-tools \
    && rm -rf /var/lib/apt/lists/*

COPY opendkim.conf /etc/opendkim.conf
COPY entrypoint.sh /usr/local/bin/managed-smtp-opendkim-entrypoint

RUN chmod +x /usr/local/bin/managed-smtp-opendkim-entrypoint \
    && mkdir -p /etc/opendkim/keys /var/run/opendkim \
    && chown -R opendkim:opendkim /var/run/opendkim

EXPOSE 8891

CMD ["managed-smtp-opendkim-entrypoint"]
