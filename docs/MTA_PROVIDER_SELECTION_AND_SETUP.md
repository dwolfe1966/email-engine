# MTA Provider Selection And Setup

Date: 2026-06-15

## Recommendation

Use a hybrid deployment:

- Keep Email Engine API/UI on Vercel or another web host with Neon/PostgreSQL.
- Deploy the first managed-SMTP MTA on a dedicated VM.
- Treat AWS EC2 as the first provider to verify if the AWS account can get outbound TCP port 25
  unblocked and PTR/rDNS aligned for an Elastic IP.
- Keep Hetzner Cloud as a low-cost backup only if the account already satisfies Hetzner's mail-port
  unblock prerequisites.
- Reject DigitalOcean, Google Cloud Compute Engine, and non-enterprise Azure subscriptions for this
  first direct-MX MTA path unless their SMTP restrictions are explicitly cleared for the account.

The first goal remains one controlled seed email through Postfix/OpenDKIM, not production volume.

## Current AWS Trial

The first AWS node is being prepared with:

- Region: `us-east-1`
- Elastic IP: `3.218.15.31`
- MTA hostname: `mta-001.email-engine.app`
- Sending domain: `email-engine.app`
- Bounce domain: `returns.email-engine.app`
- Seed mailbox: `davidtesterwex@gmail.com`

DNS has been aligned for A, PTR/rDNS, SPF, DKIM selector `ee1`, and bounce-domain MX. The MTA host
is listening publicly on TCP 25 and 587, and local SMTP banner/EHLO/STARTTLS capability smoke checks
pass. Direct seed sending remains blocked until AWS approves outbound TCP port 25.

If AWS has not approved outbound TCP port 25 by 2026-06-22, start a parallel provider review for a
second MTA host. Candidate alternates should prioritize explicit SMTP support, static IPv4, PTR/rDNS,
and a documented abuse process. Re-check current official docs/support before provisioning.

## Source-Backed Provider Notes

### AWS EC2

AWS EC2 blocks outbound port 25 to public IPv4 and IPv6 addresses by default, but AWS documents that
the restriction can be removed by request:

- <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html#port-25-throttle>

Verdict: best first production anchor if AWS approves the port 25 removal and PTR/rDNS request for
the Elastic IP.

### Google Cloud Compute Engine

Google Cloud documents that external destination TCP port 25 is blocked for Compute Engine, while
587 and 465 are allowed for relay-style sending:

- <https://cloud.google.com/compute/docs/tutorials/sending-mail>

Verdict: not suitable for our direct recipient-MX MTA path.

### Azure Virtual Machines

Azure documents that direct outbound SMTP to external domains on TCP port 25 is available only to
certain subscription types. Enterprise Agreement and MCA-E subscriptions are the practical path;
other subscription types are blocked and pushed toward authenticated relay.

- <https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-network/troubleshoot-outbound-smtp-connectivity>

Verdict: only a candidate if we already have the right enterprise subscription.

### DigitalOcean

DigitalOcean documents that SMTP ports 25, 465, and 587 are blocked on Droplets by default,
including traffic through Reserved IPs, and recommends third-party email providers.

- <https://docs.digitalocean.com/support/why-is-smtp-blocked/>

Verdict: reject for the direct-MX MTA role.

### Hetzner Cloud

Hetzner documents that ports 25 and 465 are blocked by default on all cloud servers. After one month
and payment of the first invoice, customers can submit a limit request for a valid use case; approval
is case-by-case. Port 587 is not blocked for external delivery services.

- <https://docs.hetzner.com/cloud/servers/faq/#why-can-i-not-send-any-mails-from-my-server>

Verdict: good cost profile, but not immediate unless the account already qualifies and Hetzner
approves the request.

### Vercel

Vercel remains appropriate for API/UI and lightweight scheduled HTTP-triggered work. It is not an
MTA host. Vercel Cron Jobs trigger HTTP GET requests to Vercel Functions, and Vercel Functions have
bounded request execution durations.

- <https://vercel.com/docs/cron-jobs>
- <https://vercel.com/docs/functions/limitations>

Verdict: keep for control plane only.

## AWS First-Node Setup Plan

Do not provision production traffic until AWS approves port 25 removal.

1. Choose region, probably close to the control plane and operator team.
2. Allocate one Elastic IP.
3. Request outbound port 25 removal for the Elastic IP/region/account.
4. Request or configure PTR/rDNS so the Elastic IP reverses to the MTA hostname, for example
   `mta-001.example.com`.
5. Create the VM:
   - Ubuntu 24.04 LTS or Debian 12
   - 2 vCPU / 2-4 GB RAM
   - 40-80 GB persistent disk for Postfix spool, logs, DKIM keys, TLS certs, DSN Maildir, DSN
     archive, and DSN quarantine
6. Security group:
   - inbound 22 only from trusted operator IP/VPN
   - inbound 25 from internet only if receiving bounce-domain MX traffic on the MTA
   - inbound 587 only from trusted Email Engine worker/control-plane egress IPs where possible
   - no public inbound 8891/OpenDKIM
   - outbound 25 to recipient MX hosts after AWS approval
   - outbound 443 to Email Engine API
7. DNS:
   - `A mta-001.example.com -> <Elastic IP>`
   - PTR/rDNS `<Elastic IP> -> mta-001.example.com`
   - SPF for sending domain and bounce domain
   - DKIM public key for selector, initially `ee1`
   - DMARC for sending domain
   - `MX returns.example.com -> mta-001.example.com` if using SMTP-delivered DSNs
8. Install Docker and Docker Compose plugin.
9. Prepare host directories and secrets outside the repository.
10. Fill `infra/managed-smtp/production.env.example` values on the MTA host.
11. Run:

```bash
python scripts/managed_smtp_mta_preflight.py --env-file infra/managed-smtp/production.env.example
```

12. Start the MTA:

```bash
docker compose --env-file infra/managed-smtp/production.env.example \
  -f infra/managed-smtp/docker-compose.production.yml up --build -d
```

13. Configure Email Engine production env:
   - `MANAGED_SMTP_FEEDBACK_SECRET`
   - `SMTP_HOST=mta-001.example.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME`, matching `POSTFIX_SUBMISSION_USERNAME` on the MTA host
   - `SMTP_PASSWORD`, matching `POSTFIX_SUBMISSION_PASSWORD` on the MTA host
   - `SMTP_USE_TLS=true`
14. Run `scripts/managed_smtp_bootstrap.py` with `MTA_ACTIVATE_INVENTORY=true`,
    `MTA_MARK_DOMAIN_VERIFIED=true`, `MTA_PORT25_STATUS=approved`, and
    `MTA_RDNS_STATUS=configured`.
15. Follow `docs/FIRST_MANAGED_SMTP_SEND_RUNBOOK.md`.

## Provider Decision Checklist

Answer these before provisioning:

1. Which AWS account owns the MTA infrastructure?
2. Which region will host `mta-001`?
3. Which sending domain will be used for the first seed send?
4. Which bounce domain will receive DSNs?
5. Can we edit DNS for A, MX, SPF, DKIM, and DMARC?
6. Has outbound TCP port 25 been approved?
7. Has PTR/rDNS been configured and verified?
8. What operator IPs/VPN ranges may SSH into the host?
9. What Email Engine egress IPs may submit to port 587?
10. Where will DKIM private keys and TLS private keys live on the host?
11. What seed mailbox will receive the first test?
12. Who is the go/no-go operator for the first send?
13. What is the rollback route if the seed send fails?
