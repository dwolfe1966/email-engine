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

rsyslogd
postfix start-fg
