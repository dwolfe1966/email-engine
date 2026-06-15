#!/bin/sh
set -eu

postconf -e "myhostname = ${POSTFIX_MYHOSTNAME:-smtp-staging.email-engine.local}"
postconf -e "mydomain = ${POSTFIX_MYDOMAIN:-email-engine.local}"
postconf -e "myorigin = \$mydomain"
postconf -e "mydestination ="
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ipv4"
postconf -e "mynetworks = ${POSTFIX_MYNETWORKS:-127.0.0.0/8 172.16.0.0/12}"
postconf -e "relayhost = ${POSTFIX_RELAYHOST:-}"
postconf -e "smtp_tls_security_level = may"
postconf -e "smtpd_tls_security_level = may"
postconf -e "smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination"
postconf -e "maximal_queue_lifetime = 1d"
postconf -e "bounce_queue_lifetime = 1d"

mkdir -p /var/spool/postfix/dev

if [ -n "${POSTFIX_SUBMISSION_USERNAME:-}" ] || [ -n "${POSTFIX_SUBMISSION_PASSWORD:-}" ]; then
  : "${POSTFIX_SUBMISSION_USERNAME:?POSTFIX_SUBMISSION_USERNAME is required when POSTFIX_SUBMISSION_PASSWORD is set}"
  : "${POSTFIX_SUBMISSION_PASSWORD:?POSTFIX_SUBMISSION_PASSWORD is required when POSTFIX_SUBMISSION_USERNAME is set}"
  mkdir -p /etc/postfix/sasl
  cat > /etc/postfix/sasl/smtpd.conf <<'EOF'
pwcheck_method: auxprop
auxprop_plugin: sasldb
mech_list: PLAIN LOGIN
EOF
  printf '%s\n' "$POSTFIX_SUBMISSION_PASSWORD" | saslpasswd2 -p -c -u "$POSTFIX_MYDOMAIN" "$POSTFIX_SUBMISSION_USERNAME"
  chown root:postfix /etc/sasldb2
  chmod 0640 /etc/sasldb2
  postconf -e "smtpd_sasl_auth_enable = yes"
  postconf -e "smtpd_sasl_type = cyrus"
  postconf -e "smtpd_sasl_path = smtpd"
  postconf -e "smtpd_sasl_local_domain = \$mydomain"
  postconf -e "smtpd_sasl_security_options = noanonymous"
  postconf -e "broken_sasl_auth_clients = yes"
fi

if [ -n "${POSTFIX_TLS_CERT_FILE:-}" ] || [ -n "${POSTFIX_TLS_KEY_FILE:-}" ]; then
  : "${POSTFIX_TLS_CERT_FILE:?POSTFIX_TLS_CERT_FILE is required when POSTFIX_TLS_KEY_FILE is set}"
  : "${POSTFIX_TLS_KEY_FILE:?POSTFIX_TLS_KEY_FILE is required when POSTFIX_TLS_CERT_FILE is set}"
  if [ ! -f "${POSTFIX_TLS_CERT_FILE}" ]; then
    echo "Missing Postfix TLS certificate: ${POSTFIX_TLS_CERT_FILE}" >&2
    exit 2
  fi
  if [ ! -f "${POSTFIX_TLS_KEY_FILE}" ]; then
    echo "Missing Postfix TLS private key: ${POSTFIX_TLS_KEY_FILE}" >&2
    exit 2
  fi
  postconf -e "smtpd_tls_cert_file = ${POSTFIX_TLS_CERT_FILE}"
  postconf -e "smtpd_tls_key_file = ${POSTFIX_TLS_KEY_FILE}"
  postconf -e "smtpd_tls_security_level = ${POSTFIX_TLS_SECURITY_LEVEL:-may}"
  postconf -e "smtpd_tls_auth_only = yes"
  postconf -e "smtp_tls_security_level = ${POSTFIX_OUTBOUND_TLS_SECURITY_LEVEL:-may}"
fi

if [ -n "${POSTFIX_DKIM_MILTER:-}" ]; then
  postconf -e "milter_default_action = accept"
  postconf -e "milter_protocol = 6"
  postconf -e "smtpd_milters = ${POSTFIX_DKIM_MILTER}"
  postconf -e "non_smtpd_milters = ${POSTFIX_DKIM_MILTER}"
fi

rsyslogd
postfix start-fg
