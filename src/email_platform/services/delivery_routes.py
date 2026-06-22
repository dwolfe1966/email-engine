import secrets
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    DeliveryAttempt,
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    DomainDeliveryPolicy,
    EmailSendRecord,
)
from email_platform.schemas.contracts import (
    DeliveryRouteCreate,
    DeliveryRouteUpdate,
    DomainAuthenticationDnsRecord,
    DomainAuthenticationPlanRead,
    DomainAuthenticationPlanRequest,
    DomainAuthenticationVerificationRead,
    DomainAuthenticationVerificationRecord,
    DomainBlocklistScanRead,
    DomainBlocklistScanRecord,
    DomainBlocklistScanRequest,
    DomainComplianceHoldRequest,
    DomainComplianceReleaseRequest,
    DomainDeliverabilityRead,
    DomainDeliveryPolicyCreate,
    DomainDeliveryPolicyUpdate,
    DomainDkimKeyCreateRead,
    DomainDkimKeyCreateRequest,
    DomainReputationDashboardRead,
    DomainWarmupProgressionRead,
    DomainWarmupProgressionRequest,
    ManagedSmtpRoutingRuleUpsert,
    ManagedSmtpRoutingRulesRead,
    ManagedSmtpMaintenancePolicyRead,
    ManagedSmtpMaintenanceRead,
    ManagedSmtpMaintenanceRequest,
)


@dataclass(frozen=True)
class SelectedDeliveryRoute:
    route_type: str
    route_key: str
    route_id: UUID | None = None
    domain_policy_id: UUID | None = None
    name: str | None = None
    domain: str | None = None
    warmup_stage: str | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    source: str = 'fallback'


@dataclass(frozen=True)
class DeliveryClaimDecision:
    can_claim: bool
    reason: str | None = None
    domain: str | None = None
    domain_policy_id: UUID | None = None


@dataclass(frozen=True)
class ManagedSmtpIdentity:
    domain: str
    bounce_domain: str | None = None
    envelope_from: str | None = None
    dkim_selector: str | None = None
    dkim_key_ref: str | None = None
    dkim_signing_ready: bool = False


class DnsLookupUnavailable(ValueError):
    pass


