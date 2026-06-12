# Managed SMTP MTA Hosting Provider Analysis Prompt

Use this document as a prompt for ChatGPT or another research assistant. The goal is to choose the best hosting model for Email Engine's managed SMTP/MTA infrastructure.

## Prompt

You are acting as a senior email infrastructure architect and cloud deployment advisor. Analyze which hosting provider and architecture we should use to deploy a production managed SMTP/MTA service for an ESP-style application called Email Engine.

We are not trying to use a paid relay such as SendGrid, Mailgun, Amazon SES, or Postmark as the primary sending service. We want to operate our own managed SMTP path with Postfix/OpenDKIM or equivalent MTA infrastructure, while still using a modern web app/API deployment model for the ESP control plane.

## Current Application Context

Email Engine currently has:

- A web/API application and ESP UI.
- PostgreSQL/Neon database.
- Campaigns, audiences, templates, send jobs, queued send records, retries, dead-letter controls, delivery attempts, feedback ingestion, suppressions, analytics, and operator UI.
- Delivery route and domain policy models, including `managed_smtp`.
- Managed SMTP readiness records, summary/trend/alerts/notification APIs, and Delivery Manager visibility.
- Postfix/OpenDKIM scaffold and production hardening docs.
- MTA smoke tests for SMTP banner, EHLO, STARTTLS, optional send submission, feedback posting, DKIM header validation, and cryptographic DKIM verification.
- DSN/log feedback ingestion tools.
- Readiness notification dispatcher with raw/Slack webhook formatting and dedupe state.

What we need next is the real deployment architecture that lets us send an actual email through the managed SMTP path.

## Key Technical Requirements

The MTA hosting provider must support:

- Long-running Postfix/OpenDKIM or equivalent MTA services.
- Static public IPv4 address, preferably dedicated.
- Ability to configure reverse DNS/PTR for the sending IP.
- Outbound SMTP delivery to recipient MX servers, especially TCP port 25.
- Inbound SMTP/DSN handling where needed, including MX for bounce domains.
- Open inbound ports for SMTP/submission where appropriate, likely:
  - 25 for MTA/MX traffic
  - 587 for authenticated submission from Email Engine workers
  - 465 optional, only if needed
- TLS certificate management.
- DKIM private key storage and OpenDKIM signing.
- Postfix spool/log persistence.
- Maildir or equivalent storage for DSNs/bounces.
- Firewall/security group control.
- Monitoring/log access.
- A clean path to automate provisioning via Terraform, cloud-init, Ansible, Docker Compose, or similar.

The provider should ideally support:

- Good IP reputation or at least a clean path to request/verify clean IPs.
- Abuse/compliance process that allows legitimate transactional/bulk email.
- Ability to start with low-volume warmup and grow.
- Reasonable cost for 1-2 small production MTA nodes.
- Backups/snapshots.
- IPv6 only if useful, not required.
- Separating the ESP API/UI from the MTA host.

## Important Existing Hosting Assumption

Vercel may remain useful for the UI/API/control plane, but Vercel is probably not appropriate for the actual MTA host because an MTA needs long-running daemons, static IP/PTR control, SMTP ports, spool/log persistence, and direct TCP server behavior.

Please verify this assumption. If you think Vercel can support any part of the MTA path, explain exactly which part and which part must run elsewhere.

## Candidate Provider Set

Analyze at least these options:

- AWS EC2, with Elastic IP and port 25 removal request.
- Google Cloud Compute Engine.
- Microsoft Azure Virtual Machines.
- DigitalOcean Droplets.
- Hetzner Cloud or dedicated server.
- OVHcloud VPS/dedicated.
- A reputable SMTP-friendly VPS or bare-metal provider if there is a better option.
- Hybrid: Vercel/Render/Fly.io for app + separate VPS/VM for MTA.

If a provider should be rejected, say so clearly and why.

## Known Provider Constraint Hints To Verify

Use current official documentation and cite sources. At minimum, verify:

- AWS EC2 has default outbound port 25 restrictions to public IPs and a request process to remove the restriction.
- Google Cloud Compute Engine has restrictions or guidance around sending email from instances.
- Azure has outbound SMTP/port 25 restrictions depending on subscription/resource type.
- DigitalOcean may block SMTP for some accounts or require support review.
- Vercel cron/jobs/functions are not an MTA substitute; clarify their appropriate role.

Useful starting sources:

- AWS EC2 service quotas and port 25 restriction: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html
- Google Cloud sending email from Compute Engine: https://cloud.google.com/compute/docs/tutorials/sending-mail
- Azure outbound SMTP troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-network/troubleshoot-outbound-smtp-connectivity
- DigitalOcean SMTP blocked support doc: https://docs.digitalocean.com/support/why-is-smtp-blocked/
- Vercel Cron Jobs: https://vercel.com/docs/cron-jobs
- Vercel Functions limits: https://vercel.com/docs/functions/limitations

## Required Output Format

Return the analysis in this exact structure:

1. Executive recommendation
   - Choose the recommended provider/model.
   - State whether Vercel should remain in the architecture.
   - State the first production topology.

2. Provider comparison table
   Include columns:
   - Provider
   - Static IP support
   - Reverse DNS/PTR support
   - Port 25 policy
   - Inbound SMTP support
   - Operational complexity
   - Deliverability risk
   - Cost estimate for first production node
   - Pros
   - Cons
   - Verdict

3. Recommended architecture
   Include:
   - ESP UI/API host
   - Database
   - Queue/worker placement
   - MTA host placement
   - DNS responsibilities
   - Feedback/DSN path
   - Monitoring/alerting
   - Backup/snapshot strategy

4. Minimum viable production MTA deployment
   Describe exactly what to provision for sending the first real email:
   - VM size
   - OS
   - public IP
   - DNS records
   - ports/firewall
   - Docker Compose or native packages
   - TLS
   - DKIM
   - Postfix queue/log storage
   - submission credentials
   - smoke test sequence

5. Migration from current state
   Provide a concrete step-by-step implementation plan that our coding agent can execute in the repo.

6. Risks and mitigations
   Include:
   - port 25 denial
   - dirty IP/reputation
   - PTR mismatch
   - DKIM/SPF/DMARC misconfig
   - bounce loop failure
   - abuse handling
   - provider account suspension risk
   - Vercel/serverless limitations

7. Final decision checklist
   List the 10-15 questions we must answer before provisioning.

8. Sources
   Cite official provider documentation wherever possible.

## Constraints

- Do not recommend a paid email relay as the primary solution.
- Do not ignore deliverability or abuse/compliance risk.
- Do not assume port 25 is available without verification.
- Do not assume serverless platforms can run an MTA.
- Prefer a pragmatic first production setup over an over-engineered multi-region architecture.
- The first goal is one real email through our managed SMTP path, then controlled warmup.

## Desired Bias

Bias toward a provider/model that:

- Gives us direct control over Postfix/OpenDKIM.
- Allows static IP and reverse DNS/PTR.
- Has a realistic path to outbound port 25.
- Is simple enough to deploy quickly.
- Does not force the entire ESP app off its current hosting if only the MTA needs separate infrastructure.

