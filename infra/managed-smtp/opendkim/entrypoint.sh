#!/bin/sh
set -eu

: "${OPENDKIM_DOMAINS:?OPENDKIM_DOMAINS is required}"
SELECTOR="${OPENDKIM_SELECTOR:-ee1}"
TRUSTED_HOSTS="${OPENDKIM_TRUSTED_HOSTS:-127.0.0.1 localhost managed-smtp-postfix}"

mkdir -p /etc/opendkim /var/run/opendkim

: > /etc/opendkim/KeyTable
: > /etc/opendkim/SigningTable
for domain in $(printf '%s' "$OPENDKIM_DOMAINS" | tr ',' ' '); do
  key_path="/etc/opendkim/keys/${domain}/${SELECTOR}.private"
  if [ ! -f "$key_path" ]; then
    echo "Missing DKIM private key: $key_path" >&2
    exit 2
  fi
  printf '%s._domainkey.%s %s:%s:%s\n' "$SELECTOR" "$domain" "$domain" "$SELECTOR" "$key_path" >> /etc/opendkim/KeyTable
  printf '*@%s %s._domainkey.%s\n' "$domain" "$SELECTOR" "$domain" >> /etc/opendkim/SigningTable
done

: > /etc/opendkim/TrustedHosts
for host in $TRUSTED_HOSTS; do
  printf '%s\n' "$host" >> /etc/opendkim/TrustedHosts
done

chown -R opendkim:opendkim /var/run/opendkim
exec opendkim -f -x /etc/opendkim.conf