class SystemDnsResolver:
    def lookup(self, record_type: str, name: str) -> list[str]:
        try:
            completed = subprocess.run(
                ['dig', '+short', record_type, name],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise DnsLookupUnavailable(str(exc)) from exc
        if completed.returncode != 0:
            raise DnsLookupUnavailable(completed.stderr.strip() or 'DNS lookup failed')
        return [line.strip().strip('"') for line in completed.stdout.splitlines() if line.strip()]


class OpensslDkimKeyGenerator:
    def generate(self, key_size: int) -> tuple[str, str]:
        try:
            private_result = subprocess.run(
                ['openssl', 'genrsa', str(key_size)],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            public_result = subprocess.run(
                ['openssl', 'rsa', '-pubout'],
                input=private_result.stdout,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError('OpenSSL is required to generate DKIM keys') from exc
        public_key = ''.join(
            line.strip()
            for line in public_result.stdout.splitlines()
            if 'BEGIN PUBLIC KEY' not in line and 'END PUBLIC KEY' not in line
        )
        return private_result.stdout, public_key


class DeliveryRouteService:
    def __init__(
        self,
        db: Session,
        dns_resolver: SystemDnsResolver | None = None,
        dkim_key_generator: OpensslDkimKeyGenerator | None = None,
    ) -> None:
        self.db = db
        self.dns_resolver = dns_resolver or SystemDnsResolver()
        self.dkim_key_generator = dkim_key_generator or OpensslDkimKeyGenerator()

    def create(self, payload: DeliveryRouteCreate) -> DeliveryRoute:
        route = DeliveryRoute(**payload.model_dump())
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route

    def get(self, route_id: UUID) -> DeliveryRoute | None:
        return self.db.get(DeliveryRoute, route_id)

    def list_items(
        self,
        route_type: DeliveryRouteType | None = None,
        status: DeliveryRouteStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryRoute]:
        statement = select(DeliveryRoute).order_by(
            DeliveryRoute.priority.asc(),
            DeliveryRoute.created_at.desc(),
        )
        if route_type:
            statement = statement.where(DeliveryRoute.route_type == route_type)
        if status:
            statement = statement.where(DeliveryRoute.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count(
        self,
        route_type: DeliveryRouteType | None = None,
        status: DeliveryRouteStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(DeliveryRoute)
        if route_type:
            statement = statement.where(DeliveryRoute.route_type == route_type)
        if status:
            statement = statement.where(DeliveryRoute.status == status)
        return self.db.scalar(statement) or 0

    def update(self, route_id: UUID, payload: DeliveryRouteUpdate) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(route, key, value)
        self.db.commit()
        self.db.refresh(route)
        return route

    def pause_route(self, route_id: UUID) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        route.status = DeliveryRouteStatus.paused
        self.db.commit()
        self.db.refresh(route)
        return route

    def resume_route(self, route_id: UUID) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        route.status = DeliveryRouteStatus.active
        self.db.commit()
        self.db.refresh(route)
        return route

    def managed_smtp_routing_rules(self, route_id: UUID) -> ManagedSmtpRoutingRulesRead | None:
        route = self.get(route_id)
        if not route:
            return None
        rules = self._routing_rules_from_route(route)
        return ManagedSmtpRoutingRulesRead(
            delivery_route_id=route.id,
            delivery_route_name=route.name,
            rules=rules,
            conflicts=self._routing_rule_conflicts(rules),
        )

    def upsert_managed_smtp_routing_rule(
        self,
        route_id: UUID,
        payload: ManagedSmtpRoutingRuleUpsert,
    ) -> ManagedSmtpRoutingRulesRead | None:
        route = self.get(route_id)
        if not route:
            return None
        config = dict(route.config or {})
        existing_rules = self._routing_rules_from_route(route)
        normalized_rule = self._normalized_routing_rule(payload)
        next_rules = [
            rule for rule in existing_rules if str(rule.get('name') or '') != normalized_rule['name']
        ]
        next_rules.append(normalized_rule)
        next_rules.sort(key=lambda rule: int(rule.get('priority') or 100))
        config['routing_rules'] = next_rules
        route.config = config
        self.db.commit()
        self.db.refresh(route)
        return ManagedSmtpRoutingRulesRead(
            delivery_route_id=route.id,
            delivery_route_name=route.name,
            rules=next_rules,
            conflicts=self._routing_rule_conflicts(next_rules),
        )

    def set_managed_smtp_routing_rule_enabled(
        self,
        route_id: UUID,
        rule_name: str,
        enabled: bool,
    ) -> ManagedSmtpRoutingRulesRead | None:
        route = self.get(route_id)
        if not route:
            return None
        rules = self._routing_rules_from_route(route)
        matched = False
        for rule in rules:
            if str(rule.get('name') or '') == rule_name:
                rule['enabled'] = enabled
                matched = True
        if not matched:
            return None
        return self._write_routing_rules(route, rules)

    def delete_managed_smtp_routing_rule(
        self,
        route_id: UUID,
        rule_name: str,
    ) -> ManagedSmtpRoutingRulesRead | None:
        route = self.get(route_id)
        if not route:
            return None
        rules = self._routing_rules_from_route(route)
        next_rules = [rule for rule in rules if str(rule.get('name') or '') != rule_name]
        if len(next_rules) == len(rules):
            return None
        return self._write_routing_rules(route, next_rules)

    def delete(self, route_id: UUID) -> bool:
        route = self.get(route_id)
        if not route:
            return False
        self.db.delete(route)
        self.db.commit()
        return True

    def _routing_rules_from_route(self, route: DeliveryRoute) -> list[dict[str, object]]:
        config = route.config or {}
        rules = config.get('routing_rules') if isinstance(config, dict) else None
        if not isinstance(rules, list):
            return []
        normalized_rules = [dict(rule) for rule in rules if isinstance(rule, dict)]
        return sorted(normalized_rules, key=lambda rule: int(rule.get('priority') or 100))

    def _write_routing_rules(
        self,
        route: DeliveryRoute,
        rules: list[dict[str, object]],
    ) -> ManagedSmtpRoutingRulesRead:
        next_rules = sorted(rules, key=lambda rule: int(rule.get('priority') or 100))
        config = dict(route.config or {})
        config['routing_rules'] = next_rules
        route.config = config
        self.db.commit()
        self.db.refresh(route)
        return ManagedSmtpRoutingRulesRead(
            delivery_route_id=route.id,
            delivery_route_name=route.name,
            rules=next_rules,
            conflicts=self._routing_rule_conflicts(next_rules),
        )

    def _normalized_routing_rule(
        self,
        payload: ManagedSmtpRoutingRuleUpsert,
    ) -> dict[str, object]:
        data = payload.model_dump()
        rule: dict[str, object] = {
            'name': payload.name.strip(),
            'priority': payload.priority,
            'enabled': payload.enabled,
            'send_types': self._normalized_string_list(data.get('send_types')),
            'sender_domains': self._normalized_domain_list(data.get('sender_domains')),
            'recipient_domains': self._normalized_domain_list(data.get('recipient_domains')),
            'preferred_providers': self._normalized_string_list(data.get('preferred_providers')),
            'provider_preference_mode': self._provider_preference_mode(
                data.get('provider_preference_mode')
            ),
        }
        if payload.mta_ip_pool_id:
            rule['mta_ip_pool_id'] = str(payload.mta_ip_pool_id)
        if payload.ip_pool_name:
            rule['ip_pool_name'] = payload.ip_pool_name.strip()
        return rule

    def _provider_preference_mode(self, value: object) -> str:
        mode = str(value or 'strict').strip().lower()
        if mode in {'fallback_allowed', 'allow_fallback', 'fallback'}:
            return 'fallback_allowed'
        return 'strict'

    def _routing_rule_conflicts(self, rules: list[dict[str, object]]) -> list[dict[str, object]]:
        enabled_rules = [rule for rule in rules if rule.get('enabled') is not False]
        conflicts: list[dict[str, object]] = []
        for index, first in enumerate(enabled_rules):
            for second in enabled_rules[index + 1:]:
                if int(first.get('priority') or 100) != int(second.get('priority') or 100):
                    continue
                overlapping_dimensions = [
                    dimension
                    for dimension in ('send_types', 'sender_domains', 'recipient_domains')
                    if self._routing_rule_dimension_overlaps(
                        first.get(dimension),
                        second.get(dimension),
                        normalize_domains=dimension.endswith('_domains'),
                    )
                ]
                if len(overlapping_dimensions) != 3:
                    continue
                conflicts.append(
                    {
                        'severity': 'warning',
                        'code': 'ROUTING_RULE_OVERLAP',
                        'rule_names': [
                            str(first.get('name') or 'unnamed'),
                            str(second.get('name') or 'unnamed'),
                        ],
                        'priority': int(first.get('priority') or 100),
                        'overlapping_dimensions': overlapping_dimensions,
                        'message': (
                            'Enabled routing rules share priority and overlapping match criteria.'
                        ),
                    }
                )
        return conflicts

    def _routing_rule_dimension_overlaps(
        self,
        first: object,
        second: object,
        normalize_domains: bool = False,
    ) -> bool:
        normalizer = self._normalized_domain_list if normalize_domains else self._normalized_string_list
        first_values = set(normalizer(first))
        second_values = set(normalizer(second))
        if not first_values or not second_values:
            return True
        if '*' in first_values or '*' in second_values:
            return True
        return bool(first_values.intersection(second_values))

    @staticmethod
    def _normalized_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip().lower() for item in value if str(item).strip()]

    def _normalized_domain_list(self, value: object) -> list[str]:
        return [
            domain
            for domain in (self._normalized_domain(str(item)) for item in value or [])
            if domain
        ]

    def create_domain_policy(
        self,
        payload: DomainDeliveryPolicyCreate,
    ) -> DomainDeliveryPolicy:
        policy = DomainDeliveryPolicy(
            **{
                **payload.model_dump(),
                'domain': payload.domain.lower(),
            }
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_domain_policy(self, policy_id: UUID) -> DomainDeliveryPolicy | None:
        return self.db.get(DomainDeliveryPolicy, policy_id)

    def list_domain_policies(
        self,
        domain: str | None = None,
        route_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DomainDeliveryPolicy]:
        statement = select(DomainDeliveryPolicy).order_by(
            DomainDeliveryPolicy.domain.asc(),
            DomainDeliveryPolicy.created_at.desc(),
        )
        if domain:
            statement = statement.where(DomainDeliveryPolicy.domain == domain.lower())
        if route_id:
            statement = statement.where(DomainDeliveryPolicy.route_id == route_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_domain_policies(
        self,
        domain: str | None = None,
        route_id: UUID | None = None,
    ) -> int:
        statement = select(func.count()).select_from(DomainDeliveryPolicy)
        if domain:
            statement = statement.where(DomainDeliveryPolicy.domain == domain.lower())
        if route_id:
            statement = statement.where(DomainDeliveryPolicy.route_id == route_id)
        return self.db.scalar(statement) or 0

    def update_domain_policy(
        self,
        policy_id: UUID,
        payload: DomainDeliveryPolicyUpdate,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        values = payload.model_dump(exclude_unset=True)
        if 'domain' in values and values['domain']:
            values['domain'] = str(values['domain']).lower()
        for key, value in values.items():
            setattr(policy, key, value)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def pause_domain_policy(
        self,
        policy_id: UUID,
        paused_until: datetime | None = None,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        policy.paused_until = paused_until or datetime.utcnow() + timedelta(hours=1)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def resume_domain_policy(self, policy_id: UUID) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        policy.paused_until = None
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def apply_domain_compliance_hold(
        self,
        policy_id: UUID,
        payload: DomainComplianceHoldRequest,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        held_at = datetime.utcnow()
        held_until = held_at + timedelta(hours=payload.paused_hours)
        metadata = dict(policy.metadata_json or {})
        hold = {
            'status': 'active',
            'reason': payload.reason.strip(),
            'abuse_type': payload.abuse_type.strip(),
            'operator': payload.operator,
            'held_at': held_at.isoformat(),
            'held_until': held_until.isoformat(),
        }
        metadata['compliance_hold'] = hold
        metadata['compliance_audit_log'] = self._append_compliance_audit(
            metadata,
            {
                'action': 'hold',
                'status': 'active',
                'reason': hold['reason'],
                'abuse_type': hold['abuse_type'],
                'operator': payload.operator,
                'occurred_at': held_at.isoformat(),
                'held_until': held_until.isoformat(),
                'previous_paused_until': (
                    policy.paused_until.isoformat() if policy.paused_until else None
                ),
            },
        )
        policy.paused_until = held_until
        policy.metadata_json = metadata
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def release_domain_compliance_hold(
        self,
        policy_id: UUID,
        payload: DomainComplianceReleaseRequest,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        released_at = datetime.utcnow()
        metadata = dict(policy.metadata_json or {})
        previous_hold = metadata.get('compliance_hold')
        metadata['compliance_hold'] = {
            'status': 'released',
            'reason': payload.reason.strip(),
            'operator': payload.operator,
            'released_at': released_at.isoformat(),
            'previous_hold': previous_hold if isinstance(previous_hold, dict) else None,
        }
        metadata['compliance_audit_log'] = self._append_compliance_audit(
            metadata,
            {
                'action': 'release',
                'status': 'released',
                'reason': payload.reason.strip(),
                'operator': payload.operator,
                'occurred_at': released_at.isoformat(),
                'previous_paused_until': (
                    policy.paused_until.isoformat() if policy.paused_until else None
                ),
            },
        )
        policy.paused_until = None
        policy.metadata_json = metadata
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_domain_policy(self, policy_id: UUID) -> bool:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True

    def build_domain_authentication_plan(
        self,
        policy_id: UUID,
        payload: DomainAuthenticationPlanRequest,
    ) -> DomainAuthenticationPlanRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        plan = self._domain_authentication_plan(policy.domain, payload)
        policy.metadata_json = {
            **(policy.metadata_json or {}),
            'domain_authentication': plan.model_dump(),
        }
        self.db.commit()
        self.db.refresh(policy)
        return plan

    def create_domain_dkim_key(
        self,
        policy_id: UUID,
        payload: DomainDkimKeyCreateRequest,
    ) -> DomainDkimKeyCreateRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        selector = payload.dkim_selector.strip().lower() or 'ee1'
        private_key_pem, public_key = self.dkim_key_generator.generate(payload.key_size)
        key_ref = (
            payload.key_ref
            or f'dkim/{policy.domain.lower()}/{selector}/{secrets.token_urlsafe(8)}'
        )
        dns_record = DomainAuthenticationDnsRecord(
            record_type='TXT',
            name=f'{selector}._domainkey.{policy.domain.lower()}',
            value=f'v=DKIM1; k=rsa; p={public_key}',
            purpose='Authorize Email Engine managed SMTP DKIM signing for this domain.',
        )
        policy.metadata_json = {
            **(policy.metadata_json or {}),
            'dkim_key': {
                'selector': selector,
                'key_ref': key_ref,
                'public_key': public_key,
                'dns_record': dns_record.model_dump(),
                'created_at': datetime.utcnow().isoformat(),
            },
        }
        self.db.commit()
        self.db.refresh(policy)
        return DomainDkimKeyCreateRead(
            domain=policy.domain.lower(),
            dkim_selector=selector,
            key_ref=key_ref,
            public_key=public_key,
            private_key_pem=private_key_pem,
            dns_record=dns_record,
        )

    def verify_domain_authentication(
        self,
        policy_id: UUID,
    ) -> DomainAuthenticationVerificationRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        plan_data = (policy.metadata_json or {}).get('domain_authentication')
        if not isinstance(plan_data, dict):
            return DomainAuthenticationVerificationRead(
                domain=policy.domain.lower(),
                verified=False,
                records=[],
            )
        records = [
            self._verify_dns_record(DomainAuthenticationDnsRecord.model_validate(record))
            for record in plan_data.get('dns_records', [])
            if isinstance(record, dict)
        ]
        policy.metadata_json = {
            **(policy.metadata_json or {}),
            'domain_authentication_verification': {
                'verified': all(
                    record.status == 'verified' for record in records if record.required
                ),
                'checked_at': datetime.utcnow().isoformat(),
                'records': [record.model_dump() for record in records],
            },
        }
        self.db.commit()
        self.db.refresh(policy)
        return DomainAuthenticationVerificationRead(
            domain=policy.domain.lower(),
            verified=all(record.status == 'verified' for record in records if record.required),
            records=records,
        )

    def scan_domain_blocklists(
        self,
        policy_id: UUID,
        payload: DomainBlocklistScanRequest,
    ) -> DomainBlocklistScanRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        route = self.db.get(DeliveryRoute, policy.route_id) if policy.route_id else None
        metadata = dict(policy.metadata_json or {})
        requested_ips = self._clean_list(payload.ip_addresses or [])
        ip_addresses = (
            requested_ips
            or self._metadata_list(metadata, 'ip_addresses')
            or self._route_ip_addresses(route)
        )
        zones = self._clean_list(payload.zones)
        checked_at = datetime.utcnow().isoformat()
        records: list[DomainBlocklistScanRecord] = []
        hits: list[str] = []
        for ip_address in ip_addresses:
            for zone in zones:
                record = self._scan_blocklist_zone(ip_address, zone)
                records.append(record)
                if record.status == 'listed':
                    hits.append(f'{ip_address}@{zone}')

        status = self._blocklist_scan_status(records, hits)
        if payload.update_metadata:
            metadata['ip_addresses'] = ip_addresses
            metadata['blocklist_status'] = status
            metadata['blocklist_hits'] = hits
            if status != 'unknown':
                metadata['blocklist_checked_at'] = checked_at
            policy.metadata_json = metadata
            self.db.commit()
            self.db.refresh(policy)
        return DomainBlocklistScanRead(
            domain=policy.domain.lower(),
            checked_at=checked_at,
            ip_addresses=ip_addresses,
            status=status,
            hits=hits,
            records=records,
        )

    def progress_domain_warmup(
        self,
        policy_id: UUID,
        payload: DomainWarmupProgressionRequest,
        deliverability: DomainDeliverabilityRead | None = None,
    ) -> DomainWarmupProgressionRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        metadata = dict(policy.metadata_json or {})
        evaluated_at = datetime.utcnow().isoformat()
        previous_stage = policy.warmup_stage
        previous_daily_limit = self._metadata_int(metadata, 'warmup_daily_limit')
        previous_stage_order = self._metadata_int(metadata, 'warmup_stage_order')
        sent_count = deliverability.sent_count if deliverability else 0
        bounce_rate = deliverability.bounce_rate if deliverability else 0.0
        complaint_rate = self._rate(
            deliverability.complained_count if deliverability else 0,
            max(sent_count, deliverability.send_record_count if deliverability else 0),
        )
        action, status, reason = self._warmup_progression_decision(
            payload=payload,
            metadata=metadata,
            sent_count=sent_count,
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
        )
        current_stage = previous_stage
        current_daily_limit = previous_daily_limit
        current_stage_order = previous_stage_order
        if action == 'advance':
            current_stage_order = (previous_stage_order or 0) + 1
            current_stage = payload.next_stage or f'stage_{current_stage_order}'
            current_daily_limit = payload.next_daily_limit or self._next_warmup_daily_limit(
                previous_daily_limit
            )
            policy.warmup_stage = current_stage
            metadata['warmup_stage_order'] = current_stage_order
            metadata['warmup_daily_limit'] = current_daily_limit
            metadata['warmup_last_advanced_at'] = evaluated_at
        elif action == 'hold':
            metadata['warmup_hold_reason'] = reason
            metadata['warmup_last_hold_at'] = evaluated_at

        metadata['warmup_status'] = status
        metadata['warmup_last_evaluated_at'] = evaluated_at
        metadata['warmup_audit_log'] = self._append_warmup_audit(
            metadata,
            {
                'action': action,
                'status': status,
                'reason': reason,
                'operator': payload.operator,
                'evaluated_at': evaluated_at,
                'previous_stage': previous_stage,
                'current_stage': current_stage,
                'previous_daily_limit': previous_daily_limit,
                'current_daily_limit': current_daily_limit,
                'sent_count': sent_count,
                'bounce_rate': bounce_rate,
                'complaint_rate': complaint_rate,
                'gate_evidence': payload.gate_evidence,
            },
        )
        policy.metadata_json = metadata
        self.db.commit()
        self.db.refresh(policy)
        return DomainWarmupProgressionRead(
            domain=policy.domain.lower(),
            previous_stage=previous_stage,
            current_stage=current_stage,
            previous_daily_limit=previous_daily_limit,
            current_daily_limit=current_daily_limit,
            previous_stage_order=previous_stage_order,
            current_stage_order=current_stage_order,
            action=action,
            status=status,
            reason=reason,
            evaluated_at=evaluated_at,
            sent_count=sent_count,
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
        )

    def run_managed_smtp_maintenance(
        self,
        payload: ManagedSmtpMaintenanceRequest,
        deliverability_by_domain: dict[str, DomainDeliverabilityRead] | None = None,
    ) -> ManagedSmtpMaintenanceRead:
        deliverability_by_domain = deliverability_by_domain or {}
        policies = self.list_domain_policies(limit=payload.limit)
        results: list[ManagedSmtpMaintenancePolicyRead] = []
        blocklist_scan_count = 0
        warmup_progression_count = 0
        skipped_count = 0
        for policy in policies:
            route = self.db.get(DeliveryRoute, policy.route_id) if policy.route_id else None
            route_type = route.route_type if route else None
            if (
                not payload.include_all_route_types
                and route_type is not DeliveryRouteType.managed_smtp
            ):
                skipped_count += 1
                results.append(
                    ManagedSmtpMaintenancePolicyRead(
                        policy_id=policy.id,
                        domain=policy.domain,
                        route_type=route_type,
                        skipped_reason='not_managed_smtp',
                    )
                )
                continue

            blocklist_status: str | None = None
            blocklist_hits: list[str] = []
            if payload.scan_blocklists:
                blocklist = self.scan_domain_blocklists(
                    policy.id,
                    DomainBlocklistScanRequest(zones=payload.zones),
                )
                if blocklist:
                    blocklist_scan_count += 1
                    blocklist_status = blocklist.status
                    blocklist_hits = blocklist.hits

            warmup: DomainWarmupProgressionRead | None = None
            if payload.progress_warmup:
                warmup = self.progress_domain_warmup(
                    policy.id,
                    DomainWarmupProgressionRequest(
                        advance=payload.advance_warmup,
                        max_bounce_rate=payload.max_bounce_rate,
                        max_complaint_rate=payload.max_complaint_rate,
                        min_sent_count=payload.min_sent_count,
                        operator=payload.operator,
                    ),
                    deliverability=deliverability_by_domain.get(policy.domain.lower()),
                )
                if warmup:
                    warmup_progression_count += 1

            metadata = policy.metadata_json or {}
            results.append(
                ManagedSmtpMaintenancePolicyRead(
                    policy_id=policy.id,
                    domain=policy.domain,
                    route_type=route_type,
                    blocklist_status=blocklist_status,
                    blocklist_hits=blocklist_hits,
                    warmup_action=warmup.action if warmup else None,
                    warmup_status=warmup.status if warmup else None,
                    warmup_stage=policy.warmup_stage,
                    warmup_daily_limit=self._metadata_int(metadata, 'warmup_daily_limit'),
                )
            )

        return ManagedSmtpMaintenanceRead(
            processed_count=len(policies) - skipped_count,
            blocklist_scan_count=blocklist_scan_count,
            warmup_progression_count=warmup_progression_count,
            skipped_count=skipped_count,
            results=results,
        )

    def domain_reputation_dashboard(
        self,
        policy_id: UUID,
        deliverability: DomainDeliverabilityRead | None = None,
    ) -> DomainReputationDashboardRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        route = self.db.get(DeliveryRoute, policy.route_id) if policy.route_id else None
        metadata = policy.metadata_json or {}
        verification = metadata.get('domain_authentication_verification')
        authentication_verified = bool(
            isinstance(verification, dict) and verification.get('verified')
        )
        ip_pool = self._metadata_string(metadata, 'ip_pool') or self._route_ip_pool(route)
        ip_addresses = self._metadata_list(metadata, 'ip_addresses') or self._route_ip_addresses(
            route
        )
        blocklist_hits = self._metadata_list(metadata, 'blocklist_hits') or self._route_list(
            route,
            'blocklist_hits',
        )
        blocklist_checked_at = self._metadata_string(metadata, 'blocklist_checked_at')
        blocklist_status = self._metadata_string(metadata, 'blocklist_status') or (
            self._blocklist_status(
                blocklist_hits=blocklist_hits,
                blocklist_checked_at=blocklist_checked_at,
                ip_addresses=ip_addresses,
            )
        )
        send_record_count = deliverability.send_record_count if deliverability else 0
        sent_count = deliverability.sent_count if deliverability else 0
        delivered_count = deliverability.delivered_count if deliverability else 0
        bounced_count = deliverability.bounced_count if deliverability else 0
        complained_count = deliverability.complained_count if deliverability else 0
        bounce_rate = deliverability.bounce_rate if deliverability else 0.0
        complaint_rate = self._rate(complained_count, max(sent_count, send_record_count))
        warmup_status = self._warmup_status(
            policy=policy,
            send_record_count=send_record_count,
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
        )
        reputation_status = self._reputation_status(
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
            authentication_verified=authentication_verified,
            blocklist_hits=blocklist_hits,
        )
        compliance_hold = metadata.get('compliance_hold')
        compliance_active = bool(
            isinstance(compliance_hold, dict) and compliance_hold.get('status') == 'active'
        )
        compliance_reason = (
            str(compliance_hold.get('reason'))
            if isinstance(compliance_hold, dict) and compliance_hold.get('reason')
            else None
        )
        throttle_status = self._throttle_status(policy)
        return DomainReputationDashboardRead(
            domain=policy.domain,
            route_id=policy.route_id,
            route_name=route.name if route else None,
            route_type=route.route_type if route else None,
            warmup_stage=policy.warmup_stage,
            warmup_status=warmup_status,
            warmup_daily_limit=self._metadata_int(metadata, 'warmup_daily_limit'),
            warmup_stage_order=self._metadata_int(metadata, 'warmup_stage_order'),
            ip_pool=ip_pool,
            ip_addresses=ip_addresses,
            blocklist_status=blocklist_status,
            blocklist_hits=blocklist_hits,
            blocklist_checked_at=blocklist_checked_at,
            max_per_minute=policy.max_per_minute,
            max_concurrent=policy.max_concurrent,
            paused_until=policy.paused_until,
            authentication_verified=authentication_verified,
            authentication_status='verified' if authentication_verified else 'pending',
            reputation_status=reputation_status,
            throttle_status=throttle_status,
            compliance_status='hold' if compliance_active else 'clear',
            compliance_reason=compliance_reason,
            send_record_count=send_record_count,
            sent_count=sent_count,
            delivered_count=delivered_count,
            bounced_count=bounced_count,
            complained_count=complained_count,
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
            recommendations=self._reputation_recommendations(
                policy=policy,
                authentication_verified=authentication_verified,
                reputation_status=reputation_status,
                send_record_count=send_record_count,
                bounce_rate=bounce_rate,
                complaint_rate=complaint_rate,
                ip_pool=ip_pool,
                ip_addresses=ip_addresses,
                blocklist_status=blocklist_status,
                blocklist_hits=blocklist_hits,
                warmup_status=warmup_status,
                compliance_active=compliance_active,
            ),
        )

    def select_for_record(
        self,
        record: EmailSendRecord,
        settings: Settings,
        sender_domain: str | None = None,
    ) -> SelectedDeliveryRoute:
        domain = self._normalized_domain(sender_domain) or self._domain_for_record(record)
        if domain:
            policy = self._active_domain_policy(domain)
            if policy and policy.route_id:
                route = self.db.get(DeliveryRoute, policy.route_id)
                if route and route.status == DeliveryRouteStatus.active:
                    return SelectedDeliveryRoute(
                        route_type=route.route_type.value,
                        route_key=route.name,
                        route_id=route.id,
                        domain_policy_id=policy.id,
                        name=route.name,
                        domain=policy.domain,
                        warmup_stage=policy.warmup_stage,
                        max_per_minute=policy.max_per_minute,
                        max_concurrent=policy.max_concurrent,
                        source='domain_policy',
                    )

        configured_type = self._configured_route_type(settings.email_provider)
        if configured_type:
            route = self.db.scalar(
                select(DeliveryRoute)
                .where(DeliveryRoute.status == DeliveryRouteStatus.active)
                .where(DeliveryRoute.route_type == configured_type)
                .order_by(DeliveryRoute.priority.asc(), DeliveryRoute.created_at.desc())
                .limit(1)
            )
            if route:
                return SelectedDeliveryRoute(
                    route_type=route.route_type.value,
                    route_key=route.name,
                    route_id=route.id,
                    name=route.name,
                    domain=domain,
                    source='delivery_routes',
                )

        route_type = configured_type.value if configured_type else settings.email_provider
        return SelectedDeliveryRoute(
            route_type=route_type,
            route_key=settings.email_provider,
            domain=domain,
            source='settings',
        )

    def claim_decision(
        self,
        record: EmailSendRecord,
        reserved_count: int = 0,
    ) -> DeliveryClaimDecision:
        domain = self._domain_for_record(record)
        if not domain:
            return DeliveryClaimDecision(can_claim=True)

        policy = self._domain_policy(domain)
        if not policy:
            return DeliveryClaimDecision(can_claim=True, domain=domain)
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return DeliveryClaimDecision(
                can_claim=False,
                reason='domain_policy_paused',
                domain=domain,
                domain_policy_id=policy.id,
            )
        if policy.max_per_minute is not None:
            recent_count = self._recent_domain_attempt_count(domain, seconds=60)
            if recent_count + reserved_count >= policy.max_per_minute:
                return DeliveryClaimDecision(
                    can_claim=False,
                    reason='domain_policy_max_per_minute',
                    domain=domain,
                    domain_policy_id=policy.id,
                )
        if policy.max_concurrent is not None:
            active_count = self._active_domain_attempt_count(domain)
            if active_count + reserved_count >= policy.max_concurrent:
                return DeliveryClaimDecision(
                    can_claim=False,
                    reason='domain_policy_max_concurrent',
                    domain=domain,
                    domain_policy_id=policy.id,
                )
        return DeliveryClaimDecision(
            can_claim=True,
            domain=domain,
            domain_policy_id=policy.id,
        )

    def _domain_policy(self, domain: str) -> DomainDeliveryPolicy | None:
        return self.db.scalar(
            select(DomainDeliveryPolicy)
            .where(DomainDeliveryPolicy.domain == domain)
            .limit(1)
        )

    def _active_domain_policy(self, domain: str) -> DomainDeliveryPolicy | None:
        policy = self._domain_policy(domain)
        if not policy:
            return None
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return None
        return policy

    def _configured_route_type(self, email_provider: str) -> DeliveryRouteType | None:
        if email_provider == 'smtp':
            return DeliveryRouteType.smtp_relay
        try:
            return DeliveryRouteType(email_provider)
        except ValueError:
            return None

    def _domain_authentication_plan(
        self,
        domain: str,
        payload: DomainAuthenticationPlanRequest,
    ) -> DomainAuthenticationPlanRead:
        normalized_domain = domain.lower()
        selector = payload.dkim_selector.strip().lower() or 'ee1'
        bounce_subdomain = payload.bounce_subdomain.strip().lower() or 'bounces'
        bounce_domain = f'{bounce_subdomain}.{normalized_domain}'
        dkim_public_key = payload.dkim_public_key or 'REPLACE_WITH_DKIM_PUBLIC_KEY'
        mta_hostname = payload.mta_hostname or f'smtp.{normalized_domain}'
        records = [
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=f'{selector}._domainkey.{normalized_domain}',
                value=f'v=DKIM1; k=rsa; p={dkim_public_key}',
                purpose='Authorize Email Engine managed SMTP DKIM signing for this domain.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=normalized_domain,
                value='v=spf1 mx -all',
                purpose='Authorize the domain MX path for managed SMTP staging sends.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=f'_dmarc.{normalized_domain}',
                value=f'v=DMARC1; p={payload.dmarc_policy}; rua=mailto:dmarc@{normalized_domain}',
                purpose='Publish DMARC policy and aggregate-report destination.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='MX',
                name=bounce_domain,
                value=f'10 {mta_hostname}',
                purpose='Route DSN and bounce handling traffic for the managed SMTP return path.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='MX',
                name=normalized_domain,
                value=f'10 {mta_hostname}',
                purpose='Point staging-domain mail routing at the managed SMTP host.',
                required=False,
            ),
            DomainAuthenticationDnsRecord(
                record_type='A',
                name=mta_hostname,
                value='REPLACE_WITH_MTA_IPV4',
                purpose='Map the staging MTA hostname to its server IP.',
                required=False,
            ),
        ]
        return DomainAuthenticationPlanRead(
            domain=normalized_domain,
            dkim_selector=selector,
            bounce_domain=bounce_domain,
            mta_hostname=mta_hostname,
            dmarc_policy=payload.dmarc_policy,
            dns_records=records,
            next_steps=[
                'Publish required DNS records on the staging domain.',
                'Configure Postfix DKIM signing with the matching private key and selector.',
                'Send a low-volume seed message through the managed SMTP route.',
                'Post a signed managed-SMTP feedback smoke event and confirm analytics update.',
                (
                    'Move DMARC policy from none only after alignment and bounce handling are '
                    'verified.'
                ),
            ],
        )

    def _verify_dns_record(
        self,
        expected: DomainAuthenticationDnsRecord,
    ) -> DomainAuthenticationVerificationRecord:
        try:
            observed = self.dns_resolver.lookup(expected.record_type, expected.name)
        except DnsLookupUnavailable as exc:
            return DomainAuthenticationVerificationRecord(
                record_type=expected.record_type,
                name=expected.name,
                expected_value=expected.value,
                observed_values=[],
                status='unchecked',
                message=str(exc) or 'DNS lookup unavailable',
                required=expected.required,
            )
        normalized_expected = self._normalize_dns_value(expected.value)
        observed_normalized = [self._normalize_dns_value(value) for value in observed]
        verified = normalized_expected in observed_normalized
        return DomainAuthenticationVerificationRecord(
            record_type=expected.record_type,
            name=expected.name,
            expected_value=expected.value,
            observed_values=observed,
            status='verified' if verified else 'mismatch',
            message='Record matches expected value' if verified else 'Expected value not found',
            required=expected.required,
        )

    def _normalize_dns_value(self, value: str) -> str:
        return ' '.join(value.replace('"', '').split()).lower()

    def _route_ip_pool(self, route: DeliveryRoute | None) -> str | None:
        if not route or not isinstance(route.config, dict):
            return None
        value = route.config.get('ip_pool') or route.config.get('ip_pool_name')
        return str(value) if value else None

    def _route_ip_addresses(self, route: DeliveryRoute | None) -> list[str]:
        if not route or not isinstance(route.config, dict):
            return []
        values = self._list_from_value(route.config.get('ip_addresses'))
        if values:
            return values
        single = route.config.get('ip_address')
        return [str(single)] if single else []

    def _route_list(self, route: DeliveryRoute | None, key: str) -> list[str]:
        if not route or not isinstance(route.config, dict):
            return []
        return self._list_from_value(route.config.get(key))

    def _metadata_string(self, metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        return str(value) if value else None

    def _metadata_int(self, metadata: dict[str, object], key: str) -> int | None:
        value = metadata.get(key)
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _metadata_list(self, metadata: dict[str, object], key: str) -> list[str]:
        return self._list_from_value(metadata.get(key))

    def _list_from_value(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, tuple):
            return [str(item) for item in value if item]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _clean_list(self, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = str(value).strip().lower()
            if item and item not in seen:
                cleaned.append(item)
                seen.add(item)
        return cleaned

    def _scan_blocklist_zone(self, ip_address: str, zone: str) -> DomainBlocklistScanRecord:
        query = self._blocklist_query(ip_address, zone)
        if not query:
            return DomainBlocklistScanRecord(
                ip_address=ip_address,
                zone=zone,
                query='',
                observed_values=[],
                status='invalid',
                message='Only IPv4 blocklist lookups are currently supported.',
            )
        try:
            observed_values = self.dns_resolver.lookup('A', query)
        except DnsLookupUnavailable as exc:
            return DomainBlocklistScanRecord(
                ip_address=ip_address,
                zone=zone,
                query=query,
                observed_values=[],
                status='unchecked',
                message=str(exc) or 'DNS lookup unavailable.',
            )
        if observed_values:
            return DomainBlocklistScanRecord(
                ip_address=ip_address,
                zone=zone,
                query=query,
                observed_values=observed_values,
                status='listed',
                message='Blocklist returned one or more records.',
            )
        return DomainBlocklistScanRecord(
            ip_address=ip_address,
            zone=zone,
            query=query,
            observed_values=[],
            status='clear',
            message='No blocklist record returned.',
        )

    def _blocklist_query(self, ip_address: str, zone: str) -> str | None:
        parts = ip_address.split('.')
        if len(parts) != 4:
            return None
        for part in parts:
            if not part.isdigit() or int(part) > 255:
                return None
        return f'{".".join(reversed(parts))}.{zone.strip(".")}'

    def _blocklist_scan_status(
        self,
        records: list[DomainBlocklistScanRecord],
        hits: list[str],
    ) -> str:
        if hits:
            return 'listed'
        if records and all(record.status == 'clear' for record in records):
            return 'clear'
        return 'unknown'

    def _blocklist_status(
        self,
        *,
        blocklist_hits: list[str],
        blocklist_checked_at: str | None,
        ip_addresses: list[str],
    ) -> str:
        if blocklist_hits:
            return 'listed'
        if blocklist_checked_at and ip_addresses:
            return 'clear'
        return 'unknown'

    def _warmup_progression_decision(
        self,
        *,
        payload: DomainWarmupProgressionRequest,
        metadata: dict[str, object],
        sent_count: int,
        bounce_rate: float,
        complaint_rate: float,
    ) -> tuple[str, str, str]:
        if self._metadata_list(metadata, 'blocklist_hits'):
            return 'hold', 'hold', 'Blocklist hits must be remediated before warmup advances.'
        if complaint_rate >= payload.max_complaint_rate:
            return 'hold', 'hold', 'Complaint rate exceeds warmup progression threshold.'
        if bounce_rate >= payload.max_bounce_rate:
            return 'hold', 'hold', 'Bounce rate exceeds warmup progression threshold.'
        if sent_count < payload.min_sent_count:
            return 'wait', 'active', 'Not enough sent volume to evaluate warmup advancement.'
        if not payload.advance:
            return 'keep', 'active', 'Warmup health is acceptable; advancement was not requested.'
        return 'advance', 'active', 'Warmup health is acceptable; advanced to next stage.'

    def _next_warmup_daily_limit(self, previous_daily_limit: int | None) -> int:
        if previous_daily_limit is None:
            return 100
        return max(previous_daily_limit + 1, previous_daily_limit * 2)

    def _warmup_status(
        self,
        *,
        policy: DomainDeliveryPolicy,
        send_record_count: int,
        bounce_rate: float,
        complaint_rate: float,
    ) -> str:
        if complaint_rate >= 0.001 or bounce_rate >= 0.05:
            return 'hold'
        if not policy.warmup_stage:
            return 'unset'
        if send_record_count == 0:
            return 'ready_for_seed'
        if bounce_rate >= 0.02:
            return 'watch'
        return 'active'

    def _append_compliance_audit(
        self,
        metadata: dict[str, object],
        entry: dict[str, object],
    ) -> list[object]:
        existing = metadata.get('compliance_audit_log')
        entries = list(existing) if isinstance(existing, list) else []
        entries.append(entry)
        return entries[-50:]

    def _append_warmup_audit(
        self,
        metadata: dict[str, object],
        entry: dict[str, object],
    ) -> list[object]:
        existing = metadata.get('warmup_audit_log')
        entries = list(existing) if isinstance(existing, list) else []
        entries.append(entry)
        return entries[-50:]

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _throttle_status(self, policy: DomainDeliveryPolicy) -> str:
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return 'paused'
        if policy.max_per_minute or policy.max_concurrent:
            return 'limited'
        return 'unlimited'

    def _reputation_status(
        self,
        bounce_rate: float,
        complaint_rate: float,
        authentication_verified: bool,
        blocklist_hits: list[str] | None = None,
    ) -> str:
        if blocklist_hits:
            return 'risk'
        if complaint_rate >= 0.001 or bounce_rate >= 0.05:
            return 'risk'
        if not authentication_verified:
            return 'pending_authentication'
        if bounce_rate >= 0.02:
            return 'watch'
        return 'healthy'

    def _reputation_recommendations(
        self,
        *,
        policy: DomainDeliveryPolicy,
        authentication_verified: bool,
        reputation_status: str,
        send_record_count: int,
        bounce_rate: float,
        complaint_rate: float,
        ip_pool: str | None,
        ip_addresses: list[str],
        blocklist_status: str,
        blocklist_hits: list[str],
        warmup_status: str,
        compliance_active: bool = False,
    ) -> list[str]:
        recommendations: list[str] = []
        if compliance_active:
            recommendations.append(
                'Resolve or release the compliance hold before managed-SMTP sending resumes.'
            )
        if not authentication_verified:
            recommendations.append('Verify DKIM, SPF, DMARC, and bounce-domain DNS before scaling.')
        if not ip_pool:
            recommendations.append('Assign an IP pool before production managed-SMTP sends.')
        if not ip_addresses:
            recommendations.append('Attach sending IP addresses before blocklist preflight.')
        if blocklist_status == 'listed':
            recommendations.append(
                'Pause managed-SMTP scaling until listed IPs or domains are remediated.'
            )
        elif blocklist_status == 'unknown':
            recommendations.append('Run blocklist checks for assigned IPs before production sends.')
        if not policy.warmup_stage:
            recommendations.append('Set a warmup stage for this sending domain.')
        if warmup_status == 'hold':
            recommendations.append(
                'Hold warmup progression until bounce and complaint rates recover.'
            )
        elif warmup_status == 'ready_for_seed':
            recommendations.append(
                'Run a low-volume seed test before moving this warmup stage forward.'
            )
        if not policy.max_per_minute and not policy.max_concurrent:
            recommendations.append('Set throttle limits before staging or production sends.')
        if reputation_status == 'risk':
            recommendations.append(
                'Pause or reduce volume until bounce and complaint causes are reviewed.'
            )
        elif bounce_rate >= 0.02:
            recommendations.append('Keep this domain in warmup watch until bounce rate improves.')
        if complaint_rate > 0:
            recommendations.append('Review complaint suppressions and audience consent sources.')
        if send_record_count == 0:
            recommendations.append('Run a low-volume seed test after DNS and DKIM are verified.')
        return recommendations

    def _domain_for_record(self, record: EmailSendRecord) -> str | None:
        if '@' not in record.to_email:
            return None
        return self._normalized_domain(record.to_email)

    @staticmethod
    def _normalized_domain(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if '@' in normalized:
            normalized = normalized.rsplit('@', 1)[-1]
        return normalized or None

    def _recent_domain_attempt_count(self, domain: str, seconds: int) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        return self.db.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .join(EmailSendRecord, DeliveryAttempt.send_record_id == EmailSendRecord.id)
            .where(func.lower(EmailSendRecord.to_email).like(f'%@{domain}'))
            .where(DeliveryAttempt.started_at >= cutoff)
            .where(DeliveryAttempt.status.in_(['submitting', 'submitted']))
        ) or 0

    def managed_smtp_identity_for_record(
        self,
        record: EmailSendRecord,
        sender_domain: str | None = None,
    ) -> ManagedSmtpIdentity | None:
        domain = self._normalized_domain(sender_domain) or self._domain_for_record(record)
        if not domain:
            return None
        policy = self._domain_policy(domain)
        if not policy or not policy.route_id:
            return None
        route = self.db.get(DeliveryRoute, policy.route_id)
        if not route or route.route_type != DeliveryRouteType.managed_smtp:
            return None
        metadata = policy.metadata_json or {}
        authentication = metadata.get('domain_authentication')
        bounce_domain = (
            str(authentication.get('bounce_domain'))
            if isinstance(authentication, dict) and authentication.get('bounce_domain')
            else None
        )
        dkim_key = metadata.get('dkim_key')
        dkim_selector = (
            str(dkim_key.get('selector'))
            if isinstance(dkim_key, dict) and dkim_key.get('selector')
            else None
        )
        dkim_key_ref = (
            str(dkim_key.get('key_ref'))
            if isinstance(dkim_key, dict) and dkim_key.get('key_ref')
            else None
        )
        envelope_from = self._managed_smtp_envelope_from(record, bounce_domain)
        return ManagedSmtpIdentity(
            domain=domain,
            bounce_domain=bounce_domain,
            envelope_from=envelope_from,
            dkim_selector=dkim_selector,
            dkim_key_ref=dkim_key_ref,
            dkim_signing_ready=bool(dkim_selector and dkim_key_ref),
        )

    def _managed_smtp_envelope_from(
        self,
        record: EmailSendRecord,
        bounce_domain: str | None,
    ) -> str | None:
        if not bounce_domain:
            return None
        return f'bounces+{record.id}@{bounce_domain.lower()}'

    def _active_domain_attempt_count(self, domain: str) -> int:
        return self.db.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .join(EmailSendRecord, DeliveryAttempt.send_record_id == EmailSendRecord.id)
            .where(func.lower(EmailSendRecord.to_email).like(f'%@{domain}'))
            .where(DeliveryAttempt.status == 'submitting')
        ) or 0
