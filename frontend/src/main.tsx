import { StrictMode, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Metric = {
  label: string;
  value: string;
  change: string;
  tone?: 'good' | 'warn';
};

type Insight = {
  title: string;
  detail: string;
  action: string;
  tone?: 'good' | 'warn';
};

type OperationNotice = {
  label: string;
  message: string;
  tone?: 'working' | 'success' | 'warn';
};

type Campaign = {
  name: string;
  status: string;
  sent: string;
  openRate: string;
  clickRate: string;
  failures: string;
};

type CountRow = {
  name: string;
  count: number;
};

type AnalyticsOverview = {
  campaign_count: number;
  contact_count: number;
  send_job_count: number;
  send_record_count: number;
  event_count: number;
  status_counts: CountRow[];
  event_counts: CountRow[];
  recent_events: unknown[];
};

type CampaignPerformance = {
  campaign_id: string;
  name: string;
  status: string;
  requested_count: number;
  sent_count: number;
  failed_count: number;
  opened_count: number;
  clicked_count: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
};

type CampaignAnalytics = {
  campaign_id: string;
  requested_count: number;
  queued_count: number;
  sent_count: number;
  failed_count: number;
  suppressed_count: number;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  bounced_count: number;
  complained_count: number;
  unsubscribed_count: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  status_counts: CountRow[];
  event_counts: CountRow[];
};

type CampaignWorkflowStatus = {
  campaign: CampaignRead;
  template: TemplateRead | null;
  validation: { ok: boolean; requested_count: number; errors: string[]; warnings: string[] };
  analytics: CampaignAnalytics | null;
  latest_send_job: CampaignSendJobRead | null;
  latest_send_record: EmailSendRecordRead | null;
};

type CampaignTimelinePoint = {
  date: string;
  sent_count: number;
  opened_count: number;
  clicked_count: number;
  failed_count: number;
  open_rate: number;
  click_rate: number;
};

type DomainDeliverability = {
  domain: string;
  provider: string | null;
  send_record_count: number;
  sent_count: number;
  failed_count: number;
  opened_count: number;
  clicked_count: number;
  bounced_count: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
};

type CampaignRead = {
  id: string;
  name: string;
  status: string;
  template_id: string;
  audience_query: Record<string, unknown>;
  scheduled_at: string | null;
};

type CampaignSendJobRead = {
  id: string;
  campaign_id: string;
  audience_snapshot_id: string | null;
  status: string;
  requested_count: number;
  queued_count: number;
  suppressed_count: number;
  metadata_json: Record<string, unknown>;
};

type CampaignSendJobProgress = {
  send_job_id: string;
  campaign_id: string;
  status: string;
  requested_count: number;
  queued_count: number;
  sending_count: number;
  sent_count: number;
  failed_count: number;
  suppressed_count: number;
  skipped_count: number;
  processed_count: number;
  remaining_count: number;
  active_count: number;
  percent_complete: number;
};

type EmailSendRecordRead = {
  id: string;
  campaign_id: string;
  send_job_id: string | null;
  contact_id: string;
  template_id: string;
  status: string;
  to_email: string;
  variables: Record<string, unknown>;
  provider: string | null;
  provider_message_id: string | null;
  error_message: string | null;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at: string | null;
};

type DeliveryRun = {
  claimed_count: number;
  sent_count: number;
  failed_count: number;
  processed_record_ids: string[];
};

type SuppressionRead = {
  id: string;
  email: string;
  contact_id: string | null;
  reason: 'hard_bounce' | 'spam_complaint' | 'unsubscribe' | 'manual';
  source: string;
  provider_message_id: string | null;
  metadata_json: Record<string, unknown>;
};

type DataSourceRead = {
  id: string;
  name: string;
  source_type: 'postgres' | 'mysql' | 'snowflake' | 'bigquery' | 'rest_api' | 'csv' | 'manual';
  status: 'draft' | 'active' | 'paused';
  config: Record<string, unknown>;
  secret_ref: string | null;
};

type DataSourceMappingRead = {
  id: string;
  data_source_id: string;
  name: string;
  object_type: string;
  mapping: Record<string, unknown>;
  extraction_plan: Record<string, unknown>;
};

type DataSourceImportJobRead = {
  id: string;
  data_source_id: string;
  mapping_id: string;
  status: 'completed' | 'failed' | 'dry_run';
  object_type: string;
  received_count: number;
  imported_count: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  errors: unknown[];
  metadata_json: Record<string, unknown>;
  created_at: string;
};

type DataSourceValidationRead = {
  data_source_id: string;
  source_type: DataSourceRead['source_type'];
  ok: boolean;
  checks: string[];
  errors: string[];
};

type DataSourceSchemaRead = {
  data_source_id: string;
  source_type: DataSourceRead['source_type'];
  object_types: string[];
  fields: Array<{ name: string; field_type: string; sample_values: unknown[] }>;
  sample_rows: Record<string, unknown>[];
};

type AudienceRead = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  rule_tree: Record<string, unknown>;
  estimated_count: number;
};

type ContactRead = {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  source: string | null;
  attributes: Record<string, unknown>;
  is_unsubscribed: boolean;
};

type ContactMetadata = {
  total: number;
  scanned_count: number;
  fields: string[];
  attribute_keys: string[];
  sources: Array<{ source: string; count: number }>;
  sample_contacts: ContactRead[];
};

type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

type AIAnalyticsAnalysis = {
  recommendations: Array<{
    code: string;
    priority: string;
    title: string;
    detail: string;
    suggested_action: string;
  }>;
};

type AITemplateDraft = {
  subject: string;
  html_body: string;
  css_body: string | null;
  text_body: string | null;
  sample_variables: Record<string, unknown>;
  notes: string[];
  changed_fields?: string[];
  change_summary?: string[];
  provider: string;
  model: string;
};

type AITemplateRecommendation = {
  code: string;
  category: string;
  priority: string;
  title: string;
  detail: string;
  suggested_instruction: string;
  confidence: number;
};

type AIWorkflowRecommendation = {
  area: string;
  code: string;
  category: string;
  priority: string;
  title: string;
  detail: string;
  suggested_action: string;
  confidence: number;
};

type AIWorkflowAnalysis = {
  summary?: string[];
  recommendations?: Array<{
    code: string;
    category: string;
    priority: string;
    title: string;
    detail: string;
    suggested_action?: string;
    suggested_instruction?: string;
    confidence: number;
  }>;
};

type SystemDiagnostics = {
  ok: boolean;
  environment: string;
  public_base_url: string;
  schema: {
    ok: boolean;
    current_revision: string | null;
    expected_revision: string | null;
    needs_migration: boolean;
  };
  email_provider: {
    provider: string;
    default_from_email: string;
    sendgrid_configured: boolean;
    smtp_configured: boolean;
  };
  ai: {
    provider: string;
    model: string;
    openai_configured: boolean;
  };
  entity_counts: Record<string, number>;
  database_tables: string[];
  database_table_columns: Record<string, Array<{
    name: string;
    type: string;
    nullable: boolean;
    primary_key: boolean;
  }>>;
  errors: string[];
};

type DashboardState = {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  campaignItems: CampaignRead[];
  sendJobs: CampaignSendJobRead[];
  sendRecords: EmailSendRecordRead[];
  suppressions: SuppressionRead[];
  dataSources: DataSourceRead[];
  dataMappings: DataSourceMappingRead[];
  importJobs: DataSourceImportJobRead[];
  contacts: ContactRead[];
  contactMeta: ContactMetadata | null;
  audiences: AudiencePerformance[];
  audienceItems: AudienceRead[];
  templates: TemplateRead[];
  journeys: JourneyPerformance[];
  journeyItems: JourneyRead[];
  journeyEnrollments: JourneyEnrollmentRead[];
  journeyExecutions: JourneyStepExecutionRead[];
  diagnostics: SystemDiagnostics | null;
  aiInsights: Insight[];
  loading: boolean;
  error: string | null;
};

type PageKey =
  | 'overview'
  | 'campaigns'
  | 'automations'
  | 'delivery'
  | 'compliance'
  | 'data'
  | 'contacts'
  | 'audience'
  | 'templates'
  | 'ai-studio'
  | 'analytics'
  | 'integrations'
  | 'docs'
  | 'settings';

type NavItem = {
  label: string;
  key: PageKey;
  href: string;
};

type AudiencePerformance = {
  audience_id: string;
  name: string;
  status: string;
  estimated_count: number;
  sent_count: number;
  opened_count: number;
  clicked_count: number;
  open_rate: number;
  click_rate: number;
};

type TemplateRead = {
  id: string;
  name: string;
  subject: string;
  category: string | null;
  html_body: string;
  css_body: string | null;
  text_body: string | null;
  document_json: Record<string, unknown>;
};

type TemplateVariable = {
  name: string;
  required: boolean;
  native: boolean;
  sources: string[];
  sample_value: unknown;
};

type JourneyStepRead = {
  id: string;
  journey_id: string;
  name: string;
  step_type: string;
  position: number;
  config: Record<string, unknown>;
};

type JourneyRead = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  entry_rule_tree: Record<string, unknown>;
  exit_rule_tree: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  steps: JourneyStepRead[];
};

type JourneyEnrollmentRead = {
  id: string;
  journey_id: string;
  contact_id: string;
  current_step_id: string | null;
  status: 'active' | 'completed' | 'exited' | 'paused' | 'failed';
  variables: Record<string, unknown>;
  due_at: string | null;
  entered_at: string;
  exited_at: string | null;
  last_error: string | null;
};

type JourneyStepExecutionRead = {
  id: string;
  enrollment_id: string;
  journey_id: string;
  step_id: string;
  contact_id: string;
  status: 'completed' | 'failed' | 'skipped';
  send_record_id: string | null;
  metadata_json: Record<string, unknown>;
  error_message: string | null;
  executed_at: string;
};

type JourneyPerformance = {
  journey_id: string;
  name: string;
  status: string;
  enrollment_count: number;
  active_count: number;
  completed_count: number;
  failed_count: number;
  step_failed_count: number;
  queued_send_count: number;
};

const navItems: NavItem[] = [
  { label: 'Overview', key: 'overview', href: '#overview' },
  { label: 'Campaigns', key: 'campaigns', href: '#campaigns' },
  { label: 'Automations', key: 'automations', href: '#automations' },
  { label: 'Delivery', key: 'delivery', href: '#delivery' },
  { label: 'Compliance', key: 'compliance', href: '#compliance' },
  { label: 'Data', key: 'data', href: '#data' },
  { label: 'Contacts', key: 'contacts', href: '#contacts' },
  { label: 'Audience', key: 'audience', href: '#audience' },
  { label: 'Templates', key: 'templates', href: '#templates' },
  { label: 'AI Studio', key: 'ai-studio', href: '#ai-studio' },
  { label: 'Analytics', key: 'analytics', href: '#analytics' },
  { label: 'Integrations', key: 'integrations', href: '#integrations' },
  { label: 'Docs', key: 'docs', href: '#docs' },
  { label: 'Settings', key: 'settings', href: '#settings' },
];

const fallbackMetrics: Metric[] = [
  { label: 'Total sends', value: '128,540', change: '+18.4%' },
  { label: 'Open rate', value: '42.6%', change: '+7.3%' },
  { label: 'Click rate', value: '8.7%', change: '+3.6%' },
  { label: 'Contacts', value: '3,256', change: '+12.5%' },
  { label: 'Events', value: '24,780', change: '+21.6%' },
];

const fallbackInsights: Insight[] = [
  {
    title: 'Optimal send time',
    detail: 'Your audience is most active on Tuesdays at 2:00 PM.',
    action: 'Schedule next campaign',
  },
  {
    title: 'Segment at risk',
    detail: '2,340 contacts show low engagement over the last 60 days.',
    action: 'Create re-engagement journey',
    tone: 'warn',
  },
  {
    title: 'High opportunity',
    detail: 'Loyal customers are responding best to product announcements.',
    action: 'Build campaign variant',
    tone: 'good',
  },
  {
    title: 'Content idea',
    detail: 'Shorter subject lines are outperforming long promotional copy.',
    action: 'Generate subject lines',
  },
];

const fallbackCampaigns: Campaign[] = [
  {
    name: 'Spring Sale Announcement',
    status: 'Sent',
    sent: '32,450',
    openRate: '45.1%',
    clickRate: '9.1%',
    failures: '0',
  },
  {
    name: 'New Product Launch',
    status: 'Sent',
    sent: '28,124',
    openRate: '41.3%',
    clickRate: '8.3%',
    failures: '0',
  },
  {
    name: 'Weekly Newsletter',
    status: 'Sent',
    sent: '67,966',
    openRate: '42.0%',
    clickRate: '8.5%',
    failures: '0',
  },
];

const chartLines = [
  'M0,138 C40,86 64,98 94,76 C128,50 144,44 177,66 C205,84 228,46 256,36 C285,28 306,52 344,42 C373,36 396,18 430,30 C462,44 480,12 520,24',
  'M0,172 C42,142 74,154 104,128 C138,100 160,122 192,110 C224,98 238,72 274,88 C312,106 330,124 360,108 C396,90 416,72 448,92 C480,112 500,74 520,68',
  'M0,205 C52,184 78,198 112,176 C142,156 164,172 190,158 C228,134 252,150 282,136 C316,118 344,142 374,130 C414,112 448,122 520,98',
  'M0,235 C44,220 82,230 118,212 C156,194 182,206 214,192 C252,174 282,190 312,178 C348,160 388,176 424,158 C464,138 490,152 520,134',
];

function formatInt(value: number | undefined) {
  return Number(value || 0).toLocaleString();
}

function formatPct(value: number | undefined) {
  return `${Math.round(Number(value || 0) * 1000) / 10}%`;
}

function providerLabel(value: string | null | undefined) {
  if (!value) return '-';
  return value.toLowerCase() === 'sendgrid' ? 'SG' : value;
}

function countByName(rows: CountRow[] | undefined, name: string) {
  return Number((rows || []).find((row) => row.name === name)?.count || 0);
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `${path} failed`);
  }
  return data as T;
}

function metricsFromOverview(overview: AnalyticsOverview | null): Metric[] {
  if (!overview) return fallbackMetrics;
  const sent = countByName(overview.status_counts, 'sent');
  const delivered = countByName(overview.event_counts, 'delivered');
  const opens = countByName(overview.event_counts, 'opened');
  const clicks = countByName(overview.event_counts, 'clicked');
  const rateBase = Math.max(sent, delivered, 1);
  return [
    { label: 'Total sends', value: formatInt(overview.send_record_count), change: `${formatInt(sent)} sent` },
    { label: 'Open rate', value: formatPct(opens / rateBase), change: `${formatInt(opens)} opens` },
    { label: 'Click rate', value: formatPct(clicks / rateBase), change: `${formatInt(clicks)} clicks` },
    { label: 'Contacts', value: formatInt(overview.contact_count), change: `${formatInt(overview.campaign_count)} campaigns` },
    { label: 'Events', value: formatInt(overview.event_count), change: `${formatInt(overview.recent_events.length)} recent` },
  ];
}

function campaignsFromPerformance(rows: CampaignPerformance[]): Campaign[] {
  if (!rows.length) return fallbackCampaigns;
  return rows.slice(0, 5).map((row) => ({
    name: row.name,
    status: row.status,
    sent: formatInt(row.sent_count),
    openRate: formatPct(row.open_rate),
    clickRate: formatPct(row.click_rate),
    failures: formatInt(row.failed_count),
  }));
}

function insightsFromAi(data: AIAnalyticsAnalysis | null): Insight[] {
  if (!data?.recommendations?.length) return fallbackInsights;
  return data.recommendations.slice(0, 4).map((item) => ({
    title: item.title || item.code,
    detail: item.detail,
    action: item.suggested_action,
    tone: item.priority === 'high' ? 'warn' : item.priority === 'low' ? 'good' : undefined,
  }));
}

function pageFromHash(): PageKey {
  const hash = window.location.hash.replace(/^#\/?/, '');
  const root = hash.split('/')[0];
  return navItems.find((item) => item.key === root)?.key || 'overview';
}

function routeFromHash() {
  return window.location.hash.replace(/^#\/?/, '');
}

function pageTitle(page: PageKey) {
  return navItems.find((item) => item.key === page)?.label || 'Overview';
}

function pageSubtitle(page: PageKey, dashboard: DashboardState) {
  if (dashboard.loading) return 'Loading live data from Email Engine APIs...';
  if (dashboard.error) return `Live API issue: ${dashboard.error}. Showing available data.`;
  const subtitles: Record<PageKey, string> = {
    overview: 'Live overview powered by Email Engine analytics APIs.',
    campaigns: 'Create, inspect, and launch campaigns from the product workspace.',
    automations: 'Monitor journeys, enrollments, queued sends, and execution health.',
    delivery: 'Inspect send jobs, process queued messages, and manage individual send records.',
    compliance: 'Manage suppressions before campaign launch and delivery processing.',
    data: 'Configure data sources, mappings, row ingestion, and import job visibility.',
    contacts: 'Inspect contacts, attributes, source distribution, and editable profile data.',
    audience: 'Manage audiences and segmentation readiness.',
    templates: 'Create, edit, and test dynamic email templates.',
    'ai-studio': 'Use AI helpers across templates, campaigns, audiences, and analytics.',
    analytics: 'Review performance, engagement, and delivery signals.',
    integrations: 'Connect data sources, providers, and external tools.',
    docs: 'Review ESP workflow contracts and API surfaces for GUI integration.',
    settings: 'Configure account, domains, compliance, and developer surfaces.',
  };
  return subtitles[page];
}

function Icon({ label }: { label: string }) {
  return <span className="icon" aria-hidden="true">{label.slice(0, 1)}</span>;
}

function Sidebar({ activePage }: { activePage: PageKey }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="mark">E</div>
        <span>Email Engine</span>
      </div>
      <nav>
        {navItems.map((item) => (
          <a className={item.key === activePage ? 'active' : ''} href={item.href} key={item.key}>
            <Icon label={item.label} />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
      <section className="assistant-card">
        <strong>AI Assistant</strong>
        <p>Create content, find insights, and optimize performance.</p>
        <button>Ask AI</button>
      </section>
      <section className="usage-card">
        <span>Pro Plan</span>
        <strong>12,450 / 25,000 emails</strong>
        <div className="usage-track"><span /></div>
      </section>
      <div className="profile">
        <div className="avatar">DW</div>
        <div>
          <strong>David Wolfe</strong>
          <span>email-engine.app</span>
        </div>
      </div>
    </aside>
  );
}

function headerAction(page: PageKey) {
  const actions: Partial<Record<PageKey, { label: string; href: string }>> = {
    campaigns: { label: 'Create Campaign', href: '#campaigns/new' },
    automations: { label: 'Create Journey', href: '#automations/new' },
    delivery: { label: 'Process Queue', href: '#delivery' },
    compliance: { label: 'Add Suppression', href: '#compliance/new' },
    data: { label: 'Add Data Source', href: '#data/new' },
    contacts: { label: 'Create Contact', href: '#contacts/new' },
    audience: { label: 'Create Audience', href: '#audience/new' },
    templates: { label: 'Create Template', href: '#templates/new' },
    'ai-studio': { label: 'Run AI Review', href: '#ai-studio' },
  };
  return actions[page] || null;
}

function Header({ title, status, operation, activePage }: { title: string; status: string; operation: OperationNotice; activePage: PageKey }) {
  const action = headerAction(activePage);
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{status}</p>
        <div className={`global-operation ${operation.tone || 'success'}`}>
          <strong>{operation.label}</strong>
          <span>{operation.message}</span>
        </div>
      </div>
      <div className="topbar-actions">
        <button className="ghost">May 1 - May 31, 2026</button>
        {action ? (
          <button className="primary" onClick={() => { window.location.hash = action.href; }}>{action.label}</button>
        ) : null}
      </div>
    </header>
  );
}

function WorkflowRail({ activePage }: { activePage: PageKey }) {
  const workflows = [
    {
      label: 'Campaign creation',
      detail: 'Audience + template + test send',
      href: '#campaigns',
      pages: ['campaigns', 'audience', 'templates', 'contacts', 'data'] as PageKey[],
    },
    {
      label: 'Campaign optimization',
      detail: 'Analytics + AI + delivery health',
      href: '#analytics',
      pages: ['analytics', 'ai-studio', 'delivery', 'campaigns'] as PageKey[],
    },
    {
      label: 'Template development',
      detail: 'Design + variables + preview',
      href: '#templates',
      pages: ['templates', 'ai-studio'] as PageKey[],
    },
  ];
  return (
    <section className="workflow-rail" aria-label="Key workflows">
      {workflows.map((workflow) => (
        <a className={workflow.pages.includes(activePage) ? 'active' : ''} href={workflow.href} key={workflow.label}>
          <strong>{workflow.label}</strong>
          <span>{workflow.detail}</span>
        </a>
      ))}
    </section>
  );
}

function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="metric-card">
      <div>
        <span>{metric.label}</span>
        <strong>{metric.value}</strong>
      </div>
      <small className={metric.tone === 'warn' ? 'warn' : 'good'}>{metric.change}</small>
    </article>
  );
}

function PerformanceChart() {
  return (
    <section className="panel chart-panel">
      <div className="panel-head">
        <h2>Performance over time</h2>
        <a href="#analytics">Open analytics</a>
      </div>
      <div className="legend">
        <span><i className="dot purple" />Sends</span>
        <span><i className="dot blue" />Opens</span>
        <span><i className="dot green" />Clicks</span>
        <span><i className="dot amber" />Revenue</span>
      </div>
      <svg className="line-chart" viewBox="0 0 560 280" role="img" aria-label="Performance line chart">
        {[50, 100, 150, 200, 250].map((y) => (
          <line key={y} x1="0" y1={y} x2="560" y2={y} className="grid-line" />
        ))}
        {chartLines.map((line, index) => (
          <path key={line} className={`chart-line line-${index}`} d={line} />
        ))}
      </svg>
    </section>
  );
}

function InsightsPanel({ insights }: { insights: Insight[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>AI Insights</h2>
        <a href="#analytics">View all</a>
      </div>
      <div className="insights">
        {insights.map((item) => (
          <article className={`insight ${item.tone || ''}`} key={item.title}>
            <Icon label={item.title} />
            <div>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
              <button className="link-button">{item.action}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function CampaignTable({ campaigns }: { campaigns: Campaign[] }) {
  return (
    <section className="panel table-panel">
      <div className="panel-head">
        <h2>Recent campaigns</h2>
        <a href="#campaigns">Manage campaigns</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>Campaign</th>
            <th>Status</th>
            <th>Sends</th>
            <th>Open rate</th>
            <th>Click rate</th>
            <th>Failures</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((campaign) => (
            <tr key={campaign.name}>
              <td>{campaign.name}</td>
              <td><span className="pill">{campaign.status}</span></td>
              <td>{campaign.sent}</td>
              <td>{campaign.openRate}</td>
              <td>{campaign.clickRate}</td>
              <td>{campaign.failures}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function QuickCreate() {
  return (
    <section className="panel quick-create">
      <h2>Quick create</h2>
      <a href="#campaigns">Email Campaign</a>
      <a href="#automations">Automation</a>
      <a href="#audience">Segment</a>
      <a href="#templates">Template</a>
    </section>
  );
}

function OverviewPage({ dashboard, metrics, campaigns }: {
  dashboard: DashboardState;
  metrics: Metric[];
  campaigns: Campaign[];
}) {
  const queuedRecords = dashboard.sendRecords.filter((record) => record.status === 'queued').length;
  const failedRecords = dashboard.sendRecords.filter((record) => record.status === 'failed').length;
  const activeJobs = dashboard.sendJobs.filter((job) => !['completed', 'failed', 'cancelled'].includes(job.status)).length;
  const failedImports = dashboard.importJobs.filter((job) => job.status === 'failed').length;
  const importedRows = dashboard.importJobs.reduce((sum, job) => sum + Number(job.imported_count || 0), 0);
  const activeEnrollments = dashboard.journeyEnrollments.filter((enrollment) => enrollment.status === 'active').length;
  const failedExecutions = dashboard.journeyExecutions.filter((execution) => execution.status === 'failed').length;
  const attributeKeys = dashboard.contactMeta?.attribute_keys || [];
  const topSource = dashboard.contactMeta?.sources?.[0];
  const provider = dashboard.diagnostics?.email_provider.provider || 'unknown';
  const providerReady = Boolean(
    dashboard.diagnostics?.email_provider.smtp_configured ||
    dashboard.diagnostics?.email_provider.sendgrid_configured ||
    provider === 'console',
  );
  const schemaOk = Boolean(dashboard.diagnostics?.schema.ok);
  const riskItems = [
    {
      title: queuedRecords ? 'Delivery queue needs processing' : 'Delivery queue is clear',
      detail: queuedRecords ? `${formatInt(queuedRecords)} queued records are visible.` : 'No queued records in the current result set.',
      href: '#delivery',
      tone: queuedRecords ? 'warn' : 'good',
    },
    {
      title: failedRecords ? 'Failed send records visible' : 'No failed sends visible',
      detail: failedRecords ? `${formatInt(failedRecords)} records can be reviewed or requeued.` : 'No failed send records in the current result set.',
      href: '#delivery',
      tone: failedRecords ? 'warn' : 'good',
    },
    {
      title: dashboard.suppressions.length ? 'Suppressions active' : 'No suppressions visible',
      detail: `${formatInt(dashboard.suppressions.length)} suppression rows loaded for compliance review.`,
      href: '#compliance',
      tone: dashboard.suppressions.length ? 'warn' : 'good',
    },
    {
      title: failedExecutions ? 'Journey execution failures' : 'Journey executions healthy',
      detail: failedExecutions ? `${formatInt(failedExecutions)} failed executions require review.` : `${formatInt(activeEnrollments)} active enrollments visible.`,
      href: '#automations',
      tone: failedExecutions ? 'warn' : 'good',
    },
  ];

  return (
    <>
      <section className="metric-grid">
        {metrics.map((metric) => <MetricCard metric={metric} key={metric.label} />)}
      </section>
      <section className="workflow-grid full-span">
        <article className={`workflow-card ${providerReady ? '' : 'warn'}`}>
          <span>Provider</span>
          <strong>{providerLabel(provider)}</strong>
          <p>{providerReady ? 'Outbound provider path is configured for sends.' : 'Outbound provider configuration needs review before live sends.'}</p>
          <a href="#integrations">Open integrations</a>
        </article>
        <article className={`workflow-card ${schemaOk ? '' : 'warn'}`}>
          <span>System</span>
          <strong>{schemaOk ? 'Schema ready' : 'Schema review'}</strong>
          <p>{dashboard.diagnostics?.schema.current_revision || 'No schema revision reported.'}</p>
          <a href="#settings">Open diagnostics</a>
        </article>
        <article className={`workflow-card ${activeJobs || queuedRecords ? 'warn' : ''}`}>
          <span>Delivery</span>
          <strong>{formatInt(activeJobs)} active jobs</strong>
          <p>{formatInt(queuedRecords)} queued and {formatInt(failedRecords)} failed records visible.</p>
          <a href="#delivery">Open delivery</a>
        </article>
        <article className={`workflow-card ${failedImports ? 'warn' : ''}`}>
          <span>Data</span>
          <strong>{formatInt(importedRows)} imported</strong>
          <p>{formatInt(dashboard.dataSources.length)} sources, {formatInt(dashboard.dataMappings.length)} mappings, {formatInt(failedImports)} failed jobs.</p>
          <a href="#data">Open data</a>
        </article>
      </section>
      <section className="dashboard-grid">
        <section className="panel">
          <div className="panel-head"><h2>Operations Radar</h2><a href="#analytics">Reports</a></div>
          <div className="insights">
            {riskItems.map((item) => (
              <article className={`insight ${item.tone === 'warn' ? 'warn' : 'good'}`} key={item.title}>
                <Icon label={item.title} />
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  <a className="link-button" href={item.href}>Review</a>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Audience Readiness</h2><a href="#contacts">Contacts</a></div>
          <p className="large-number">{formatInt(dashboard.contactMeta?.total || dashboard.contacts.length)}</p>
          <span className="muted">contacts across {formatInt(dashboard.contactMeta?.sources.length || 0)} sources</span>
          <div className="module-links">
            <a href="#contacts">{formatInt(attributeKeys.length)} attribute keys</a>
            <a href="#audience">{formatInt(dashboard.audienceItems.length)} audiences</a>
            <a href="#data">{topSource ? `${topSource.source}: ${formatInt(topSource.count)}` : 'No top source'}</a>
          </div>
        </section>
      </section>
      <section className="lower-grid">
        <CampaignTable campaigns={campaigns} />
        <section className="panel quick-create">
          <h2>Run Workflow</h2>
          <a href="#data">Import contacts</a>
          <a href="#templates">Create template</a>
          <a href="#audience">Build audience</a>
          <a href="#campaigns">Launch campaign</a>
          <a href="#automations">Enroll journey</a>
          <a href="#analytics">Review reports</a>
        </section>
      </section>
    </>
  );
}

function EmptyState({ title, detail, actionHref, actionLabel }: {
  title: string;
  detail: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{detail}</p>
      {actionHref && actionLabel ? <a href={actionHref}>{actionLabel}</a> : null}
    </div>
  );
}

function CampaignsPage({ campaigns, campaignItems, templates, audiences, route, onRefresh, onOperation }: {
  campaigns: CampaignPerformance[];
  campaignItems: CampaignRead[];
  templates: TemplateRead[];
  audiences: AudienceRead[];
  route: string;
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const routeParts = route.split('/');
  const routeCampaignId = routeParts[0] === 'campaigns' && routeParts[1] && routeParts[1] !== 'new'
    ? routeParts[1]
    : '';
  const isDetailPage = routeParts[0] === 'campaigns' && Boolean(routeParts[1]);
  const isNewCampaign = routeParts[0] === 'campaigns' && routeParts[1] === 'new';
  const [campaignName, setCampaignName] = useState('ESP Test Campaign');
  const [templateId, setTemplateId] = useState('');
  const [audienceId, setAudienceId] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [testEmail, setTestEmail] = useState('');
  const [variablesJson, setVariablesJson] = useState('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
  const [operationStatus, setOperationStatus] = useState('Ready to create a draft campaign.');
  const [operationBusy, setOperationBusy] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [workflowStatus, setWorkflowStatus] = useState<CampaignWorkflowStatus | null>(null);

  useEffect(() => {
    if (!templateId && templates.length) setTemplateId(templates[0].id);
    if (!audienceId && audiences.length) setAudienceId(audiences[0].id);
    if (routeCampaignId && selectedCampaignId !== routeCampaignId) setSelectedCampaignId(routeCampaignId);
    if (isNewCampaign && selectedCampaignId) setSelectedCampaignId('');
  }, [audienceId, audiences, isNewCampaign, routeCampaignId, selectedCampaignId, templateId, templates]);

  const totalRequested = campaigns.reduce((sum, item) => sum + Number(item.requested_count || 0), 0);
  const totalSent = campaigns.reduce((sum, item) => sum + Number(item.sent_count || 0), 0);
  const totalFailures = campaigns.reduce((sum, item) => sum + Number(item.failed_count || 0), 0);
  const selectedAudience = audiences.find((item) => item.id === audienceId);
  const selectedCampaign = campaignItems.find((item) => item.id === selectedCampaignId);
  const selectedTemplate = templates.find((item) => item.id === templateId);
  const campaignPerformanceById = new Map(campaigns.map((campaign) => [campaign.campaign_id, campaign]));
  const selectedCampaignPerformance = selectedCampaignId ? campaignPerformanceById.get(selectedCampaignId) : null;

  useEffect(() => {
    if (!selectedCampaign) return;
    setCampaignName(selectedCampaign.name);
    if (selectedCampaign.template_id) setTemplateId(selectedCampaign.template_id);
  }, [selectedCampaign]);
  const workflowSteps = [
    { label: 'Setup', detail: selectedCampaign ? selectedCampaign.name : 'Create or select a draft', ready: Boolean(selectedCampaignId) },
    { label: 'Content', detail: selectedTemplate ? selectedTemplate.name : 'Choose a template', ready: Boolean(templateId) },
    { label: 'Audience', detail: selectedAudience ? `${selectedAudience.name} (${formatInt(selectedAudience.estimated_count)})` : 'Choose an audience', ready: Boolean(audienceId) },
    { label: 'Test', detail: testEmail.trim() ? testEmail.trim() : 'Enter a test recipient', ready: Boolean(testEmail.trim()) },
    { label: 'Launch', detail: 'Dry-run before production send', ready: Boolean(selectedCampaignId && templateId && audienceId) },
  ];
  const readinessCards = [
    {
      label: 'Draft',
      ready: Boolean(selectedCampaignId),
      detail: selectedCampaign ? `${selectedCampaign.status} campaign selected.` : 'Save a draft before preview, test send, or launch.',
    },
    {
      label: 'Template',
      ready: Boolean(selectedTemplate),
      detail: selectedTemplate ? selectedTemplate.subject : 'Choose the email template for this campaign.',
    },
    {
      label: 'Audience',
      ready: Boolean(selectedAudience),
      detail: selectedAudience ? `${formatInt(selectedAudience.estimated_count)} estimated contacts.` : 'Choose a saved audience before launch.',
    },
    {
      label: 'Validation',
      ready: Boolean(workflowStatus?.validation?.ok),
      detail: workflowStatus
        ? workflowStatus.validation.ok
          ? `${formatInt(workflowStatus.validation.requested_count)} contacts validated.`
          : `${formatInt((workflowStatus.validation.errors || []).length)} errors / ${formatInt((workflowStatus.validation.warnings || []).length)} warnings.`
        : 'Run readiness check before sending.',
    },
    {
      label: 'Delivery',
      ready: Boolean(workflowStatus?.latest_send_job || selectedCampaignPerformance?.sent_count),
      detail: workflowStatus?.latest_send_job
        ? `${workflowStatus.latest_send_job.status}: ${formatInt(workflowStatus.latest_send_job.queued_count)} queued.`
        : selectedCampaignPerformance
          ? `${formatInt(selectedCampaignPerformance.sent_count)} sent so far.`
          : 'No delivery job visible yet.',
    },
  ];

  function parsedVariables() {
    try {
      const parsed = JSON.parse(variablesJson || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Variables must be a JSON object.');
      }
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid variables JSON.');
    }
  }

  async function runOperation(label: string, operation: () => Promise<string>) {
    setOperationBusy(true);
    setOperationStatus(`${label}...`);
    onOperation({ label: 'Campaign workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setOperationStatus(message);
      onOperation({ label: 'Campaign workflow', message, tone: 'success' });
      await onRefresh();
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setOperationStatus(message);
      onOperation({ label: 'Campaign workflow', message, tone: 'warn' });
    } finally {
      setOperationBusy(false);
    }
  }

  async function createDraftCampaign() {
    await runOperation(selectedCampaignId ? 'Saving campaign setup' : 'Creating draft campaign', async () => {
      if (!templateId) throw new Error('Select a template.');
      const payload = {
        name: campaignName.trim() || `ESP Campaign ${new Date().toISOString()}`,
        template_id: templateId,
        audience_query: selectedAudience?.rule_tree || {},
      };
      const saved = await fetchJson<CampaignRead>(selectedCampaignId ? `/api/v1/campaigns/${selectedCampaignId}` : '/api/v1/campaigns', {
        method: selectedCampaignId ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      });
      setSelectedCampaignId(saved.id);
      window.location.hash = `#campaigns/${saved.id}`;
      return `${selectedCampaignId ? 'Saved campaign' : 'Created draft campaign'}: ${saved.name}`;
    });
  }

  async function validateCampaign() {
    await runOperation('Validating campaign', async () => {
      const campaignId = selectedCampaignId || selectedCampaign?.id;
      if (!campaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<{ ok: boolean; requested_count: number; errors: string[]; warnings: string[] }>(`/api/v1/campaigns/${campaignId}/validate`, {
        method: 'POST',
        body: JSON.stringify({ audience_id: audienceId || null, variables: parsedVariables(), dry_run: true }),
      });
      const issueCount = (data.errors?.length || 0) + (data.warnings?.length || 0);
      return data.ok
        ? `Validation passed. ${formatInt(data.requested_count)} contacts matched.`
        : `Validation found ${formatInt(issueCount)} issue(s): ${(data.errors || data.warnings || []).join('; ')}`;
    });
  }

  async function loadCampaignWorkflowStatus() {
    await runOperation('Loading campaign readiness', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<CampaignWorkflowStatus>(`/api/v1/campaigns/${selectedCampaignId}/workflow-status`);
      setWorkflowStatus(data);
      return data.validation.ok
        ? `Ready check passed for ${data.campaign.name}.`
        : `Ready check found ${formatInt((data.validation.errors || []).length)} error(s) and ${formatInt((data.validation.warnings || []).length)} warning(s).`;
    });
  }

  async function previewTestEmail() {
    await runOperation('Rendering test preview', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<{ subject: string; html_body: string }>(`/api/v1/campaigns/${selectedCampaignId}/test-preview`, {
        method: 'POST',
        body: JSON.stringify({ variables: parsedVariables() }),
      });
      setPreviewHtml(data.html_body || '');
      return `Rendered preview: ${data.subject}`;
    });
  }

  async function sendTestEmail() {
    await runOperation('Sending test email', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      if (!testEmail.trim()) throw new Error('Enter a test recipient email.');
      const data = await fetchJson<{ status: string; provider_message_id?: string }>(`/api/v1/campaigns/${selectedCampaignId}/test-send`, {
        method: 'POST',
        body: JSON.stringify({ to_email: testEmail.trim(), variables: parsedVariables() }),
      });
      return `Test send ${data.status}${data.provider_message_id ? ` (${data.provider_message_id})` : ''}.`;
    });
  }

  async function dryRunLaunch() {
    await runOperation('Running dry-run launch', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<{ requested_count: number; queued_count: number; suppressed_count: number }>(`/api/v1/campaigns/${selectedCampaignId}/launch`, {
        method: 'POST',
        body: JSON.stringify({ audience_id: audienceId || null, variables: parsedVariables(), dry_run: true }),
      });
      return `Dry run complete. ${formatInt(data.requested_count)} requested, ${formatInt(data.queued_count)} queued, ${formatInt(data.suppressed_count)} suppressed.`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid entity-list-page">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Campaigns', value: formatInt(campaignItems.length), change: 'live rows' }} />
          <MetricCard metric={{ label: 'Requested', value: formatInt(totalRequested), change: 'targeted sends' }} />
          <MetricCard metric={{ label: 'Sent', value: formatInt(totalSent), change: 'processed sends' }} />
          <MetricCard metric={{ label: 'Failures', value: formatInt(totalFailures), change: 'delivery issues', tone: totalFailures ? 'warn' : 'good' }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Campaigns</h2>
              <span className="muted">Open one campaign to edit setup, test content, and manage launch readiness.</span>
            </div>
            <div className="button-row">
              <a href="#analytics">View reports</a>
              <a href="#campaigns/new">New campaign</a>
            </div>
          </div>
          {campaignItems.length ? (
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Status</th>
                  <th>Requested</th>
                  <th>Sent</th>
                  <th>Open rate</th>
                  <th>Click rate</th>
                  <th>Failures</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {campaignItems.map((campaign) => {
                  const performance = campaignPerformanceById.get(campaign.id);
                  return (
                    <tr
                      className={`selectable-row ${campaign.id === selectedCampaignId ? 'selected-row' : ''}`}
                      key={campaign.id}
                      onClick={() => setSelectedCampaignId(campaign.id)}
                    >
                      <td>{campaign.name}</td>
                      <td><span className="pill">{campaign.status}</span></td>
                      <td>{formatInt(performance?.requested_count)}</td>
                      <td>{formatInt(performance?.sent_count)}</td>
                      <td>{performance ? formatPct(performance.open_rate) : '-'}</td>
                      <td>{performance ? formatPct(performance.click_rate) : '-'}</td>
                      <td>{formatInt(performance?.failed_count)}</td>
                      <td>
                        <a
                          className="link-button"
                          href={`#campaigns/${campaign.id}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          Open
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No campaigns yet" detail="Create a campaign, then it will appear in this list." actionHref="#campaigns/new" actionLabel="Create campaign" />
          )}
        </section>
        {selectedCampaign ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedCampaign.name}</h2>
                <span className="muted">Selected campaign summary</span>
              </div>
              <a href={`#campaigns/${selectedCampaign.id}`}>Open campaign workspace</a>
            </div>
            <div className="summary-grid">
              <div><span>Status</span><strong>{selectedCampaign.status}</strong></div>
              <div><span>Template</span><strong>{templates.find((template) => template.id === selectedCampaign.template_id)?.name || selectedCampaign.template_id.slice(0, 8)}</strong></div>
              <div><span>Requested</span><strong>{formatInt(selectedCampaignPerformance?.requested_count)}</strong></div>
              <div><span>Sent</span><strong>{formatInt(selectedCampaignPerformance?.sent_count)}</strong></div>
              <div><span>Open rate</span><strong>{selectedCampaignPerformance ? formatPct(selectedCampaignPerformance.open_rate) : '-'}</strong></div>
              <div><span>Click rate</span><strong>{selectedCampaignPerformance ? formatPct(selectedCampaignPerformance.click_rate) : '-'}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      <section className="campaign-flow full-span">
        {workflowSteps.map((step, index) => (
          <article className={step.ready ? 'ready' : ''} key={step.label}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <p>{step.detail}</p>
            </div>
          </article>
        ))}
      </section>
      <section className="workflow-grid full-span">
        {readinessCards.map((item) => (
          <article className={`workflow-card ${item.ready ? '' : 'warn'}`} key={item.label}>
            <span>{item.ready ? 'Ready' : 'Needs attention'}</span>
            <strong>{item.label}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>
      {selectedCampaign ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedCampaign.name}</h2>
              <span className="muted">Campaign workspace summary</span>
            </div>
            <a href="#delivery">Open delivery</a>
          </div>
          <div className="summary-grid">
            <div><span>Status</span><strong>{selectedCampaign.status}</strong></div>
            <div><span>Template</span><strong>{selectedTemplate?.name || selectedCampaign.template_id.slice(0, 8)}</strong></div>
            <div><span>Audience</span><strong>{selectedAudience?.name || 'Selected at launch'}</strong></div>
            <div><span>Requested</span><strong>{formatInt(workflowStatus?.analytics?.requested_count ?? selectedCampaignPerformance?.requested_count)}</strong></div>
            <div><span>Sent</span><strong>{formatInt(workflowStatus?.analytics?.sent_count ?? selectedCampaignPerformance?.sent_count)}</strong></div>
            <div><span>Latest job</span><strong>{workflowStatus?.latest_send_job?.status || 'None loaded'}</strong></div>
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <div>
            <h2>{selectedCampaign ? selectedCampaign.name : 'Create Campaign'}</h2>
            <span className="muted">{selectedCampaign ? 'Edit setup, test content, and manage launch readiness.' : 'Create a draft campaign from a template and audience.'}</span>
          </div>
          <div className="button-row">
            <a href="#campaigns">Back to campaigns</a>
            <a href="#templates">Edit templates</a>
          </div>
        </div>
        <div className="workflow-section">
          <h3>1. Setup</h3>
          <div className="form-grid">
            <label>
              Campaign name
              <input value={campaignName} onChange={(event) => {
                setCampaignName(event.target.value);
                setWorkflowStatus(null);
              }} />
            </label>
            <label>
              Existing campaign
              <select
                value={selectedCampaignId}
                onChange={(event) => {
                  const nextCampaignId = event.target.value;
                  setSelectedCampaignId(nextCampaignId);
                  setWorkflowStatus(null);
                  window.location.hash = nextCampaignId ? `#campaigns/${nextCampaignId}` : '#campaigns/new';
                }}
              >
                <option value="">Create new draft</option>
                {campaignItems.map((campaign) => (
                  <option value={campaign.id} key={campaign.id}>{campaign.name} ({campaign.status})</option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="workflow-section">
          <h3>2. Content and Audience</h3>
          <div className="form-grid">
            <label>
              Template
              <select value={templateId} onChange={(event) => {
                setTemplateId(event.target.value);
                setWorkflowStatus(null);
              }}>
                <option value="">Select template</option>
                {templates.map((template) => (
                  <option value={template.id} key={template.id}>{template.name}</option>
                ))}
              </select>
            </label>
            <label>
              Audience
              <select value={audienceId} onChange={(event) => {
                setAudienceId(event.target.value);
                setWorkflowStatus(null);
              }}>
                <option value="">Select audience</option>
                {audiences.map((audience) => (
                  <option value={audience.id} key={audience.id}>{audience.name} ({formatInt(audience.estimated_count)})</option>
                ))}
              </select>
            </label>
            <label>
              Audience size
              <input value={selectedAudience ? formatInt(selectedAudience.estimated_count) : 'No audience selected'} readOnly />
            </label>
          </div>
        </div>
        <div className="workflow-section">
          <h3>3. Test Data</h3>
          <div className="form-grid">
            <label>
              Test recipient
              <input value={testEmail} onChange={(event) => setTestEmail(event.target.value)} placeholder="you@example.com" />
            </label>
            <label className="wide-field">
              Personalization data
              <textarea value={variablesJson} onChange={(event) => setVariablesJson(event.target.value)} rows={8} />
            </label>
          </div>
        </div>
        <div className="campaign-action-bar">
          <div>
            <strong>Draft</strong>
            <button className="primary" onClick={createDraftCampaign} disabled={operationBusy || !templateId}>{selectedCampaignId ? 'Save Setup' : 'Save Draft'}</button>
          </div>
          <div>
            <strong>Review</strong>
            <button className="ghost" onClick={loadCampaignWorkflowStatus} disabled={operationBusy || !selectedCampaignId}>Readiness</button>
            <button className="ghost" onClick={validateCampaign} disabled={operationBusy || !selectedCampaignId}>Check Audience</button>
            <button className="ghost" onClick={previewTestEmail} disabled={operationBusy || !selectedCampaignId}>Preview Email</button>
          </div>
          <div>
            <strong>Send</strong>
            <button className="ghost" onClick={sendTestEmail} disabled={operationBusy || !selectedCampaignId}>Send Test</button>
            <button className="ghost" onClick={dryRunLaunch} disabled={operationBusy || !selectedCampaignId}>Dry-Run Launch</button>
          </div>
        </div>
        <div className={`operation-banner ${operationStatus.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{operationBusy ? 'Working' : 'Status'}</strong>
          <span>{operationStatus}</span>
          {selectedCampaign ? <small>Selected: {selectedCampaign.name}</small> : null}
        </div>
        {previewHtml ? (
          <iframe className="email-preview" title="Campaign test preview" srcDoc={previewHtml} />
        ) : null}
      </section>
    </section>
  );
}

function AutomationsPage({ journeys, journeyItems, templates, contacts, enrollments, executions, route, onRefresh }: {
  journeys: JourneyPerformance[];
  journeyItems: JourneyRead[];
  templates: TemplateRead[];
  contacts: ContactRead[];
  enrollments: JourneyEnrollmentRead[];
  executions: JourneyStepExecutionRead[];
  route: string;
  onRefresh: () => Promise<void>;
}) {
  const [selectedJourneyId, setSelectedJourneyId] = useState('');
  const [name, setName] = useState('ESP Journey Draft');
  const [description, setDescription] = useState('Created from the ESP automation workflow.');
  const [entryRuleJson, setEntryRuleJson] = useState('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
  const [exitRuleJson, setExitRuleJson] = useState('{}');
  const [templateId, setTemplateId] = useState('');
  const [stepName, setStepName] = useState('Send welcome email');
  const [contactId, setContactId] = useState('');
  const [enrollmentVariablesJson, setEnrollmentVariablesJson] = useState('{\n  "source": "esp_automation",\n  "plan": "trial"\n}');
  const [status, setStatus] = useState('Ready to create or update a journey.');
  const [busy, setBusy] = useState(false);
  const routeParts = route.split('/');
  const routeJourneyId = routeParts[0] === 'automations' && routeParts[1] && routeParts[1] !== 'new' ? routeParts[1] : '';
  const isDetailPage = routeParts[0] === 'automations' && Boolean(routeParts[1]);

  useEffect(() => {
    if (routeParts[1] === 'new') {
      resetJourneyEditor();
    } else if (routeJourneyId) {
      const journey = journeyItems.find((item) => item.id === routeJourneyId);
      if (journey && selectedJourneyId !== journey.id) loadJourneyIntoEditor(journey);
    } else if (!selectedJourneyId && journeyItems.length) {
      loadJourneyIntoEditor(journeyItems[0]);
    }
    if (!templateId && templates.length) setTemplateId(templates[0].id);
    if (!contactId && contacts.length) setContactId(contacts[0].id);
  }, [contactId, contacts, journeyItems, route, routeJourneyId, selectedJourneyId, templateId, templates]);

  const failures = journeys.reduce((sum, item) =>
    sum + Number(item.failed_count || 0) + Number(item.step_failed_count || 0), 0);
  const queued = journeys.reduce((sum, item) => sum + Number(item.queued_send_count || 0), 0);
  const active = journeys.reduce((sum, item) => sum + Number(item.active_count || 0), 0);
  const completed = journeys.reduce((sum, item) => sum + Number(item.completed_count || 0), 0);
  const selectedJourney = journeyItems.find((item) => item.id === selectedJourneyId);
  const selectedJourneyPerformance = journeys.find((item) => item.journey_id === selectedJourneyId);
  const selectedContact = contacts.find((item) => item.id === contactId);
  const visibleEnrollments = selectedJourneyId
    ? enrollments.filter((item) => item.journey_id === selectedJourneyId)
    : enrollments;
  const visibleExecutions = selectedJourneyId
    ? executions.filter((item) => item.journey_id === selectedJourneyId)
    : executions;
  const failedExecutions = visibleExecutions.filter((item) => item.status === 'failed').length;

  function loadJourneyIntoEditor(journey: JourneyRead) {
    setSelectedJourneyId(journey.id);
    setName(journey.name);
    setDescription(journey.description || '');
    setEntryRuleJson(JSON.stringify(journey.entry_rule_tree || {}, null, 2));
    setExitRuleJson(JSON.stringify(journey.exit_rule_tree || {}, null, 2));
    setStatus(`Loaded journey: ${journey.name}`);
  }

  function resetJourneyEditor() {
    setSelectedJourneyId('');
    setName('ESP Journey Draft');
    setDescription('Created from the ESP automation workflow.');
    setEntryRuleJson('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
    setExitRuleJson('{}');
    setStatus('Ready to create a new journey.');
  }

  function parseJsonObject(value: string, label: string) {
    try {
      const parsed = JSON.parse(value || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error(`${label} must be a JSON object.`);
      }
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : `Invalid ${label}.`);
    }
  }

  async function runJourneyOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    try {
      const message = await operation();
      setStatus(message);
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function saveJourney() {
    await runJourneyOperation(selectedJourneyId ? 'Saving journey' : 'Creating journey', async () => {
      const payload = {
        name: name.trim() || 'Untitled ESP Journey',
        description: description || null,
        entry_rule_tree: parseJsonObject(entryRuleJson, 'entry rule'),
        exit_rule_tree: parseJsonObject(exitRuleJson, 'exit rule'),
        metadata_json: { source: 'esp_automation_workflow' },
      };
      const saved = selectedJourneyId
        ? await fetchJson<JourneyRead>(`/api/v1/journeys/${selectedJourneyId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        : await fetchJson<JourneyRead>('/api/v1/journeys', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      setSelectedJourneyId(saved.id);
      window.location.hash = `#automations/${saved.id}`;
      await onRefresh();
      return `Saved journey: ${saved.name}`;
    });
  }

  async function addSendStep() {
    await runJourneyOperation('Adding send step', async () => {
      if (!selectedJourneyId) throw new Error('Save or select a journey first.');
      if (!templateId) throw new Error('Select a template.');
      const step = await fetchJson<JourneyStepRead>(`/api/v1/journeys/${selectedJourneyId}/steps`, {
        method: 'POST',
        body: JSON.stringify({
          name: stepName.trim() || 'Send email',
          step_type: 'send_email',
          position: selectedJourney?.steps?.length || 0,
          config: { template_id: templateId },
        }),
      });
      await onRefresh();
      return `Added step: ${step.name}`;
    });
  }

  async function processDue() {
    await runJourneyOperation('Processing due enrollments', async () => {
      const suffix = selectedJourneyId ? `&journey_id=${encodeURIComponent(selectedJourneyId)}` : '';
      const data = await fetchJson<{ claimed_count: number; completed_count: number; failed_count: number; queued_send_count: number }>(`/api/v1/journeys/process?limit=25${suffix}`, {
        method: 'POST',
      });
      await onRefresh();
      return `Processed ${formatInt(data.claimed_count)} enrollment(s), queued ${formatInt(data.queued_send_count)} send(s), failed ${formatInt(data.failed_count)}.`;
    });
  }

  async function enrollContact() {
    await runJourneyOperation('Enrolling contact', async () => {
      if (!selectedJourneyId) throw new Error('Save or select a journey first.');
      if (!contactId) throw new Error('Select a contact.');
      const enrollment = await fetchJson<JourneyEnrollmentRead>(`/api/v1/journeys/${selectedJourneyId}/enrollments`, {
        method: 'POST',
        body: JSON.stringify({
          contact_id: contactId,
          variables: parseJsonObject(enrollmentVariablesJson, 'enrollment variables'),
        }),
      });
      await onRefresh();
      return `Enrolled ${selectedContact?.email || contactId}; status is ${enrollment.status}.`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Journeys', value: formatInt(journeys.length), change: 'total' }} />
          <MetricCard metric={{ label: 'Active', value: formatInt(active), change: 'active enrollments' }} />
          <MetricCard metric={{ label: 'Completed', value: formatInt(completed), change: 'finished enrollments' }} />
          <MetricCard metric={{ label: 'Failures', value: formatInt(failures), change: 'needs review', tone: failures ? 'warn' : 'good' }} />
          <MetricCard metric={{ label: 'Queued sends', value: formatInt(queued), change: 'delivery backlog', tone: queued ? 'warn' : 'good' }} />
          <MetricCard metric={{ label: 'Visible runs', value: formatInt(visibleEnrollments.length), change: `${formatInt(visibleExecutions.length)} executions` }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Automation Journeys</h2>
              <span className="muted">Select a journey to inspect health, then open it for builder controls.</span>
            </div>
            <a href="#automations/new">Create journey</a>
          </div>
          {journeys.length ? (
            <table>
              <thead>
                <tr>
                  <th>Journey</th>
                  <th>Status</th>
                  <th>Enrollments</th>
                  <th>Active</th>
                  <th>Completed</th>
                  <th>Failures</th>
                  <th>Queued sends</th>
                  <th>Builder</th>
                </tr>
              </thead>
              <tbody>
                {journeys.map((journey) => {
                  const journeyItem = journeyItems.find((item) => item.id === journey.journey_id);
                  return (
                    <tr
                      className={`selectable-row ${journey.journey_id === selectedJourneyId ? 'selected-row' : ''}`}
                      key={journey.journey_id}
                      onClick={() => {
                        if (journeyItem) loadJourneyIntoEditor(journeyItem);
                        else setSelectedJourneyId(journey.journey_id);
                      }}
                    >
                      <td>{journey.name}</td>
                      <td><span className="pill">{journey.status}</span></td>
                      <td>{formatInt(journey.enrollment_count)}</td>
                      <td>{formatInt(journey.active_count)}</td>
                      <td>{formatInt(journey.completed_count)}</td>
                      <td>{formatInt(Number(journey.failed_count || 0) + Number(journey.step_failed_count || 0))}</td>
                      <td>{formatInt(journey.queued_send_count)}</td>
                      <td><a href={`#automations/${journey.journey_id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No journeys yet" detail="Create a journey and add send steps to start automation testing." actionHref="#automations/new" actionLabel="Create journey" />
          )}
        </section>
        {(selectedJourney || selectedJourneyPerformance) ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedJourney?.name || selectedJourneyPerformance?.name || 'Selected journey'}</h2>
                <span className="muted">Selected journey summary</span>
              </div>
              <a href={`#automations/${selectedJourneyId}`}>Open journey builder</a>
            </div>
            <div className="summary-grid">
              <div><span>Status</span><strong>{selectedJourney?.status || selectedJourneyPerformance?.status || '-'}</strong></div>
              <div><span>Steps</span><strong>{formatInt(selectedJourney?.steps?.length || 0)}</strong></div>
              <div><span>Enrollments</span><strong>{formatInt(selectedJourneyPerformance?.enrollment_count)}</strong></div>
              <div><span>Active</span><strong>{formatInt(selectedJourneyPerformance?.active_count)}</strong></div>
              <div><span>Failures</span><strong>{formatInt(Number(selectedJourneyPerformance?.failed_count || 0) + Number(selectedJourneyPerformance?.step_failed_count || 0))}</strong></div>
              <div><span>Queued sends</span><strong>{formatInt(selectedJourneyPerformance?.queued_send_count)}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      {(selectedJourney || selectedJourneyPerformance) ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedJourney?.name || selectedJourneyPerformance?.name || 'Selected journey'}</h2>
              <span className="muted">Selected journey summary</span>
            </div>
            <a href="#delivery">Open delivery</a>
          </div>
          <div className="summary-grid">
            <div><span>Status</span><strong>{selectedJourney?.status || selectedJourneyPerformance?.status || '-'}</strong></div>
            <div><span>Steps</span><strong>{formatInt(selectedJourney?.steps?.length || 0)}</strong></div>
            <div><span>Enrollments</span><strong>{formatInt(selectedJourneyPerformance?.enrollment_count)}</strong></div>
            <div><span>Active</span><strong>{formatInt(selectedJourneyPerformance?.active_count)}</strong></div>
            <div><span>Failures</span><strong>{formatInt(Number(selectedJourneyPerformance?.failed_count || 0) + Number(selectedJourneyPerformance?.step_failed_count || 0))}</strong></div>
            <div><span>Queued sends</span><strong>{formatInt(selectedJourneyPerformance?.queued_send_count)}</strong></div>
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>{selectedJourney ? 'Journey Builder' : 'Create Journey'}</h2>
          <div className="button-row">
            <a href="#automations">Back to automations</a>
            <a href="#delivery">Open delivery</a>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Existing journey
            <select value={selectedJourneyId} onChange={(event) => {
              const journey = journeyItems.find((item) => item.id === event.target.value);
              if (journey) {
                loadJourneyIntoEditor(journey);
                window.location.hash = `#automations/${journey.id}`;
              } else {
                resetJourneyEditor();
                window.location.hash = '#automations/new';
              }
            }}>
              <option value="">Create new journey</option>
              {journeyItems.map((journey) => (
                <option value={journey.id} key={journey.id}>{journey.name} ({journey.status})</option>
              ))}
            </select>
          </label>
          <label>
            Journey name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Send-step template
            <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
              <option value="">Select template</option>
              {templates.map((template) => <option value={template.id} key={template.id}>{template.name}</option>)}
            </select>
          </label>
          <label className="wide-field">
            Description
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label>
            Step name
            <input value={stepName} onChange={(event) => setStepName(event.target.value)} />
          </label>
          <label>
            Enrollment contact
            <select value={contactId} onChange={(event) => setContactId(event.target.value)}>
              <option value="">Select contact</option>
              {contacts.map((contact) => <option value={contact.id} key={contact.id}>{contact.email}</option>)}
            </select>
          </label>
          <label className="wide-field">
            Entry rule JSON
            <textarea value={entryRuleJson} onChange={(event) => setEntryRuleJson(event.target.value)} rows={8} />
          </label>
          <label>
            Exit rule JSON
            <textarea value={exitRuleJson} onChange={(event) => setExitRuleJson(event.target.value)} rows={8} />
          </label>
          <label className="wide-field">
            Enrollment variables JSON
            <textarea value={enrollmentVariablesJson} onChange={(event) => setEnrollmentVariablesJson(event.target.value)} rows={6} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveJourney} disabled={busy}>Save Journey</button>
          <button className="ghost" onClick={addSendStep} disabled={busy || !selectedJourneyId || !templateId}>Add Send Step</button>
          <button className="ghost" onClick={enrollContact} disabled={busy || !selectedJourneyId || !contactId}>Enroll Contact</button>
          <button className="ghost" onClick={processDue} disabled={busy}>Process Due</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {selectedJourney?.steps?.length ? <small>{selectedJourney.steps.map((step) => `${step.position + 1}. ${step.name}`).join(' | ')}</small> : null}
          {selectedContact ? <small>Selected contact: {selectedContact.email}</small> : null}
        </div>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <h2>Journey Enrollments</h2>
          <span className="muted">{formatInt(visibleEnrollments.length)} visible</span>
        </div>
        {visibleEnrollments.length ? (
          <table>
            <thead><tr><th>Contact</th><th>Status</th><th>Current step</th><th>Due</th><th>Entered</th><th>Error</th></tr></thead>
            <tbody>
              {visibleEnrollments.slice(0, 12).map((enrollment) => {
                const contact = contacts.find((item) => item.id === enrollment.contact_id);
                const step = journeyItems.flatMap((journey) => journey.steps || []).find((item) => item.id === enrollment.current_step_id);
                return (
                  <tr key={enrollment.id}>
                    <td>{contact?.email || enrollment.contact_id.slice(0, 8)}</td>
                    <td><span className="pill">{enrollment.status}</span></td>
                    <td>{step?.name || enrollment.current_step_id?.slice(0, 8) || '-'}</td>
                    <td>{enrollment.due_at || '-'}</td>
                    <td>{enrollment.entered_at}</td>
                    <td>{enrollment.last_error || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No enrollments visible" detail="Select a journey and contact, then enroll the contact to test journey execution." actionHref="#contacts" actionLabel="Open Contacts" />
        )}
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <h2>Step Executions</h2>
          <span className="muted">{formatInt(visibleExecutions.length)} visible / {formatInt(failedExecutions)} failed</span>
        </div>
        {visibleExecutions.length ? (
          <table>
            <thead><tr><th>Executed</th><th>Status</th><th>Step</th><th>Contact</th><th>Send record</th><th>Error</th></tr></thead>
            <tbody>
              {visibleExecutions.slice(0, 12).map((execution) => {
                const contact = contacts.find((item) => item.id === execution.contact_id);
                const step = journeyItems.flatMap((journey) => journey.steps || []).find((item) => item.id === execution.step_id);
                return (
                  <tr key={execution.id}>
                    <td>{execution.executed_at}</td>
                    <td><span className="pill">{execution.status}</span></td>
                    <td>{step?.name || execution.step_id.slice(0, 8)}</td>
                    <td>{contact?.email || execution.contact_id.slice(0, 8)}</td>
                    <td>{execution.send_record_id ? execution.send_record_id.slice(0, 8) : '-'}</td>
                    <td>{execution.error_message || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No step executions visible" detail="Process due journey enrollments to create execution history." actionHref="#delivery" actionLabel="Open Delivery" />
        )}
      </section>
    </section>
  );
}

function AudiencePage({ audiences, audienceItems, metadata, route, onRefresh, onOperation }: {
  audiences: AudiencePerformance[];
  audienceItems: AudienceRead[];
  metadata: ContactMetadata | null;
  route: string;
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const routeParts = route.split('/');
  const routeAudienceId = routeParts[0] === 'audience' && routeParts[1] && routeParts[1] !== 'new'
    ? routeParts[1]
    : '';
  const isDetailPage = routeParts[0] === 'audience' && Boolean(routeParts[1]);
  const isNewAudience = routeParts[0] === 'audience' && routeParts[1] === 'new';
  const [selectedAudienceId, setSelectedAudienceId] = useState('');
  const [name, setName] = useState('ESP Audience Draft');
  const [description, setDescription] = useState('Created from the ESP audience workflow.');
  const [ruleJson, setRuleJson] = useState('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
  const [status, setStatus] = useState('Ready to create or preview an audience.');
  const [busy, setBusy] = useState(false);
  const [matchedCount, setMatchedCount] = useState<number | null>(null);
  const [sampleContacts, setSampleContacts] = useState<ContactRead[]>([]);

  useEffect(() => {
    if (isNewAudience && selectedAudienceId) {
      resetAudienceEditor();
      return;
    }
    if (routeAudienceId) {
      const routedAudience = audienceItems.find((item) => item.id === routeAudienceId);
      if (routedAudience && routedAudience.id !== selectedAudienceId) {
        loadAudienceIntoEditor(routedAudience);
      }
      return;
    }
    if (!isDetailPage && !selectedAudienceId && audienceItems.length) {
      loadAudienceIntoEditor(audienceItems[0]);
    }
  }, [audienceItems, isDetailPage, isNewAudience, routeAudienceId, selectedAudienceId]);

  const estimated = audiences.reduce((sum, item) => sum + Number(item.estimated_count || 0), 0);
  const sent = audiences.reduce((sum, item) => sum + Number(item.sent_count || 0), 0);
  const bestAudience = audiences.reduce<AudiencePerformance | null>((best, item) =>
    !best || Number(item.open_rate || 0) > Number(best.open_rate || 0) ? item : best, null);
  const audiencePerformanceById = new Map(audiences.map((audience) => [audience.audience_id, audience]));
  const selectedAudience = audienceItems.find((item) => item.id === selectedAudienceId);
  const selectedAudiencePerformance = selectedAudienceId ? audiencePerformanceById.get(selectedAudienceId) : null;
  const ruleJsonValid = isRuleJsonValid();
  const availableFields = metadata?.fields || [];
  const attributeFields = (metadata?.attribute_keys || []).map((key) => `attributes.${key}`);
  const fieldHints = [...availableFields, ...attributeFields].slice(0, 18);
  const workflowSteps = [
    { label: 'Define', detail: name.trim() ? name.trim() : 'Name the audience', ready: Boolean(name.trim()) },
    { label: 'Rule', detail: ruleJsonValid ? 'Valid JSON rule' : 'Fix rule JSON', ready: ruleJsonValid },
    { label: 'Preview', detail: matchedCount === null ? 'Preview reach' : `${formatInt(matchedCount)} matched`, ready: matchedCount !== null },
    { label: 'Snapshot', detail: selectedAudienceId ? 'Ready to snapshot' : 'Save audience first', ready: Boolean(selectedAudienceId) },
  ];
  const readinessCards = [
    {
      label: 'Contact data',
      detail: metadata ? `${formatInt(metadata.total)} contacts, ${formatInt(metadata.fields.length + metadata.attribute_keys.length)} usable fields` : 'Contact metadata has not loaded.',
      ready: Boolean(metadata?.total),
    },
    {
      label: 'Audience rule',
      detail: ruleJsonValid ? 'Rule JSON can be previewed.' : 'Rule JSON must be an object.',
      ready: ruleJsonValid,
    },
    {
      label: 'Preview impact',
      detail: matchedCount === null ? 'Run preview before using this audience in a campaign.' : `${formatInt(matchedCount)} contact(s) matched.`,
      ready: matchedCount !== null,
    },
    {
      label: 'Campaign-ready',
      detail: selectedAudienceId && Number(matchedCount || 0) > 0 ? 'Saved with reachable contacts.' : 'Save and preview before launch.',
      ready: Boolean(selectedAudienceId && Number(matchedCount || 0) > 0),
    },
  ];

  function loadAudienceIntoEditor(audience: AudienceRead) {
    setSelectedAudienceId(audience.id);
    setName(audience.name);
    setDescription(audience.description || '');
    setRuleJson(JSON.stringify(audience.rule_tree || {}, null, 2));
    setMatchedCount(audience.estimated_count);
    setSampleContacts([]);
    setStatus(`Loaded audience: ${audience.name}`);
  }

  function resetAudienceEditor() {
    setSelectedAudienceId('');
    setName('ESP Audience Draft');
    setDescription('Created from the ESP audience workflow.');
    setRuleJson('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
    setMatchedCount(null);
    setSampleContacts([]);
    setStatus('Ready to create or preview a new audience.');
  }

  function parsedRuleTree() {
    try {
      const parsed = JSON.parse(ruleJson || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Rule tree must be a JSON object.');
      }
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid audience rule JSON.');
    }
  }

  function isRuleJsonValid() {
    try {
      parsedRuleTree();
      return true;
    } catch {
      return false;
    }
  }

  function insertFieldRule(field: string) {
    setRuleJson(JSON.stringify({ field, comparator: 'exists', value: true }, null, 2));
    setMatchedCount(null);
    setSampleContacts([]);
    setStatus(`Inserted starter rule for ${field}. Preview to estimate impact.`);
  }

  async function runAudienceOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    onOperation({ label: 'Audience workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setStatus(message);
      onOperation({ label: 'Audience workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'Audience workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  async function saveAudience() {
    await runAudienceOperation(selectedAudienceId ? 'Saving audience' : 'Creating audience', async () => {
      const payload = {
        name: name.trim() || 'Untitled ESP Audience',
        description: description || null,
        rule_tree: parsedRuleTree(),
      };
      const saved = selectedAudienceId
        ? await fetchJson<AudienceRead>(`/api/v1/audiences/${selectedAudienceId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        : await fetchJson<AudienceRead>('/api/v1/audiences', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      setSelectedAudienceId(saved.id);
      setMatchedCount(saved.estimated_count);
      await onRefresh();
      window.location.hash = `#audience/${saved.id}`;
      return `Saved audience: ${saved.name} (${formatInt(saved.estimated_count)} matched).`;
    });
  }

  async function previewAudience() {
    await runAudienceOperation('Previewing audience', async () => {
      const data = await fetchJson<{ estimated_count: number; sample_contacts: ContactRead[] }>('/api/v1/audiences/preview', {
        method: 'POST',
        body: JSON.stringify({ rule_tree: parsedRuleTree(), limit: 10 }),
      });
      setMatchedCount(data.estimated_count);
      setSampleContacts(data.sample_contacts || []);
      return `Preview matched ${formatInt(data.estimated_count)} contact(s).`;
    });
  }

  async function snapshotAudience() {
    await runAudienceOperation('Creating snapshot', async () => {
      if (!selectedAudienceId) throw new Error('Save or select an audience first.');
      const data = await fetchJson<{ version_number: number; estimated_count: number }>(`/api/v1/audiences/${selectedAudienceId}/snapshots`, {
        method: 'POST',
        body: JSON.stringify({ metadata_json: { source: 'esp_audience_workflow' } }),
      });
      return `Created snapshot v${data.version_number} with ${formatInt(data.estimated_count)} contacts.`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid entity-list-page">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Audiences', value: formatInt(audienceItems.length), change: 'saved segments' }} />
          <MetricCard metric={{ label: 'Estimated reach', value: formatInt(estimated), change: 'matched contacts' }} />
          <MetricCard metric={{ label: 'Sent', value: formatInt(sent), change: 'campaign sends' }} />
          <MetricCard metric={{ label: 'Best open rate', value: bestAudience ? formatPct(bestAudience.open_rate) : '0%', change: bestAudience?.name || 'no activity' }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Audiences</h2>
              <span className="muted">Select an audience for summary, or open one to edit rules and preview reach.</span>
            </div>
            <div className="button-row">
              <a href="#data">Import contacts</a>
              <a href="#audience/new">New audience</a>
            </div>
          </div>
          {audienceItems.length ? (
            <table>
              <thead>
                <tr>
                  <th>Audience</th>
                  <th>Status</th>
                  <th>Estimated</th>
                  <th>Sent</th>
                  <th>Open rate</th>
                  <th>Click rate</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {audienceItems.map((audience) => {
                  const performance = audiencePerformanceById.get(audience.id);
                  return (
                    <tr
                      className={`selectable-row ${audience.id === selectedAudienceId ? 'selected-row' : ''}`}
                      key={audience.id}
                      onClick={() => loadAudienceIntoEditor(audience)}
                    >
                      <td>{audience.name}</td>
                      <td><span className="pill">{audience.status}</span></td>
                      <td>{formatInt(performance?.estimated_count ?? audience.estimated_count)}</td>
                      <td>{formatInt(performance?.sent_count)}</td>
                      <td>{performance ? formatPct(performance.open_rate) : '-'}</td>
                      <td>{performance ? formatPct(performance.click_rate) : '-'}</td>
                      <td><a href={`#audience/${audience.id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No audiences yet" detail="Import contacts or create a dynamic audience rule set." actionHref="#audience/new" actionLabel="Create audience" />
          )}
        </section>
        {selectedAudience ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedAudience.name}</h2>
                <span className="muted">Selected audience summary</span>
              </div>
              <a href={`#audience/${selectedAudience.id}`}>Open audience builder</a>
            </div>
            <div className="summary-grid">
              <div><span>Status</span><strong>{selectedAudience.status}</strong></div>
              <div><span>Estimated</span><strong>{formatInt(selectedAudiencePerformance?.estimated_count ?? selectedAudience.estimated_count)}</strong></div>
              <div><span>Sent</span><strong>{formatInt(selectedAudiencePerformance?.sent_count)}</strong></div>
              <div><span>Open rate</span><strong>{selectedAudiencePerformance ? formatPct(selectedAudiencePerformance.open_rate) : '-'}</strong></div>
              <div><span>Click rate</span><strong>{selectedAudiencePerformance ? formatPct(selectedAudiencePerformance.click_rate) : '-'}</strong></div>
              <div><span>Description</span><strong>{selectedAudience.description || '-'}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      <section className="campaign-flow full-span">
        {workflowSteps.map((step, index) => (
          <article className={step.ready ? 'ready' : ''} key={step.label}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <p>{step.detail}</p>
            </div>
          </article>
        ))}
      </section>
      <section className="workflow-grid full-span">
        {readinessCards.map((item) => (
          <article className={`workflow-card ${item.ready ? '' : 'warn'}`} key={item.label}>
            <span>{item.ready ? 'Ready' : 'Needs attention'}</span>
            <strong>{item.label}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>
      {selectedAudience ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedAudience.name}</h2>
              <span className="muted">Audience workspace summary</span>
            </div>
            <a href="#campaigns">Use in campaign</a>
          </div>
          <div className="summary-grid">
            <div><span>Status</span><strong>{selectedAudience.status}</strong></div>
            <div><span>Estimated</span><strong>{formatInt(selectedAudiencePerformance?.estimated_count ?? selectedAudience.estimated_count)}</strong></div>
            <div><span>Sent</span><strong>{formatInt(selectedAudiencePerformance?.sent_count)}</strong></div>
            <div><span>Open rate</span><strong>{selectedAudiencePerformance ? formatPct(selectedAudiencePerformance.open_rate) : '-'}</strong></div>
            <div><span>Click rate</span><strong>{selectedAudiencePerformance ? formatPct(selectedAudiencePerformance.click_rate) : '-'}</strong></div>
            <div><span>Description</span><strong>{selectedAudience.description || '-'}</strong></div>
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <div>
            <h2>{selectedAudience ? selectedAudience.name : 'Create Audience'}</h2>
            <span className="muted">Define rules, preview matched contacts, and snapshot stable campaign targets.</span>
          </div>
          <div className="button-row">
            <a href="#audience">Back to audiences</a>
            <a href="#data">Import contacts</a>
          </div>
        </div>
        <div className="workflow-section">
          <h3>1. Setup</h3>
          <div className="form-grid">
            <label>
              Existing audience
              <select
                value={selectedAudienceId}
                onChange={(event) => {
                  const nextAudienceId = event.target.value;
                  const audience = audienceItems.find((item) => item.id === nextAudienceId);
                  if (audience) loadAudienceIntoEditor(audience);
                  else resetAudienceEditor();
                  window.location.hash = nextAudienceId ? `#audience/${nextAudienceId}` : '#audience/new';
                }}
              >
                <option value="">Create new audience</option>
                {audienceItems.map((audience) => (
                  <option value={audience.id} key={audience.id}>{audience.name} ({formatInt(audience.estimated_count)})</option>
                ))}
              </select>
            </label>
            <label>
              Audience name
              <input value={name} onChange={(event) => {
                setName(event.target.value);
                setMatchedCount(null);
              }} />
            </label>
            <label>
              Matched contacts
              <input value={matchedCount === null ? 'Not previewed' : formatInt(matchedCount)} readOnly />
            </label>
            <label className="wide-field">
              Description
              <input value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
          </div>
        </div>
        <div className="workflow-section">
          <h3>2. Rule definition</h3>
          {fieldHints.length ? (
            <div className="field-chip-row" aria-label="Available audience fields">
              {fieldHints.map((field) => (
                <button type="button" className="field-chip" key={field} onClick={() => insertFieldRule(field)}>
                  {field}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Import contacts to expose fields and attribute keys for rule building.</p>
          )}
          <div className="form-grid">
            <label className="wide-field">
              Rule JSON
              <textarea value={ruleJson} onChange={(event) => {
                setRuleJson(event.target.value);
                setMatchedCount(null);
                setSampleContacts([]);
              }} rows={10} />
            </label>
          </div>
        </div>
        <div className="workflow-section">
          <h3>3. Preview and snapshot</h3>
          <div className="button-row">
            <button className="primary" onClick={saveAudience} disabled={busy}>Save Audience</button>
            <button className="ghost" onClick={previewAudience} disabled={busy}>Preview Contacts</button>
            <button className="ghost" onClick={snapshotAudience} disabled={busy || !selectedAudienceId}>Create Snapshot</button>
          </div>
          <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
            <strong>{busy ? 'Working' : 'Status'}</strong>
            <span>{status}</span>
          </div>
        </div>
        {sampleContacts.length ? (
          <div className="workflow-section">
            <h3>Matched Contacts Preview</h3>
            <table>
              <thead><tr><th>Email</th><th>Name</th><th>Source</th><th>Status</th></tr></thead>
              <tbody>
                {sampleContacts.map((contact) => (
                  <tr key={contact.id}>
                    <td>{contact.email}</td>
                    <td>{[contact.first_name, contact.last_name].filter(Boolean).join(' ') || '-'}</td>
                    <td>{contact.source || '-'}</td>
                    <td><span className="pill">{contact.is_unsubscribed ? 'unsubscribed' : 'subscribed'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </section>
  );
}

function TemplatesPage({ templates, route, onRefresh, onOperation }: {
  templates: TemplateRead[];
  route: string;
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const routeParts = route.split('/');
  const routeTemplateId = routeParts[0] === 'templates' && routeParts[1] && routeParts[1] !== 'new'
    ? routeParts[1]
    : '';
  const isDetailPage = routeParts[0] === 'templates' && Boolean(routeParts[1]);
  const isNewTemplate = routeParts[0] === 'templates' && routeParts[1] === 'new';
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [name, setName] = useState('ESP Template Draft');
  const [subject, setSubject] = useState('Hello {{ first_name }}');
  const [htmlBody, setHtmlBody] = useState('<p>Hello {{ first_name }},</p>\n<p>Welcome to Email Engine.</p>');
  const [cssBody, setCssBody] = useState('body { font-family: Arial, sans-serif; color: #111827; }\np { line-height: 1.5; }');
  const [variablesJson, setVariablesJson] = useState('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
  const [status, setStatus] = useState('Ready to edit or preview a template.');
  const [busy, setBusy] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [variables, setVariables] = useState<TemplateVariable[]>([]);
  const [aiInstruction, setAiInstruction] = useState('Improve clarity, preserve all Jinja variables, add a stronger CTA, and keep the design email-safe.');
  const [aiRecommendations, setAiRecommendations] = useState<AITemplateRecommendation[]>([]);
  const [aiNotes, setAiNotes] = useState<string[]>([]);
  const [pendingAiDraft, setPendingAiDraft] = useState<AITemplateDraft | null>(null);
  const [editorMode, setEditorMode] = useState<'edit' | 'preview'>('edit');
  const [cssPreset, setCssPreset] = useState({
    font: 'Arial, Helvetica, sans-serif',
    background: '#f5f7fb',
    text: '#111827',
    accent: '#2563eb',
    container: '640',
    padding: '24',
    radius: '8',
  });
  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId);
  const templateCategories = new Set(templates.map((template) => template.category || 'template'));
  const detectedVariableNames = variables.map((item) => item.name);
  const liveTemplateGuidance = [
    {
      label: 'Subject',
      ready: Boolean(subject.trim()),
      detail: subject.trim() ? 'Subject line is present.' : 'Add a clear subject before preview or send.',
    },
    {
      label: 'Personalization',
      ready: /\{\{\s*[\w.]+\s*(\|[^}]*)?\}\}/.test(subject + htmlBody),
      detail: detectedVariableNames.length ? `${formatInt(detectedVariableNames.length)} variables detected.` : 'Variables refresh automatically during preview.',
    },
    {
      label: 'Compliance',
      ready: /unsubscribe/i.test(htmlBody),
      detail: /unsubscribe/i.test(htmlBody) ? 'Unsubscribe language appears present.' : 'Add unsubscribe copy or URL before production use.',
    },
    {
      label: 'Tracking',
      ready: /tracking_(open|click)|href=/i.test(htmlBody),
      detail: /tracking_(open|click)|href=/i.test(htmlBody) ? 'Tracking or links are present.' : 'Add links or tracking placeholders for reporting.',
    },
    {
      label: 'Preview',
      ready: Boolean(previewHtml),
      detail: previewHtml ? 'Rendered with sample variables.' : 'Render preview after edits.',
    },
  ];
  const templateSteps = [
    { label: 'Setup', detail: name.trim() || 'Name the template', ready: Boolean(name.trim()) },
    { label: 'Subject', detail: subject.trim() || 'Add a subject line', ready: Boolean(subject.trim()) },
    { label: 'Content', detail: htmlBody.trim() ? 'HTML/Jinja ready' : 'Add HTML/Jinja', ready: Boolean(htmlBody.trim()) },
    { label: 'Variables', detail: variables.length ? `${formatInt(variables.length)} detected` : 'Auto-detected at preview', ready: Boolean(variables.length) },
    { label: 'Preview', detail: previewHtml ? 'Preview rendered' : 'Render preview', ready: Boolean(previewHtml) },
  ];

  useEffect(() => {
    if (routeTemplateId && selectedTemplateId !== routeTemplateId) {
      const template = templates.find((item) => item.id === routeTemplateId);
      if (template) loadTemplateIntoEditor(template);
    }
    if (isNewTemplate && selectedTemplateId) {
      resetTemplateEditor();
    }
  }, [isNewTemplate, routeTemplateId, selectedTemplateId, templates]);

  function resetTemplateEditor() {
    setSelectedTemplateId('');
    setName('ESP Template Draft');
    setSubject('Hello {{ first_name }}');
    setHtmlBody('<p>Hello {{ first_name }},</p>\n<p>Welcome to Email Engine.</p>');
    setCssBody('body { font-family: Arial, sans-serif; color: #111827; }\np { line-height: 1.5; }');
    setVariablesJson('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
    setPreviewHtml('');
    setVariables([]);
    setAiRecommendations([]);
    setAiNotes([]);
    setPendingAiDraft(null);
    setEditorMode('edit');
    setStatus('Ready to create a new template.');
  }

  function loadTemplateIntoEditor(template: TemplateRead) {
    setSelectedTemplateId(template.id);
    setName(template.name);
    setSubject(template.subject);
    setHtmlBody(template.html_body || '');
    setCssBody(template.css_body || '');
    setPreviewHtml('');
    setAiRecommendations([]);
    setAiNotes([]);
    setPendingAiDraft(null);
    setEditorMode('edit');
    setStatus(`Loaded template: ${template.name}`);
  }

  function applyAiDraft(draft: AITemplateDraft) {
    setSubject(draft.subject || subject);
    setHtmlBody(draft.html_body || htmlBody);
    setCssBody(draft.css_body || '');
    if (draft.sample_variables && Object.keys(draft.sample_variables).length) {
      setVariablesJson(JSON.stringify(draft.sample_variables, null, 2));
    }
    setAiNotes(draft.change_summary || draft.notes || []);
    setPreviewHtml('');
    setPendingAiDraft(null);
    setEditorMode('edit');
  }

  function generatedCssFromPreset() {
    const width = Number(cssPreset.container) || 640;
    const padding = Number(cssPreset.padding) || 24;
    const radius = Number(cssPreset.radius) || 8;
    return [
      `body { margin: 0; background: ${cssPreset.background}; color: ${cssPreset.text}; font-family: ${cssPreset.font}; }`,
      `.email-container { max-width: ${width}px; margin: 0 auto; background: #ffffff; padding: ${padding}px; border-radius: ${radius}px; }`,
      `h1, h2, h3 { color: ${cssPreset.text}; margin-top: 0; }`,
      `p { line-height: 1.55; }`,
      `a { color: ${cssPreset.accent}; }`,
      `.button, .cta { display: inline-block; background: ${cssPreset.accent}; color: #ffffff; padding: 12px 18px; border-radius: ${radius}px; text-decoration: none; font-weight: 700; }`,
      `.muted { color: #6b7280; font-size: 13px; }`,
      `@media only screen and (max-width: 640px) { .email-container { width: auto !important; padding: 18px !important; border-radius: 0 !important; } }`,
    ].join('\n');
  }

  function applyCssPreset() {
    setCssBody(generatedCssFromPreset());
    setPreviewHtml('');
    setStatus('Generated email-safe CSS from style controls. Click Preview to render it.');
  }

  function parsedVariables() {
    try {
      const parsed = JSON.parse(variablesJson || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Variables must be a JSON object.');
      }
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid variables JSON.');
    }
  }

  async function runTemplateOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    onOperation({ label: 'Template workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setStatus(message);
      onOperation({ label: 'Template workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'Template workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  async function saveTemplate() {
    await runTemplateOperation(selectedTemplateId ? 'Saving template' : 'Creating template', async () => {
      const payload = {
        name: name.trim() || 'Untitled ESP Template',
        subject,
        html_body: htmlBody,
        css_body: cssBody || null,
        text_body: null,
      };
      const saved = selectedTemplateId
        ? await fetchJson<TemplateRead>(`/api/v1/templates/${selectedTemplateId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        : await fetchJson<TemplateRead>('/api/v1/templates', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      setSelectedTemplateId(saved.id);
      window.location.hash = `#templates/${saved.id}`;
      await onRefresh();
      return `Saved template: ${saved.name}`;
    });
  }

  async function cancelTemplateChanges() {
    await runTemplateOperation('Cancelling changes', async () => {
      if (!selectedTemplateId) {
        resetTemplateEditor();
        return 'Discarded unsaved draft changes.';
      }
      const template = await fetchJson<TemplateRead>(`/api/v1/templates/${selectedTemplateId}`);
      loadTemplateIntoEditor(template);
      await onRefresh();
      return `Reloaded template: ${template.name}`;
    });
  }

  async function previewTemplate() {
    await runTemplateOperation('Rendering preview', async () => {
      const variableData = await refreshVariables(true);
      const data = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject,
          html_body: htmlBody,
          css_body: cssBody || null,
          variables: variableData.renderVariables,
        }),
      });
      setPreviewHtml(data.html_body || '');
      setEditorMode('preview');
      const issueText = data.errors?.length ? ` ${data.errors.join('; ')}` : '';
      return `Rendered preview: ${data.subject}.${issueText}`;
    });
  }

  async function refreshVariables(fillMissingSamples = true) {
    const currentVariables = parsedVariables();
    const data = await fetchJson<{ variables: TemplateVariable[]; sample_variables: Record<string, unknown>; errors: string[] }>('/api/v1/templates/variables', {
      method: 'POST',
      body: JSON.stringify({
        subject,
        html_body: htmlBody,
        css_body: cssBody || null,
        variables: currentVariables,
      }),
    });
    setVariables(data.variables || []);
    const renderVariables = data.sample_variables && Object.keys(data.sample_variables).length
      ? { ...data.sample_variables, ...currentVariables }
      : currentVariables;
    if (fillMissingSamples && data.sample_variables && Object.keys(data.sample_variables).length) {
      setVariablesJson(JSON.stringify(renderVariables, null, 2));
    }
    return { ...data, renderVariables };
  }

  async function seedSamples() {
    await runTemplateOperation('Seeding sample templates', async () => {
      const data = await fetchJson<TemplateRead[]>('/api/v1/templates/samples', { method: 'POST' });
      await onRefresh();
      return `Sample templates ready: ${formatInt(data.length)} templates.`;
    });
  }

  async function draftWithAi() {
    await runTemplateOperation('Drafting with AI', async () => {
      const draft = await fetchJson<AITemplateDraft>('/api/v1/ai/templates/draft', {
        method: 'POST',
        body: JSON.stringify({
          brief: `${name}. Subject direction: ${subject}. Create an email-safe HTML/Jinja template for this concept.`,
          brand: { product: 'Email Engine ESP', tone: 'clear, direct, useful' },
          required_variables: ['first_name', 'tracking_open', 'tracking_click', 'unsubscribe_url'],
        }),
      });
      setPendingAiDraft(draft);
      setAiNotes(draft.change_summary || draft.notes || []);
      return `AI draft ready for review from ${draft.provider}/${draft.model}.`;
    });
  }

  async function applyAiEdit(instruction = aiInstruction) {
    await runTemplateOperation('Applying AI edit', async () => {
      const draft = await fetchJson<AITemplateDraft>('/api/v1/ai/templates/edit', {
        method: 'POST',
        body: JSON.stringify({
          instruction,
          current_subject: subject,
          current_html: htmlBody,
          current_css: cssBody || null,
          sample_variables: parsedVariables(),
        }),
      });
      setPendingAiDraft(draft);
      setAiNotes(draft.change_summary || draft.notes || []);
      return `AI edit ready for review. ${(draft.change_summary || draft.notes || []).slice(0, 2).join(' ')}`;
    });
  }

  async function loadAiRecommendations() {
    await runTemplateOperation('Loading AI suggestions', async () => {
      const data = await fetchJson<{ recommendations: AITemplateRecommendation[]; sample_variables: Record<string, unknown>; summary: string[] }>('/api/v1/ai/templates/recommend', {
        method: 'POST',
        body: JSON.stringify({
          current_subject: subject,
          current_html: htmlBody,
          current_css: cssBody || null,
          sample_variables: parsedVariables(),
          goals: ['Improve engagement', 'Preserve dynamic variables', 'Improve deliverability readiness', 'Improve email-safe layout'],
        }),
      });
      setAiRecommendations(data.recommendations || []);
      setAiNotes(data.summary || []);
      if (data.sample_variables && Object.keys(data.sample_variables).length) {
        setVariablesJson(JSON.stringify(data.sample_variables, null, 2));
      }
      return `Loaded ${formatInt(data.recommendations?.length || 0)} AI suggestion(s).`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Templates', value: formatInt(templates.length), change: 'saved templates' }} />
          <MetricCard metric={{ label: 'Categories', value: formatInt(templateCategories.size), change: 'content groups' }} />
          <MetricCard metric={{ label: 'Selected', value: selectedTemplate ? 'Loaded' : 'None', change: selectedTemplate?.name || 'select a template' }} />
          <MetricCard metric={{ label: 'Variables', value: formatInt(variables.length), change: variables.length ? 'last inspected' : 'not inspected' }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Templates</h2>
              <span className="muted">Select a template to inspect content readiness, then open it for editing and preview.</span>
            </div>
            <div className="button-row">
              <a href="#templates/new">Create template</a>
              <button className="link-button" onClick={seedSamples} disabled={busy}>Seed samples</button>
            </div>
          </div>
          {templates.length ? (
            <table>
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Subject</th>
                  <th>Category</th>
                  <th>CSS</th>
                  <th>HTML size</th>
                  <th>Editor</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => (
                  <tr
                    className={`selectable-row ${template.id === selectedTemplateId ? 'selected-row' : ''}`}
                    key={template.id}
                    onClick={() => loadTemplateIntoEditor(template)}
                  >
                    <td>{template.name}</td>
                    <td>{template.subject}</td>
                    <td>{template.category || 'template'}</td>
                    <td><span className="pill">{template.css_body ? 'configured' : 'none'}</span></td>
                    <td>{formatInt((template.html_body || '').length)}</td>
                    <td><a href={`#templates/${template.id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No templates yet" detail="Seed sample templates or create one in the template wizard." actionHref="#templates/new" actionLabel="Create template" />
          )}
        </section>
        {selectedTemplate ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedTemplate.name}</h2>
                <span className="muted">Selected template summary</span>
              </div>
              <a href={`#templates/${selectedTemplate.id}`}>Open template wizard</a>
            </div>
            <div className="summary-grid">
              <div><span>Category</span><strong>{selectedTemplate.category || 'template'}</strong></div>
              <div><span>Subject</span><strong>{selectedTemplate.subject}</strong></div>
              <div><span>CSS</span><strong>{selectedTemplate.css_body ? 'Configured' : 'None'}</strong></div>
              <div><span>Text</span><strong>{selectedTemplate.text_body ? 'Configured' : 'None'}</strong></div>
              <div><span>HTML size</span><strong>{formatInt((selectedTemplate.html_body || '').length)} chars</strong></div>
              <div><span>Variables</span><strong>{variables.length ? variables.map((item) => item.name).join(', ') : 'Inspect in wizard'}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      <section className="campaign-flow full-span">
        {templateSteps.map((step, index) => (
          <article className={step.ready ? 'ready' : ''} key={step.label}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <p>{step.detail}</p>
            </div>
          </article>
        ))}
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <div>
            <h2>{selectedTemplate ? selectedTemplate.name : 'Create Template'}</h2>
            <span className="muted">Edit HTML/Jinja, render previews, and review AI drafts before applying them.</span>
          </div>
          <div className="button-row">
            <a href="#templates">Back to templates</a>
            <button className="link-button" onClick={seedSamples} disabled={busy}>Seed samples</button>
          </div>
        </div>
        <div className="template-action-bar">
          <div className="button-row">
            <button className="primary" onClick={saveTemplate} disabled={busy}>Save Template</button>
            <button className="ghost" onClick={cancelTemplateChanges} disabled={busy}>Cancel Changes</button>
          </div>
          <div className="button-row">
            <button className="ghost" onClick={draftWithAi} disabled={busy}>Draft with AI</button>
            <button className="ghost" onClick={() => applyAiEdit()} disabled={busy}>Review AI Edit</button>
            <button className="ghost" onClick={loadAiRecommendations} disabled={busy}>AI Suggestions</button>
          </div>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {variables.length ? <small>{variables.map((item) => item.name).join(', ')}</small> : null}
        </div>
        <div className="template-editor-shell">
          <section className="template-editor-main">
            <div className="tab-row">
              <button className={editorMode === 'edit' ? 'active' : ''} onClick={() => setEditorMode('edit')}>Edit</button>
              <button className={editorMode === 'preview' ? 'active' : ''} onClick={previewTemplate} disabled={busy}>Preview</button>
            </div>
            {editorMode === 'edit' ? (
              <div className="form-grid">
                <label>
                  Existing template
                  <select value={selectedTemplateId} onChange={(event) => {
                    const template = templates.find((item) => item.id === event.target.value);
                    if (template) {
                      loadTemplateIntoEditor(template);
                      window.location.hash = `#templates/${template.id}`;
                    } else {
                      resetTemplateEditor();
                      window.location.hash = '#templates/new';
                    }
                  }}>
                    <option value="">Create new template</option>
                    {templates.map((template) => (
                      <option value={template.id} key={template.id}>{template.name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Template name
                  <input value={name} onChange={(event) => setName(event.target.value)} />
                </label>
                <label>
                  Subject
                  <input value={subject} onChange={(event) => setSubject(event.target.value)} />
                </label>
                <label className="wide-field">
                  HTML / Jinja
                  <textarea value={htmlBody} onChange={(event) => {
                    setHtmlBody(event.target.value);
                    setPreviewHtml('');
                  }} rows={16} />
                </label>
                <label>
                  Sample variables JSON
                  <textarea value={variablesJson} onChange={(event) => {
                    setVariablesJson(event.target.value);
                    setPreviewHtml('');
                  }} rows={16} />
                </label>
                <label className="wide-field">
                  CSS
                  <textarea value={cssBody} onChange={(event) => {
                    setCssBody(event.target.value);
                    setPreviewHtml('');
                  }} rows={7} />
                </label>
                <label className="wide-field">
                  AI instruction
                  <textarea value={aiInstruction} onChange={(event) => setAiInstruction(event.target.value)} rows={4} />
                </label>
              </div>
            ) : previewHtml ? (
              <iframe className="email-preview" title="Template preview" srcDoc={previewHtml} />
            ) : (
              <div className="empty-state">
                <strong>Preview not rendered</strong>
                <p>Click Preview to refresh variables and render this template with the current sample data.</p>
              </div>
            )}
          </section>
          <aside className="template-side-pane">
            <section className="workflow-section">
              <h3>Readiness</h3>
              <div className="compact-status-list">
                {liveTemplateGuidance.map((item) => (
                  <div className={item.ready ? 'ready' : 'warn'} key={item.label}>
                    <strong>{item.label}</strong>
                    <span>{item.detail}</span>
                  </div>
                ))}
              </div>
            </section>
            <section className="workflow-section">
              <h3>CSS Helper</h3>
              <div className="css-helper-grid">
                <label>
                  Font
                  <select value={cssPreset.font} onChange={(event) => setCssPreset((current) => ({ ...current, font: event.target.value }))}>
                    <option value="Arial, Helvetica, sans-serif">Arial</option>
                    <option value="Georgia, 'Times New Roman', serif">Georgia</option>
                    <option value="'Trebuchet MS', Arial, sans-serif">Trebuchet</option>
                    <option value="Verdana, Geneva, sans-serif">Verdana</option>
                  </select>
                </label>
                <label>
                  Background
                  <input type="color" value={cssPreset.background} onChange={(event) => setCssPreset((current) => ({ ...current, background: event.target.value }))} />
                </label>
                <label>
                  Text
                  <input type="color" value={cssPreset.text} onChange={(event) => setCssPreset((current) => ({ ...current, text: event.target.value }))} />
                </label>
                <label>
                  Accent
                  <input type="color" value={cssPreset.accent} onChange={(event) => setCssPreset((current) => ({ ...current, accent: event.target.value }))} />
                </label>
                <label>
                  Width
                  <input type="number" min="480" max="760" step="20" value={cssPreset.container} onChange={(event) => setCssPreset((current) => ({ ...current, container: event.target.value }))} />
                </label>
                <label>
                  Padding
                  <input type="number" min="12" max="48" step="2" value={cssPreset.padding} onChange={(event) => setCssPreset((current) => ({ ...current, padding: event.target.value }))} />
                </label>
                <label>
                  Radius
                  <input type="number" min="0" max="24" step="2" value={cssPreset.radius} onChange={(event) => setCssPreset((current) => ({ ...current, radius: event.target.value }))} />
                </label>
              </div>
              <button className="ghost" onClick={applyCssPreset} disabled={busy}>Generate CSS</button>
            </section>
            <section className="workflow-section">
              <h3>AI Draft Review</h3>
              {pendingAiDraft ? (
                <div className="ai-draft-preview">
                  <span className="muted">{pendingAiDraft.provider}/{pendingAiDraft.model}</span>
                  <strong>{pendingAiDraft.subject}</strong>
                  <pre>{(pendingAiDraft.html_body || '').slice(0, 900)}</pre>
                  <div className="button-row">
                    <button className="primary" onClick={() => applyAiDraft(pendingAiDraft)} disabled={busy}>Apply Draft</button>
                    <button className="ghost" onClick={() => setPendingAiDraft(null)} disabled={busy}>Discard</button>
                  </div>
                </div>
              ) : (
                <p className="muted">AI drafts and edits appear here for review before they change the editor.</p>
              )}
            </section>
            {(aiNotes.length || aiRecommendations.length) ? (
              <section className="workflow-section">
                <h3>AI Suggestions</h3>
                {aiNotes.length ? (
                  <div className="module-links">
                    {aiNotes.slice(0, 3).map((note) => <span className="pill" key={note}>{note}</span>)}
                  </div>
                ) : null}
                {aiRecommendations.length ? (
                  <div className="recommendation-list">
                    {aiRecommendations.slice(0, 5).map((item) => (
                      <article key={item.code}>
                        <span className="pill">{item.priority}</span>
                        <strong>{item.title}</strong>
                        <p>{item.detail}</p>
                        <button className="link-button" onClick={() => applyAiEdit(item.suggested_instruction)} disabled={busy}>Review change</button>
                      </article>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}
          </aside>
        </div>
      </section>
    </section>
  );
}

function DeliveryPage({ sendJobs, sendRecords, campaigns, onRefresh, onOperation }: {
  sendJobs: CampaignSendJobRead[];
  sendRecords: EmailSendRecordRead[];
  campaigns: CampaignRead[];
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const [selectedJobId, setSelectedJobId] = useState('');
  const [selectedRecordId, setSelectedRecordId] = useState('');
  const [progress, setProgress] = useState<CampaignSendJobProgress | null>(null);
  const [trackingLinks, setTrackingLinks] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState('Ready to inspect send jobs and delivery records.');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedJobId && sendJobs.length) setSelectedJobId(sendJobs[0].id);
    if (!selectedRecordId && sendRecords.length) setSelectedRecordId(sendRecords[0].id);
  }, [sendJobs, selectedJobId, selectedRecordId, sendRecords]);

  const queuedRecords = sendRecords.filter((record) => record.status === 'queued').length;
  const failedRecords = sendRecords.filter((record) => record.status === 'failed').length;
  const sentRecords = sendRecords.filter((record) => record.status === 'sent').length;
  const activeJobs = sendJobs.filter((job) => !['completed', 'failed', 'cancelled'].includes(job.status)).length;
  const selectedJob = sendJobs.find((job) => job.id === selectedJobId);
  const selectedRecord = sendRecords.find((record) => record.id === selectedRecordId);
  const selectedCampaign = campaigns.find((campaign) => campaign.id === selectedJob?.campaign_id || campaign.id === selectedRecord?.campaign_id);

  async function runDeliveryOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    onOperation({ label: 'Delivery workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setStatus(message);
      onOperation({ label: 'Delivery workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'Delivery workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  async function loadProgress() {
    await runDeliveryOperation('Loading send job progress', async () => {
      if (!selectedJobId) throw new Error('Select a send job.');
      const data = await fetchJson<CampaignSendJobProgress>(`/api/v1/campaign-send-jobs/${selectedJobId}/progress`);
      setProgress(data);
      return `Loaded progress: ${formatInt(data.processed_count)} processed, ${formatInt(data.remaining_count)} remaining.`;
    });
  }

  async function processQueued() {
    await runDeliveryOperation('Processing queued records', async () => {
      const suffix = selectedJobId ? `?limit=25&send_job_id=${encodeURIComponent(selectedJobId)}` : '?limit=25';
      const data = await fetchJson<DeliveryRun>(`/api/v1/delivery/process-queued${suffix}`, { method: 'POST' });
      await onRefresh();
      if (selectedJobId) {
        const refreshedProgress = await fetchJson<CampaignSendJobProgress>(`/api/v1/campaign-send-jobs/${selectedJobId}/progress`);
        setProgress(refreshedProgress);
      }
      return `Processed ${formatInt(data.claimed_count)} record(s): ${formatInt(data.sent_count)} sent, ${formatInt(data.failed_count)} failed.`;
    });
  }

  async function requeueRecord() {
    await runDeliveryOperation('Requeueing send record', async () => {
      if (!selectedRecordId) throw new Error('Select a send record.');
      const record = await fetchJson<EmailSendRecordRead>(`/api/v1/email-send-records/${selectedRecordId}/requeue`, { method: 'POST' });
      await onRefresh();
      return `Requeued ${record.to_email}; status is ${record.status}.`;
    });
  }

  async function skipRecord() {
    await runDeliveryOperation('Skipping send record', async () => {
      if (!selectedRecordId) throw new Error('Select a send record.');
      const record = await fetchJson<EmailSendRecordRead>(`/api/v1/email-send-records/${selectedRecordId}/skip`, { method: 'POST' });
      await onRefresh();
      return `Skipped ${record.to_email}; status is ${record.status}.`;
    });
  }

  async function loadTrackingLinks() {
    await runDeliveryOperation('Loading tracking links', async () => {
      if (!selectedRecordId) throw new Error('Select a send record.');
      const data = await fetchJson<Record<string, unknown>>(`/api/v1/email-send-records/${selectedRecordId}/tracking-links`);
      setTrackingLinks(data);
      return `Loaded tracking links for ${selectedRecord?.to_email || selectedRecordId}.`;
    });
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Send jobs', value: formatInt(sendJobs.length), change: `${formatInt(activeJobs)} active`, tone: activeJobs ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Queued records', value: formatInt(queuedRecords), change: 'visible records', tone: queuedRecords ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Sent records', value: formatInt(sentRecords), change: 'visible records' }} />
        <MetricCard metric={{ label: 'Failed records', value: formatInt(failedRecords), change: 'needs review', tone: failedRecords ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Progress', value: progress ? formatPct(progress.percent_complete) : 'n/a', change: progress ? `${formatInt(progress.active_count)} active` : 'select a job' }} />
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <div>
            <h2>Send Jobs</h2>
            <span className="muted">Select a job to review queue progress and process records.</span>
          </div>
          <button className="link-button" onClick={loadProgress} disabled={busy || !selectedJobId}>Load progress</button>
        </div>
        {sendJobs.length ? (
          <table>
            <thead><tr><th>Job</th><th>Campaign</th><th>Status</th><th>Requested</th><th>Queued</th><th>Suppressed</th></tr></thead>
            <tbody>
              {sendJobs.map((job) => (
                <tr
                  className={`selectable-row ${job.id === selectedJobId ? 'selected-row' : ''}`}
                  key={job.id}
                  onClick={() => {
                    setSelectedJobId(job.id);
                    setProgress(null);
                  }}
                >
                  <td>{job.id.slice(0, 8)}</td>
                  <td>{campaigns.find((campaign) => campaign.id === job.campaign_id)?.name || job.campaign_id.slice(0, 8)}</td>
                  <td><span className="pill">{job.status}</span></td>
                  <td>{formatInt(job.requested_count)}</td>
                  <td>{formatInt(job.queued_count)}</td>
                  <td>{formatInt(job.suppressed_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState title="No send jobs" detail="Launch or dry-run a campaign to create send jobs for delivery review." actionHref="#campaigns" actionLabel="Open Campaigns" />}
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <div>
            <h2>Send Records</h2>
            <span className="muted">Select a record to requeue, skip, inspect attempts, or load tracking links.</span>
          </div>
          <button className="link-button" onClick={loadTrackingLinks} disabled={busy || !selectedRecordId}>Tracking links</button>
        </div>
        {sendRecords.length ? (
          <table>
            <thead><tr><th>Email</th><th>Status</th><th>Campaign</th><th>Job</th><th>Provider</th><th>Attempts</th><th>Next retry</th></tr></thead>
            <tbody>
              {sendRecords.map((record) => (
                <tr
                  className={`selectable-row ${record.id === selectedRecordId ? 'selected-row' : ''}`}
                  key={record.id}
                  onClick={() => {
                    setSelectedRecordId(record.id);
                    setTrackingLinks(null);
                  }}
                >
                  <td>{record.to_email}</td>
                  <td><span className="pill">{record.status}</span></td>
                  <td>{campaigns.find((campaign) => campaign.id === record.campaign_id)?.name || record.campaign_id.slice(0, 8)}</td>
                  <td>{record.send_job_id ? record.send_job_id.slice(0, 8) : '-'}</td>
                  <td>{providerLabel(record.provider)}</td>
                  <td>{record.attempt_count} / {record.max_attempts}</td>
                  <td>{record.next_attempt_at || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState title="No send records" detail="Launch a test campaign or process a journey to create send records." actionHref="#campaigns" actionLabel="Open Campaigns" />}
      </section>
      {(selectedJob || selectedRecord) ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>Selected Delivery Item</h2>
              <span className="muted">{selectedCampaign?.name || 'No campaign context'}</span>
            </div>
            <a href="#campaigns">Open campaigns</a>
          </div>
          <div className="summary-grid">
            <div><span>Job</span><strong>{selectedJob ? selectedJob.id.slice(0, 8) : '-'}</strong></div>
            <div><span>Job status</span><strong>{selectedJob?.status || '-'}</strong></div>
            <div><span>Requested</span><strong>{formatInt(selectedJob?.requested_count)}</strong></div>
            <div><span>Record</span><strong>{selectedRecord ? selectedRecord.id.slice(0, 8) : '-'}</strong></div>
            <div><span>Recipient</span><strong>{selectedRecord?.to_email || '-'}</strong></div>
            <div><span>Record status</span><strong>{selectedRecord?.status || '-'}</strong></div>
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>Delivery Operations</h2>
          <a href="#analytics">Open analytics</a>
        </div>
        <div className="form-grid">
          <label className="wide-field">
            Send job
            <select value={selectedJobId} onChange={(event) => {
              setSelectedJobId(event.target.value);
              setProgress(null);
            }}>
              <option value="">All queued records</option>
              {sendJobs.map((job) => (
                <option value={job.id} key={job.id}>
                  {job.id.slice(0, 8)} | {job.status} | requested {formatInt(job.requested_count)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Send record
            <select value={selectedRecordId} onChange={(event) => {
              setSelectedRecordId(event.target.value);
              setTrackingLinks(null);
            }}>
              <option value="">Select record</option>
              {sendRecords.map((record) => (
                <option value={record.id} key={record.id}>
                  {record.to_email} | {record.status} | {record.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Provider
            <input value={providerLabel(selectedRecord?.provider)} readOnly />
          </label>
          <label>
            Attempts
            <input value={selectedRecord ? `${selectedRecord.attempt_count} / ${selectedRecord.max_attempts}` : 'No record selected'} readOnly />
          </label>
          <label className="wide-field">
            Last error
            <input value={selectedRecord?.error_message || 'No error visible'} readOnly />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={processQueued} disabled={busy}>Process Queued</button>
          <button className="ghost" onClick={loadProgress} disabled={busy || !selectedJobId}>Load Progress</button>
          <button className="ghost" onClick={requeueRecord} disabled={busy || !selectedRecordId}>Requeue Record</button>
          <button className="ghost" onClick={skipRecord} disabled={busy || !selectedRecordId}>Skip Record</button>
          <button className="ghost" onClick={loadTrackingLinks} disabled={busy || !selectedRecordId}>Tracking Links</button>
          <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh Lists</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
      {progress ? (
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Processed', value: formatInt(progress.processed_count), change: `${formatInt(progress.remaining_count)} remaining` }} />
          <MetricCard metric={{ label: 'Queued', value: formatInt(progress.queued_count), change: `${formatInt(progress.sending_count)} sending`, tone: progress.queued_count ? 'warn' : 'good' }} />
          <MetricCard metric={{ label: 'Sent', value: formatInt(progress.sent_count), change: 'completed sends' }} />
          <MetricCard metric={{ label: 'Failed', value: formatInt(progress.failed_count), change: `${formatInt(progress.skipped_count)} skipped`, tone: progress.failed_count ? 'warn' : 'good' }} />
        </section>
      ) : null}
      {trackingLinks ? (
        <section className="panel full-span">
          <div className="panel-head"><h2>Tracking Links</h2><span className="muted">{selectedRecord?.to_email || selectedRecordId}</span></div>
          <pre className="json-preview">{JSON.stringify(trackingLinks, null, 2)}</pre>
        </section>
      ) : null}
    </section>
  );
}

function CompliancePage({ suppressions, sendRecords, route, onRefresh }: {
  suppressions: SuppressionRead[];
  sendRecords: EmailSendRecordRead[];
  route: string;
  onRefresh: () => Promise<void>;
}) {
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState<SuppressionRead['reason']>('manual');
  const [source, setSource] = useState('esp_compliance');
  const [selectedSuppressionId, setSelectedSuppressionId] = useState('');
  const [status, setStatus] = useState('Ready to create or remove suppressions.');
  const [busy, setBusy] = useState(false);
  const routeParts = route.split('/');
  const routeSuppressionId = routeParts[0] === 'compliance' && routeParts[1] && routeParts[1] !== 'new' ? routeParts[1] : '';
  const isDetailPage = routeParts[0] === 'compliance' && Boolean(routeParts[1]);

  useEffect(() => {
    if (routeParts[1] === 'new') {
      resetSuppressionEditor();
    } else if (routeSuppressionId) {
      const suppression = suppressions.find((item) => item.id === routeSuppressionId);
      if (suppression && selectedSuppressionId !== suppression.id) loadSuppression(suppression);
    } else if (!selectedSuppressionId && suppressions.length) {
      setSelectedSuppressionId(suppressions[0].id);
    }
  }, [route, routeSuppressionId, selectedSuppressionId, suppressions]);

  const manualCount = suppressions.filter((item) => item.reason === 'manual').length;
  const unsubscribeCount = suppressions.filter((item) => item.reason === 'unsubscribe').length;
  const bounceCount = suppressions.filter((item) => item.reason === 'hard_bounce').length;
  const complaintCount = suppressions.filter((item) => item.reason === 'spam_complaint').length;
  const failedWithEmail = sendRecords.filter((record) => record.status === 'failed' && record.to_email).slice(0, 10);
  const selectedSuppression = suppressions.find((item) => item.id === selectedSuppressionId);

  function resetSuppressionEditor() {
    setEmail('');
    setReason('manual');
    setSource('esp_compliance');
    setSelectedSuppressionId('');
    setStatus('Ready to create a new suppression.');
  }

  function loadSuppression(item: SuppressionRead) {
    setSelectedSuppressionId(item.id);
    setEmail(item.email);
    setReason(item.reason);
    setSource(item.source);
    setStatus(`Loaded suppression for ${item.email}.`);
  }

  async function runComplianceOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    try {
      setStatus(await operation());
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function addSuppression() {
    await runComplianceOperation('Creating suppression', async () => {
      const trimmedEmail = email.trim();
      if (!trimmedEmail) throw new Error('Email is required.');
      const created = await fetchJson<SuppressionRead>('/api/v1/suppressions', {
        method: 'POST',
        body: JSON.stringify({
          email: trimmedEmail,
          reason,
          source: source.trim() || 'esp_compliance',
          metadata_json: { source_page: 'esp_compliance' },
        }),
      });
      setSelectedSuppressionId(created.id);
      window.location.hash = `#compliance/${created.id}`;
      await onRefresh();
      return `Created ${created.reason} suppression for ${created.email}.`;
    });
  }

  async function deleteSuppression() {
    await runComplianceOperation('Deleting suppression', async () => {
      if (!selectedSuppressionId) throw new Error('Select a suppression.');
      await fetchJson<{ id: string }>(`/api/v1/suppressions/${selectedSuppressionId}`, { method: 'DELETE' });
      const deletedEmail = selectedSuppression?.email || selectedSuppressionId;
      resetSuppressionEditor();
      window.location.hash = '#compliance';
      await onRefresh();
      return `Deleted suppression for ${deletedEmail}.`;
    });
  }

  return (
    <section className="page-grid">
      {!isDetailPage ? (
        <>
          <section className="metric-grid full-span compact-metrics">
            <MetricCard metric={{ label: 'Suppressions', value: formatInt(suppressions.length), change: 'visible records', tone: suppressions.length ? 'warn' : 'good' }} />
            <MetricCard metric={{ label: 'Manual', value: formatInt(manualCount), change: 'operator managed' }} />
            <MetricCard metric={{ label: 'Unsubscribes', value: formatInt(unsubscribeCount), change: 'contact opt-outs', tone: unsubscribeCount ? 'warn' : 'good' }} />
            <MetricCard metric={{ label: 'Bounces', value: formatInt(bounceCount), change: `${formatInt(complaintCount)} complaints`, tone: bounceCount || complaintCount ? 'warn' : 'good' }} />
          </section>
          <section className="panel table-panel full-span">
            <div className="panel-head">
              <div>
                <h2>Suppressions</h2>
                <span className="muted">Select a suppression to inspect source, provider message, and delete controls.</span>
              </div>
              <div className="button-row">
                <a href="#compliance/new">Add suppression</a>
                <a href="#delivery">Open delivery</a>
              </div>
            </div>
            {suppressions.length ? (
              <table>
                <thead><tr><th>Email</th><th>Reason</th><th>Source</th><th>Provider message</th><th>Contact</th><th>Editor</th></tr></thead>
                <tbody>
                  {suppressions.map((item) => (
                    <tr
                      className={`selectable-row ${item.id === selectedSuppressionId ? 'selected-row' : ''}`}
                      key={item.id}
                      onClick={() => loadSuppression(item)}
                    >
                      <td>{item.email}</td>
                      <td><span className="pill">{item.reason}</span></td>
                      <td>{item.source}</td>
                      <td>{item.provider_message_id || '-'}</td>
                      <td>{item.contact_id ? item.contact_id.slice(0, 8) : '-'}</td>
                      <td><a href={`#compliance/${item.id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <EmptyState title="No suppressions" detail="Create manual suppressions here or ingest provider feedback to populate compliance records." actionHref="#compliance/new" actionLabel="Add suppression" />}
          </section>
        </>
      ) : null}
      {selectedSuppression ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedSuppression.email}</h2>
              <span className="muted">Suppression editor summary</span>
            </div>
            <a href="#compliance">Back to suppressions</a>
          </div>
          <div className="summary-grid">
            <div><span>Reason</span><strong>{selectedSuppression.reason}</strong></div>
            <div><span>Source</span><strong>{selectedSuppression.source}</strong></div>
            <div><span>Provider message</span><strong>{selectedSuppression.provider_message_id || '-'}</strong></div>
            <div><span>Contact</span><strong>{selectedSuppression.contact_id ? selectedSuppression.contact_id.slice(0, 8) : '-'}</strong></div>
            <div><span>Metadata</span><strong>{Object.keys(selectedSuppression.metadata_json || {}).length ? 'Present' : 'None'}</strong></div>
            <div><span>State</span><strong>Suppressed</strong></div>
          </div>
        </section>
      ) : null}
      {isDetailPage ? (
        <section className="panel full-span campaign-workbench">
          <div className="panel-head">
            <h2>{selectedSuppression ? 'Compliance Operations' : 'Add Suppression'}</h2>
            <div className="button-row">
              <a href="#compliance">Back to suppressions</a>
              <a href="#analytics">Open analytics</a>
            </div>
          </div>
          <div className="form-grid">
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="person@example.com" />
            </label>
            <label>
              Reason
              <select value={reason} onChange={(event) => setReason(event.target.value as SuppressionRead['reason'])}>
                <option value="manual">Manual</option>
                <option value="unsubscribe">Unsubscribe</option>
                <option value="hard_bounce">Hard bounce</option>
                <option value="spam_complaint">Spam complaint</option>
              </select>
            </label>
            <label>
              Source
              <input value={source} onChange={(event) => setSource(event.target.value)} />
            </label>
            <label className="wide-field">
              Existing suppression
              <select value={selectedSuppressionId} onChange={(event) => {
                const suppression = suppressions.find((item) => item.id === event.target.value);
                if (suppression) {
                  loadSuppression(suppression);
                  window.location.hash = `#compliance/${suppression.id}`;
                } else {
                  resetSuppressionEditor();
                  window.location.hash = '#compliance/new';
                }
              }}>
                <option value="">Select suppression</option>
                {suppressions.map((item) => (
                  <option value={item.id} key={item.id}>{item.email} | {item.reason} | {item.source}</option>
                ))}
              </select>
            </label>
            <label>
              Selected provider message
              <input value={selectedSuppression?.provider_message_id || 'none'} readOnly />
            </label>
          </div>
          <div className="button-row">
            <button className="primary" onClick={addSuppression} disabled={busy}>Add Suppression</button>
            <button className="ghost" onClick={deleteSuppression} disabled={busy || !selectedSuppressionId}>Delete Selected</button>
            <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh Suppressions</button>
          </div>
          <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
            <strong>{busy ? 'Working' : 'Status'}</strong>
            <span>{status}</span>
          </div>
          {failedWithEmail.length ? (
            <div className="button-row">
              {failedWithEmail.map((record) => (
                <button className="ghost" key={record.id} onClick={() => setEmail(record.to_email)} disabled={busy}>
                  Use {record.to_email}
                </button>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}

function DataPage({ dataSources, mappings, importJobs, route, onRefresh, onOperation }: {
  dataSources: DataSourceRead[];
  mappings: DataSourceMappingRead[];
  importJobs: DataSourceImportJobRead[];
  route: string;
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [selectedMappingId, setSelectedMappingId] = useState('');
  const [name, setName] = useState('ESP Manual Contact Source');
  const [sourceType, setSourceType] = useState<DataSourceRead['source_type']>('manual');
  const [statusValue, setStatusValue] = useState<DataSourceRead['status']>('draft');
  const [configJson, setConfigJson] = useState('{\n  "fields": ["email", "first_name", "last_name", "plan"],\n  "sample_rows": [\n    { "email": "sample@example.com", "first_name": "Sample", "last_name": "Contact", "plan": "trial" }\n  ]\n}');
  const [mappingName, setMappingName] = useState('Contact import mapping');
  const [mappingJson, setMappingJson] = useState('{\n  "email": "email",\n  "first_name": "first_name",\n  "last_name": "last_name",\n  "source": "source",\n  "attributes": {\n    "plan": "plan"\n  }\n}');
  const [rowsJson, setRowsJson] = useState('[\n  { "email": "esp-import-sample@example.com", "first_name": "ESP", "last_name": "Sample", "source": "esp_data_page", "plan": "trial" }\n]');
  const [validation, setValidation] = useState<DataSourceValidationRead | null>(null);
  const [schema, setSchema] = useState<DataSourceSchemaRead | null>(null);
  const [status, setStatus] = useState('Ready to configure a source, map fields, and import contacts.');
  const [busy, setBusy] = useState(false);
  const routeParts = route.split('/');
  const routeSourceId = routeParts[0] === 'data' && routeParts[1] && routeParts[1] !== 'new' ? routeParts[1] : '';
  const isDetailPage = routeParts[0] === 'data' && Boolean(routeParts[1]);

  useEffect(() => {
    if (routeParts[1] === 'new') {
      resetSourceEditor();
    } else if (routeSourceId) {
      const source = dataSources.find((item) => item.id === routeSourceId);
      if (source && selectedSourceId !== source.id) loadSource(source);
    } else if (!selectedSourceId && dataSources.length) {
      loadSource(dataSources[0]);
    }
  }, [dataSources, route, routeSourceId, selectedSourceId]);

  useEffect(() => {
    const sourceMappings = mappings.filter((mapping) => mapping.data_source_id === selectedSourceId);
    if (!selectedMappingId && sourceMappings.length) loadMapping(sourceMappings[0]);
  }, [mappings, selectedMappingId, selectedSourceId]);

  const sourceMappings = mappings.filter((mapping) => mapping.data_source_id === selectedSourceId);
  const selectedSource = dataSources.find((source) => source.id === selectedSourceId);
  const selectedMapping = mappings.find((mapping) => mapping.id === selectedMappingId);
  const completedJobs = importJobs.filter((job) => job.status === 'completed').length;
  const dryRunJobs = importJobs.filter((job) => job.status === 'dry_run').length;
  const failedJobs = importJobs.filter((job) => job.status === 'failed').length;
  const importedCount = importJobs.reduce((sum, job) => sum + Number(job.imported_count || 0), 0);

  function parseJsonObject(value: string, label: string) {
    try {
      const parsed = JSON.parse(value || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object.`);
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : `Invalid ${label}.`);
    }
  }

  function parseRows() {
    try {
      const parsed = JSON.parse(rowsJson || '[]');
      if (!Array.isArray(parsed)) throw new Error('Rows must be a JSON array.');
      return parsed as Record<string, unknown>[];
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid rows JSON.');
    }
  }

  function loadSource(source: DataSourceRead) {
    setSelectedSourceId(source.id);
    setName(source.name);
    setSourceType(source.source_type);
    setStatusValue(source.status);
    setConfigJson(JSON.stringify(source.config || {}, null, 2));
    setValidation(null);
    setSchema(null);
    setStatus(`Loaded source: ${source.name}`);
  }

  function resetSourceEditor() {
    setSelectedSourceId('');
    setSelectedMappingId('');
    setName('ESP Manual Contact Source');
    setSourceType('manual');
    setStatusValue('draft');
    setConfigJson('{\n  "fields": ["email", "first_name", "last_name", "plan"],\n  "sample_rows": [\n    { "email": "sample@example.com", "first_name": "Sample", "last_name": "Contact", "plan": "trial" }\n  ]\n}');
    setMappingName('Contact import mapping');
    setMappingJson('{\n  "email": "email",\n  "first_name": "first_name",\n  "last_name": "last_name",\n  "source": "source",\n  "attributes": {\n    "plan": "plan"\n  }\n}');
    setValidation(null);
    setSchema(null);
    setStatus('Ready to create a new data source.');
  }

  function loadMapping(mapping: DataSourceMappingRead) {
    setSelectedMappingId(mapping.id);
    setMappingName(mapping.name);
    setMappingJson(JSON.stringify(mapping.mapping || {}, null, 2));
    setStatus(`Loaded mapping: ${mapping.name}`);
  }

  async function runDataOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    onOperation({ label: 'Data workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setStatus(message);
      onOperation({ label: 'Data workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'Data workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  async function saveSource() {
    await runDataOperation(selectedSourceId ? 'Saving data source' : 'Creating data source', async () => {
      const payload = {
        name: name.trim() || 'Untitled ESP Data Source',
        source_type: sourceType,
        status: statusValue,
        config: parseJsonObject(configJson, 'config'),
        secret_ref: null,
      };
      const saved = selectedSourceId
        ? await fetchJson<DataSourceRead>(`/api/v1/data-sources/${selectedSourceId}`, { method: 'PATCH', body: JSON.stringify(payload) })
        : await fetchJson<DataSourceRead>('/api/v1/data-sources', { method: 'POST', body: JSON.stringify(payload) });
      setSelectedSourceId(saved.id);
      window.location.hash = `#data/${saved.id}`;
      await onRefresh();
      return `Saved data source: ${saved.name}.`;
    });
  }

  async function validateSource() {
    await runDataOperation('Validating data source', async () => {
      if (!selectedSourceId) throw new Error('Save or select a data source first.');
      const data = await fetchJson<DataSourceValidationRead>(`/api/v1/data-sources/${selectedSourceId}/validate`, { method: 'POST' });
      setValidation(data);
      return data.ok ? `Validation passed: ${data.checks.join(', ') || 'checks complete'}.` : `Validation failed: ${data.errors.join(', ') || 'unknown issue'}.`;
    });
  }

  async function discoverSchema() {
    await runDataOperation('Discovering schema', async () => {
      if (!selectedSourceId) throw new Error('Save or select a data source first.');
      const data = await fetchJson<DataSourceSchemaRead>(`/api/v1/data-sources/${selectedSourceId}/schema`);
      setSchema(data);
      if (data.sample_rows?.length) setRowsJson(JSON.stringify(data.sample_rows.slice(0, 5), null, 2));
      return `Discovered ${formatInt(data.fields.length)} field(s) and ${formatInt(data.sample_rows.length)} sample row(s).`;
    });
  }

  async function saveMapping() {
    await runDataOperation(selectedMappingId ? 'Saving mapping' : 'Creating mapping', async () => {
      if (!selectedSourceId) throw new Error('Save or select a data source first.');
      const payload = {
        data_source_id: selectedSourceId,
        name: mappingName.trim() || 'Contact import mapping',
        object_type: 'contact',
        mapping: parseJsonObject(mappingJson, 'mapping'),
        extraction_plan: { source: 'esp_data_page' },
      };
      const saved = selectedMappingId
        ? await fetchJson<DataSourceMappingRead>(`/api/v1/data-source-mappings/${selectedMappingId}`, { method: 'PATCH', body: JSON.stringify(payload) })
        : await fetchJson<DataSourceMappingRead>('/api/v1/data-source-mappings', { method: 'POST', body: JSON.stringify(payload) });
      setSelectedMappingId(saved.id);
      await onRefresh();
      return `Saved mapping: ${saved.name}.`;
    });
  }

  async function ingestRows(dryRun: boolean) {
    await runDataOperation(dryRun ? 'Dry-running import' : 'Importing rows', async () => {
      if (!selectedSourceId) throw new Error('Select a data source.');
      if (!selectedMappingId) throw new Error('Select or create a mapping.');
      const job = await fetchJson<DataSourceImportJobRead>(`/api/v1/data-sources/${selectedSourceId}/ingest`, {
        method: 'POST',
        body: JSON.stringify({
          mapping_id: selectedMappingId,
          rows: parseRows(),
          dry_run: dryRun,
          metadata_json: { source: 'esp_data_page' },
        }),
      });
      await onRefresh();
      return `${dryRun ? 'Dry run' : 'Import'} ${job.status}: ${formatInt(job.imported_count)} imported, ${formatInt(job.skipped_count)} skipped.`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Sources', value: formatInt(dataSources.length), change: 'configured' }} />
          <MetricCard metric={{ label: 'Mappings', value: formatInt(mappings.length), change: 'field maps' }} />
          <MetricCard metric={{ label: 'Imported rows', value: formatInt(importedCount), change: `${formatInt(completedJobs)} completed jobs` }} />
          <MetricCard metric={{ label: 'Dry runs', value: formatInt(dryRunJobs), change: 'validation jobs' }} />
          <MetricCard metric={{ label: 'Failed jobs', value: formatInt(failedJobs), change: 'needs review', tone: failedJobs ? 'warn' : 'good' }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Data Sources</h2>
              <span className="muted">Select a source to review mappings, imports, and schema readiness.</span>
            </div>
            <a href="#data/new">New source</a>
          </div>
          {dataSources.length ? (
            <table>
              <thead><tr><th>Source</th><th>Type</th><th>Status</th><th>Mappings</th><th>Secret</th><th>Editor</th></tr></thead>
              <tbody>
                {dataSources.map((source) => (
                  <tr
                    className={`selectable-row ${source.id === selectedSourceId ? 'selected-row' : ''}`}
                    key={source.id}
                    onClick={() => loadSource(source)}
                  >
                    <td>{source.name}</td>
                    <td><span className="pill">{source.source_type}</span></td>
                    <td>{source.status}</td>
                    <td>{formatInt(mappings.filter((mapping) => mapping.data_source_id === source.id).length)}</td>
                    <td>{source.secret_ref || '-'}</td>
                    <td><a href={`#data/${source.id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No data sources" detail="Create a source to start importing contacts from CSV, manual rows, or external systems." actionHref="#data/new" actionLabel="Create source" />}
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Mappings</h2>
              <span className="muted">{selectedSource ? `Mappings for ${selectedSource.name}` : 'Select a source to filter mappings.'}</span>
            </div>
            {selectedSourceId ? <a href={`#data/${selectedSourceId}`}>Edit mappings</a> : <span className="muted">Select a source</span>}
          </div>
          {sourceMappings.length ? (
            <table>
              <thead><tr><th>Mapping</th><th>Object</th><th>Fields</th><th>Source</th></tr></thead>
              <tbody>
                {sourceMappings.map((mapping) => (
                  <tr
                    className={`selectable-row ${mapping.id === selectedMappingId ? 'selected-row' : ''}`}
                    key={mapping.id}
                    onClick={() => loadMapping(mapping)}
                  >
                    <td>{mapping.name}</td>
                    <td>{mapping.object_type}</td>
                    <td>{formatInt(Object.keys(mapping.mapping || {}).length)}</td>
                    <td>{selectedSource?.name || mapping.data_source_id.slice(0, 8)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No mappings for selected source" detail="Open a data source to create a contact import mapping." actionHref={selectedSourceId ? `#data/${selectedSourceId}` : '#data/new'} actionLabel="Open source" />}
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Import Jobs</h2>
              <span className="muted">{formatInt(importJobs.length)} visible</span>
            </div>
            <a href="#contacts">Open contacts</a>
          </div>
          {importJobs.length ? (
            <table>
              <thead><tr><th>Created</th><th>Status</th><th>Object</th><th>Received</th><th>Imported</th><th>Created</th><th>Updated</th><th>Skipped</th><th>Errors</th></tr></thead>
              <tbody>
                {importJobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.created_at}</td>
                    <td><span className="pill">{job.status}</span></td>
                    <td>{job.object_type}</td>
                    <td>{formatInt(job.received_count)}</td>
                    <td>{formatInt(job.imported_count)}</td>
                    <td>{formatInt(job.created_count)}</td>
                    <td>{formatInt(job.updated_count)}</td>
                    <td>{formatInt(job.skipped_count)}</td>
                    <td>{formatInt(job.errors?.length || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No import jobs" detail="Open a data source, save a mapping, then run a dry run or import rows." actionHref={selectedSourceId ? `#data/${selectedSourceId}` : '#data/new'} actionLabel="Open source" />}
        </section>
        {(selectedSource || selectedMapping || validation || schema) ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedSource?.name || 'Selected Data Context'}</h2>
                <span className="muted">Selected source and mapping summary</span>
              </div>
              <a href={selectedSourceId ? `#data/${selectedSourceId}` : '#data/new'}>Open data source</a>
            </div>
            <div className="summary-grid">
              <div><span>Source type</span><strong>{selectedSource?.source_type || '-'}</strong></div>
              <div><span>Source status</span><strong>{selectedSource?.status || '-'}</strong></div>
              <div><span>Mapping</span><strong>{selectedMapping?.name || '-'}</strong></div>
              <div><span>Validation</span><strong>{validation ? (validation.ok ? 'Passed' : 'Failed') : 'Not checked'}</strong></div>
              <div><span>Schema fields</span><strong>{schema ? formatInt(schema.fields.length) : 'Unknown'}</strong></div>
              <div><span>Sample rows</span><strong>{schema ? formatInt(schema.sample_rows.length) : 'Unknown'}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      {(selectedSource || selectedMapping || validation || schema) ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedSource?.name || 'New Data Source'}</h2>
              <span className="muted">Source, mapping, validation, and import workspace</span>
            </div>
            <a href="#data">Back to data sources</a>
          </div>
          <div className="summary-grid">
            <div><span>Source type</span><strong>{selectedSource?.source_type || sourceType}</strong></div>
            <div><span>Source status</span><strong>{selectedSource?.status || statusValue}</strong></div>
            <div><span>Mapping</span><strong>{selectedMapping?.name || 'Create or select'}</strong></div>
            <div><span>Validation</span><strong>{validation ? (validation.ok ? 'Passed' : 'Failed') : 'Not checked'}</strong></div>
            <div><span>Schema fields</span><strong>{schema ? formatInt(schema.fields.length) : 'Unknown'}</strong></div>
            <div><span>Sample rows</span><strong>{schema ? formatInt(schema.sample_rows.length) : 'Unknown'}</strong></div>
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>{selectedSource ? 'Data Operations' : 'Create Data Source'}</h2>
          <div className="button-row">
            <a href="#data">Back to data sources</a>
            <a href="#contacts">Open contacts</a>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Existing source
            <select value={selectedSourceId} onChange={(event) => {
              const source = dataSources.find((item) => item.id === event.target.value);
              if (source) {
                loadSource(source);
                window.location.hash = `#data/${source.id}`;
              } else {
                resetSourceEditor();
                window.location.hash = '#data/new';
              }
            }}>
              <option value="">Create new source</option>
              {dataSources.map((source) => <option value={source.id} key={source.id}>{source.name} ({source.source_type})</option>)}
            </select>
          </label>
          <label>
            Source name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value as DataSourceRead['source_type'])}>
              <option value="manual">Manual</option>
              <option value="csv">CSV</option>
              <option value="rest_api">REST API</option>
              <option value="postgres">Postgres</option>
              <option value="mysql">MySQL</option>
              <option value="snowflake">Snowflake</option>
              <option value="bigquery">BigQuery</option>
            </select>
          </label>
          <label>
            Status
            <select value={statusValue} onChange={(event) => setStatusValue(event.target.value as DataSourceRead['status'])}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </label>
          <label className="wide-field">
            Config JSON
            <textarea value={configJson} onChange={(event) => setConfigJson(event.target.value)} rows={8} />
          </label>
          <label>
            Existing mapping
            <select value={selectedMappingId} onChange={(event) => {
              const mapping = mappings.find((item) => item.id === event.target.value);
              if (mapping) loadMapping(mapping);
              else setSelectedMappingId('');
            }}>
              <option value="">Create new mapping</option>
              {sourceMappings.map((mapping) => <option value={mapping.id} key={mapping.id}>{mapping.name}</option>)}
            </select>
          </label>
          <label>
            Mapping name
            <input value={mappingName} onChange={(event) => setMappingName(event.target.value)} />
          </label>
          <label className="wide-field">
            Contact mapping JSON
            <textarea value={mappingJson} onChange={(event) => setMappingJson(event.target.value)} rows={8} />
          </label>
          <label>
            Import rows JSON
            <textarea value={rowsJson} onChange={(event) => setRowsJson(event.target.value)} rows={8} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveSource} disabled={busy}>Save Source</button>
          <button className="ghost" onClick={validateSource} disabled={busy || !selectedSourceId}>Validate</button>
          <button className="ghost" onClick={discoverSchema} disabled={busy || !selectedSourceId}>Discover Schema</button>
          <button className="ghost" onClick={saveMapping} disabled={busy || !selectedSourceId}>Save Mapping</button>
          <button className="ghost" onClick={() => ingestRows(true)} disabled={busy || !selectedSourceId || !selectedMappingId}>Dry Run</button>
          <button className="ghost" onClick={() => ingestRows(false)} disabled={busy || !selectedSourceId || !selectedMappingId}>Import Rows</button>
          <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
      {schema?.fields?.length ? (
        <section className="panel table-panel full-span">
          <div className="panel-head"><h2>Discovered Fields</h2><span className="muted">{formatInt(schema.fields.length)} fields</span></div>
          <table>
            <thead><tr><th>Field</th><th>Type</th><th>Samples</th></tr></thead>
            <tbody>
              {schema.fields.map((field) => (
                <tr key={field.name}><td>{field.name}</td><td>{field.field_type}</td><td>{field.sample_values.map((value) => String(value)).join(', ') || '-'}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </section>
  );
}

function ContactsPage({ contacts, metadata, route, onRefresh }: {
  contacts: ContactRead[];
  metadata: ContactMetadata | null;
  route: string;
  onRefresh: () => Promise<void>;
}) {
  const [selectedContactId, setSelectedContactId] = useState('');
  const [email, setEmail] = useState('new-contact@example.com');
  const [firstName, setFirstName] = useState('New');
  const [lastName, setLastName] = useState('Contact');
  const [source, setSource] = useState('esp_contacts');
  const [attributesJson, setAttributesJson] = useState('{\n  "plan": "trial",\n  "segment": "manual-test"\n}');
  const [isUnsubscribed, setIsUnsubscribed] = useState(false);
  const [unsubscribeToken, setUnsubscribeToken] = useState('');
  const [status, setStatus] = useState('Ready to inspect or edit contacts.');
  const [busy, setBusy] = useState(false);
  const routeParts = route.split('/');
  const routeContactId = routeParts[0] === 'contacts' && routeParts[1] && routeParts[1] !== 'new' ? routeParts[1] : '';
  const isDetailPage = routeParts[0] === 'contacts' && Boolean(routeParts[1]);

  useEffect(() => {
    if (routeParts[1] === 'new') {
      resetContactEditor();
    } else if (routeContactId) {
      const contact = contacts.find((item) => item.id === routeContactId);
      if (contact && selectedContactId !== contact.id) loadContact(contact);
    } else if (!selectedContactId && contacts.length) {
      loadContact(contacts[0]);
    }
  }, [contacts, route, routeContactId, selectedContactId]);

  const unsubscribedCount = contacts.filter((contact) => contact.is_unsubscribed).length;
  const attributedCount = contacts.filter((contact) => Object.keys(contact.attributes || {}).length).length;
  const uniqueSources = new Set(contacts.map((contact) => contact.source).filter(Boolean)).size;
  const selectedContact = contacts.find((contact) => contact.id === selectedContactId);
  const sourceRows = metadata?.sources || [];
  const attributeKeys = metadata?.attribute_keys || [];

  function parseAttributes() {
    try {
      const parsed = JSON.parse(attributesJson || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Attributes must be a JSON object.');
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid attributes JSON.');
    }
  }

  function loadContact(contact: ContactRead) {
    setSelectedContactId(contact.id);
    setEmail(contact.email);
    setFirstName(contact.first_name || '');
    setLastName(contact.last_name || '');
    setSource(contact.source || '');
    setAttributesJson(JSON.stringify(contact.attributes || {}, null, 2));
    setIsUnsubscribed(Boolean(contact.is_unsubscribed));
    setUnsubscribeToken('');
    setStatus(`Loaded contact: ${contact.email}`);
  }

  async function runContactOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    try {
      setStatus(await operation());
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function saveContact() {
    await runContactOperation(selectedContactId ? 'Saving contact' : 'Creating contact', async () => {
      const payload = {
        email: email.trim(),
        first_name: firstName || null,
        last_name: lastName || null,
        source: source || null,
        attributes: parseAttributes(),
      };
      if (!payload.email) throw new Error('Email is required.');
      const saved = selectedContactId
        ? await fetchJson<ContactRead>(`/api/v1/audiences/contacts/${selectedContactId}`, {
          method: 'PATCH',
          body: JSON.stringify({ ...payload, is_unsubscribed: isUnsubscribed }),
        })
        : await fetchJson<ContactRead>('/api/v1/audiences/contacts', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      setSelectedContactId(saved.id);
      window.location.hash = `#contacts/${saved.id}`;
      await onRefresh();
      return `Saved contact: ${saved.email}.`;
    });
  }

  function resetContactEditor() {
    setSelectedContactId('');
    setEmail('new-contact@example.com');
    setFirstName('New');
    setLastName('Contact');
    setSource('esp_contacts');
    setAttributesJson('{\n  "plan": "trial",\n  "segment": "manual-test"\n}');
    setIsUnsubscribed(false);
    setUnsubscribeToken('');
    setStatus('Ready to create a new contact.');
  }

  async function newContact() {
    resetContactEditor();
    window.location.hash = '#contacts/new';
  }

  async function deleteContact() {
    await runContactOperation('Deleting contact', async () => {
      if (!selectedContactId) throw new Error('Select a contact.');
      await fetchJson<{ id: string }>(`/api/v1/audiences/contacts/${selectedContactId}`, { method: 'DELETE' });
      const deletedEmail = selectedContact?.email || selectedContactId;
      await newContact();
      await onRefresh();
      return `Deleted contact: ${deletedEmail}.`;
    });
  }

  async function loadUnsubscribeToken() {
    await runContactOperation('Creating unsubscribe token', async () => {
      if (!selectedContactId) throw new Error('Select a contact.');
      const data = await fetchJson<{ contact_id: string; token: string }>(`/api/v1/audiences/contacts/${selectedContactId}/unsubscribe-token`, { method: 'POST' });
      setUnsubscribeToken(data.token);
      return `Generated unsubscribe token for ${selectedContact?.email || data.contact_id}.`;
    });
  }

  if (!isDetailPage) {
    return (
      <section className="page-grid">
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Contacts', value: formatInt(metadata?.total || contacts.length), change: `${formatInt(metadata?.scanned_count || contacts.length)} scanned` }} />
          <MetricCard metric={{ label: 'Visible', value: formatInt(contacts.length), change: 'loaded rows' }} />
          <MetricCard metric={{ label: 'Attributed', value: formatInt(attributedCount), change: `${formatInt(attributeKeys.length)} keys` }} />
          <MetricCard metric={{ label: 'Sources', value: formatInt(uniqueSources || sourceRows.length), change: 'source values' }} />
          <MetricCard metric={{ label: 'Unsubscribed', value: formatInt(unsubscribedCount), change: 'visible contacts', tone: unsubscribedCount ? 'warn' : 'good' }} />
        </section>
        <section className="panel table-panel full-span">
          <div className="panel-head">
            <div>
              <h2>Contacts</h2>
              <span className="muted">Select a contact to inspect attributes, then open it for profile and compliance edits.</span>
            </div>
            <div className="button-row">
              <a href="#contacts/new">Create contact</a>
              <a href="#data">Import contacts</a>
            </div>
          </div>
          {contacts.length ? (
            <table>
              <thead><tr><th>Email</th><th>Name</th><th>Source</th><th>Status</th><th>Attributes</th><th>Editor</th></tr></thead>
              <tbody>
                {contacts.map((contact) => (
                  <tr
                    className={`selectable-row ${contact.id === selectedContactId ? 'selected-row' : ''}`}
                    key={contact.id}
                    onClick={() => loadContact(contact)}
                  >
                    <td>{contact.email}</td>
                    <td>{[contact.first_name, contact.last_name].filter(Boolean).join(' ') || '-'}</td>
                    <td>{contact.source || '-'}</td>
                    <td><span className="pill">{contact.is_unsubscribed ? 'unsubscribed' : 'subscribed'}</span></td>
                    <td>{Object.keys(contact.attributes || {}).slice(0, 6).join(', ') || '-'}</td>
                    <td><a href={`#contacts/${contact.id}`} onClick={(event) => event.stopPropagation()}>Open</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No contacts" detail="Import contacts from the Data page or create one here." actionHref="#contacts/new" actionLabel="Create contact" />}
        </section>
        {selectedContact ? (
          <section className="panel full-span selected-summary">
            <div className="panel-head">
              <div>
                <h2>{selectedContact.email}</h2>
                <span className="muted">Selected contact summary</span>
              </div>
              <a href={`#contacts/${selectedContact.id}`}>Open contact editor</a>
            </div>
            <div className="summary-grid">
              <div><span>Name</span><strong>{[selectedContact.first_name, selectedContact.last_name].filter(Boolean).join(' ') || '-'}</strong></div>
              <div><span>Source</span><strong>{selectedContact.source || '-'}</strong></div>
              <div><span>Status</span><strong>{selectedContact.is_unsubscribed ? 'Unsubscribed' : 'Subscribed'}</strong></div>
              <div><span>Attributes</span><strong>{formatInt(Object.keys(selectedContact.attributes || {}).length)}</strong></div>
              <div><span>Top source</span><strong>{sourceRows[0]?.source || '-'}</strong></div>
              <div><span>Known keys</span><strong>{formatInt(attributeKeys.length)}</strong></div>
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  return (
    <section className="page-grid">
      {selectedContact ? (
        <section className="panel full-span selected-summary">
          <div className="panel-head">
            <div>
              <h2>{selectedContact.email}</h2>
              <span className="muted">Contact editor summary</span>
            </div>
            <a href="#contacts">Back to contacts</a>
          </div>
          <div className="summary-grid">
            <div><span>Name</span><strong>{[selectedContact.first_name, selectedContact.last_name].filter(Boolean).join(' ') || '-'}</strong></div>
            <div><span>Source</span><strong>{selectedContact.source || '-'}</strong></div>
            <div><span>Status</span><strong>{selectedContact.is_unsubscribed ? 'Unsubscribed' : 'Subscribed'}</strong></div>
            <div><span>Attributes</span><strong>{formatInt(Object.keys(selectedContact.attributes || {}).length)}</strong></div>
            <div><span>Top source</span><strong>{sourceRows[0]?.source || '-'}</strong></div>
            <div><span>Known keys</span><strong>{formatInt(attributeKeys.length)}</strong></div>
          </div>
        </section>
      ) : null}
      {attributeKeys.length ? (
        <section className="panel full-span">
          <div className="panel-head">
            <div>
              <h2>Attribute Fields</h2>
              <span className="muted">{formatInt(attributeKeys.length)} keys available for audience rules and template variables.</span>
            </div>
            <a href="#templates">Open templates</a>
          </div>
          <div className="button-row">
            {attributeKeys.slice(0, 24).map((key) => <button className="ghost" key={key} onClick={() => setAttributesJson(JSON.stringify({ ...parseAttributes(), [key]: `sample ${key}` }, null, 2))}>{key}</button>)}
          </div>
        </section>
      ) : null}
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>{selectedContact ? 'Contact Operations' : 'Create Contact'}</h2>
          <div className="button-row">
            <a href="#contacts">Back to contacts</a>
            <a href="#compliance">Open compliance</a>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Existing contact
            <select value={selectedContactId} onChange={(event) => {
              const contact = contacts.find((item) => item.id === event.target.value);
              if (contact) {
                loadContact(contact);
                window.location.hash = `#contacts/${contact.id}`;
              } else {
                resetContactEditor();
                window.location.hash = '#contacts/new';
              }
            }}>
              <option value="">Create new contact</option>
              {contacts.map((contact) => <option value={contact.id} key={contact.id}>{contact.email}</option>)}
            </select>
          </label>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            First name
            <input value={firstName} onChange={(event) => setFirstName(event.target.value)} />
          </label>
          <label>
            Last name
            <input value={lastName} onChange={(event) => setLastName(event.target.value)} />
          </label>
          <label>
            Source
            <input value={source} onChange={(event) => setSource(event.target.value)} />
          </label>
          <label>
            Unsubscribed
            <select value={isUnsubscribed ? 'true' : 'false'} onChange={(event) => setIsUnsubscribed(event.target.value === 'true')}>
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </label>
          <label className="wide-field">
            Attributes JSON
            <textarea value={attributesJson} onChange={(event) => setAttributesJson(event.target.value)} rows={8} />
          </label>
          <label>
            Unsubscribe token
            <textarea value={unsubscribeToken || 'Not generated'} readOnly rows={8} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveContact} disabled={busy}>Save Contact</button>
          <button className="ghost" onClick={newContact} disabled={busy}>New Contact</button>
          <button className="ghost" onClick={loadUnsubscribeToken} disabled={busy || !selectedContactId}>Unsubscribe Token</button>
          <button className="ghost" onClick={deleteContact} disabled={busy || !selectedContactId}>Delete Contact</button>
          <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
    </section>
  );
}

function AnalyticsPage({ overview, campaigns, campaignItems, audiences, journeys, onRefresh, onOperation }: {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  campaignItems: CampaignRead[];
  audiences: AudiencePerformance[];
  journeys: JourneyPerformance[];
  onRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('Select a campaign to load detailed reporting.');
  const [campaignDetail, setCampaignDetail] = useState<CampaignAnalytics | null>(null);
  const [timeline, setTimeline] = useState<CampaignTimelinePoint[]>([]);
  const [domains, setDomains] = useState<DomainDeliverability[]>([]);

  useEffect(() => {
    if (!selectedCampaignId && campaignItems.length) setSelectedCampaignId(campaignItems[0].id);
  }, [campaignItems, selectedCampaignId]);

  const totalSent = campaigns.reduce((sum, item) => sum + Number(item.sent_count || 0), 0);
  const totalOpens = campaigns.reduce((sum, item) => sum + Number(item.opened_count || 0), 0);
  const totalClicks = campaigns.reduce((sum, item) => sum + Number(item.clicked_count || 0), 0);
  const totalAudienceReach = audiences.reduce((sum, item) => sum + Number(item.estimated_count || 0), 0);
  const activeEnrollments = journeys.reduce((sum, item) => sum + Number(item.active_count || 0), 0);
  const topCampaigns = [...campaigns].sort((a, b) => Number(b.open_rate || 0) - Number(a.open_rate || 0)).slice(0, 5);
  const topAudiences = [...audiences].sort((a, b) => Number(b.open_rate || 0) - Number(a.open_rate || 0)).slice(0, 5);
  const journeyRisks = [...journeys].sort((a, b) => {
    const bFailures = Number(b.failed_count || 0) + Number(b.step_failed_count || 0);
    const aFailures = Number(a.failed_count || 0) + Number(a.step_failed_count || 0);
    return bFailures - aFailures;
  }).slice(0, 5);
  const selectedCampaign = campaignItems.find((item) => item.id === selectedCampaignId);
  const maxTimelineSent = Math.max(...timeline.map((point) => Number(point.sent_count || 0)), 1);
  const statusRows = overview?.status_counts || [];
  const eventRows = overview?.event_counts || [];
  const maxStatusCount = Math.max(...statusRows.map((row) => Number(row.count || 0)), 1);
  const maxEventCount = Math.max(...eventRows.map((row) => Number(row.count || 0)), 1);
  const selectedCampaignPerformance = campaigns.find((item) => item.campaign_id === selectedCampaignId);
  const rateRows = topCampaigns.map((campaign) => ({
    name: campaign.name,
    openRate: Number(campaign.open_rate || 0),
    clickRate: Number(campaign.click_rate || 0),
    failureRate: Number(campaign.failed_count || 0) / Math.max(Number(campaign.requested_count || campaign.sent_count || 0), 1),
  }));
  const maxRate = Math.max(...rateRows.flatMap((row) => [row.openRate, row.clickRate, row.failureRate]), 0.01);

  async function loadReport() {
    setBusy(true);
    setStatus('Loading report...');
    onOperation({ label: 'Optimization workflow', message: 'Loading campaign report...', tone: 'working' });
    try {
      await onRefresh();
      if (!selectedCampaignId) {
        const message = 'No campaign selected.';
        setStatus(message);
        onOperation({ label: 'Optimization workflow', message, tone: 'warn' });
        return;
      }
      const [detail, timelineData, domainData] = await Promise.all([
        fetchJson<CampaignAnalytics>(`/api/v1/campaigns/${selectedCampaignId}/analytics`),
        fetchJson<{ points: CampaignTimelinePoint[] }>(`/api/v1/campaigns/${selectedCampaignId}/analytics/timeline?days=${days}`),
        fetchJson<ListResponse<DomainDeliverability>>(`/api/v1/analytics/domains?limit=10&offset=0&campaign_id=${selectedCampaignId}`),
      ]);
      setCampaignDetail(detail);
      setTimeline(timelineData.points || []);
      setDomains(domainData.items || []);
      const message = `Loaded report for ${selectedCampaign?.name || selectedCampaignId}.`;
      setStatus(message);
      onOperation({ label: 'Optimization workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'Optimization workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        {metricsFromOverview(overview).map((metric) => <MetricCard metric={metric} key={metric.label} />)}
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Campaign Performance</h2><a href="#campaigns">Manage campaigns</a></div>
        {topCampaigns.length ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Status</th>
                  <th>Sent</th>
                  <th>Open rate</th>
                  <th>Click rate</th>
                  <th>Failures</th>
                </tr>
              </thead>
              <tbody>
                {topCampaigns.map((campaign) => (
                  <tr
                    className={`selectable-row ${selectedCampaignId === campaign.campaign_id ? 'selected-row' : ''}`}
                    key={campaign.campaign_id}
                    onClick={() => setSelectedCampaignId(campaign.campaign_id)}
                  >
                    <td>{campaign.name}</td>
                    <td><span className="pill">{campaign.status}</span></td>
                    <td>{formatInt(campaign.sent_count)}</td>
                    <td>{formatPct(campaign.open_rate)}</td>
                    <td>{formatPct(campaign.click_rate)}</td>
                    <td>{formatInt(campaign.failed_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="selected-summary">
              <div>
                <span>Selected campaign</span>
                <strong>{selectedCampaignPerformance?.name || selectedCampaign?.name || 'Select a campaign'}</strong>
              </div>
              <div>
                <span>Engagement</span>
                <strong>{formatPct((selectedCampaignPerformance?.open_rate ?? totalOpens / Math.max(totalSent, 1)) || 0)}</strong>
              </div>
              <div>
                <span>Clicks</span>
                <strong>{formatPct((selectedCampaignPerformance?.click_rate ?? totalClicks / Math.max(totalSent, 1)) || 0)}</strong>
              </div>
              <div>
                <span>Next step</span>
                <strong>Load detail report</strong>
              </div>
            </div>
          </>
        ) : (
          <EmptyState title="No campaign analytics yet" detail="Launch a test campaign to populate campaign comparison reports." actionHref="#campaigns" actionLabel="Open Campaigns" />
        )}
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>Reporting Controls</h2>
          <a href="#analytics">Open reports</a>
        </div>
        <div className="form-grid">
          <label>
            Campaign
            <select value={selectedCampaignId} onChange={(event) => setSelectedCampaignId(event.target.value)}>
              <option value="">Select campaign</option>
              {campaignItems.map((campaign) => (
                <option value={campaign.id} key={campaign.id}>{campaign.name} ({campaign.status})</option>
              ))}
            </select>
          </label>
          <label>
            Timeline days
            <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
          <label>
            Campaign status
            <input value={selectedCampaign?.status || 'No campaign selected'} readOnly />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={loadReport} disabled={busy || !selectedCampaignId}>Load Report</button>
          <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh Summary</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
      <section className="panel full-span">
        <div className="panel-head"><h2>Pipeline Status</h2><span className="muted">{formatInt(statusRows.length)} statuses</span></div>
        {statusRows.length ? (
          <div className="timeline-bars">
            {statusRows.map((row) => (
              <article className="timeline-row" key={row.name}>
                <span>{row.name}</span>
                <div className="timeline-track">
                  <i style={{ width: `${Math.max(4, (Number(row.count || 0) / maxStatusCount) * 100)}%` }} />
                </div>
                <strong>{formatInt(row.count)}</strong>
                <small>{formatPct(Number(row.count || 0) / Math.max(overview?.send_record_count || 0, 1))} of records</small>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No send statuses yet" detail="Launch a campaign or process queued delivery records to populate pipeline status." actionHref="#campaigns" actionLabel="Open Campaigns" />
        )}
      </section>
      <section className="panel full-span">
        <div className="panel-head"><h2>Event Mix</h2><span className="muted">{formatInt(overview?.event_count || 0)} events</span></div>
        {eventRows.length ? (
          <div className="timeline-bars">
            {eventRows.map((row) => (
              <article className="timeline-row" key={row.name}>
                <span>{row.name}</span>
                <div className="timeline-track">
                  <i style={{ width: `${Math.max(4, (Number(row.count || 0) / maxEventCount) * 100)}%` }} />
                </div>
                <strong>{formatInt(row.count)}</strong>
                <small>{formatPct(Number(row.count || 0) / Math.max(overview?.event_count || 0, 1))} of events</small>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No events yet" detail="Open and click tracking events appear here after messages are sent and interacted with." actionHref="#delivery" actionLabel="Open Delivery" />
        )}
      </section>
      {rateRows.length ? (
        <section className="panel full-span">
          <div className="panel-head"><h2>Campaign Rate Comparison</h2><a href="#campaigns">Manage campaigns</a></div>
          <div className="timeline-bars">
            {rateRows.map((row) => (
              <article className="timeline-row" key={row.name}>
                <span>{row.name}</span>
                <div className="timeline-track">
                  <i style={{ width: `${Math.max(4, (row.openRate / maxRate) * 100)}%` }} />
                </div>
                <strong>{formatPct(row.openRate)}</strong>
                <small>{formatPct(row.clickRate)} click / {formatPct(row.failureRate)} failed</small>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {campaignDetail ? (
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Selected sent', value: formatInt(campaignDetail.sent_count), change: `${formatInt(campaignDetail.delivered_count)} delivered` }} />
          <MetricCard metric={{ label: 'Selected open rate', value: formatPct(campaignDetail.open_rate), change: `${formatInt(campaignDetail.opened_count)} opens` }} />
          <MetricCard metric={{ label: 'Selected click rate', value: formatPct(campaignDetail.click_rate), change: `${formatInt(campaignDetail.clicked_count)} clicks` }} />
          <MetricCard metric={{ label: 'Selected bounces', value: formatInt(campaignDetail.bounced_count), change: formatPct(campaignDetail.bounce_rate), tone: campaignDetail.bounced_count ? 'warn' : 'good' }} />
        </section>
      ) : null}
      {timeline.length ? (
        <section className="panel full-span">
          <div className="panel-head"><h2>Campaign Timeline</h2><span className="muted">{formatInt(timeline.length)} points</span></div>
          <div className="timeline-bars">
            {timeline.map((point) => (
              <article className="timeline-row" key={point.date}>
                <span>{point.date}</span>
                <div className="timeline-track">
                  <i style={{ width: `${Math.max(4, (Number(point.sent_count || 0) / maxTimelineSent) * 100)}%` }} />
                </div>
                <strong>{formatInt(point.sent_count)}</strong>
                <small>{formatPct(point.open_rate)} open / {formatPct(point.click_rate)} click</small>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {domains.length ? (
        <section className="panel table-panel full-span">
          <div className="panel-head"><h2>Domain Deliverability</h2><a href="#analytics">Open analytics</a></div>
          <table>
            <thead><tr><th>Domain</th><th>Provider</th><th>Sends</th><th>Open</th><th>Click</th><th>Bounce</th></tr></thead>
            <tbody>
              {domains.map((domain) => (
                <tr key={`${domain.domain}-${domain.provider || 'provider'}`}>
                  <td>{domain.domain}</td>
                  <td>{providerLabel(domain.provider)}</td>
                  <td>{formatInt(domain.send_record_count)}</td>
                  <td>{formatPct(domain.open_rate)}</td>
                  <td>{formatPct(domain.click_rate)}</td>
                  <td>{formatPct(domain.bounce_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Campaign Performance</h2><a href="#analytics">Open analytics</a></div>
        <p className="large-number">{formatInt(totalSent)}</p>
        <span className="muted">sent across {formatInt(campaigns.length)} campaigns</span>
      </section>
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Audience Reach</h2><a href="#audience">Open audiences</a></div>
        <p className="large-number">{formatInt(totalAudienceReach)}</p>
        <span className="muted">estimated contacts across saved audiences</span>
      </section>
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Journey Health</h2><a href="#automations">Open journeys</a></div>
        <p className="large-number">{formatInt(activeEnrollments)}</p>
        <span className="muted">active journey enrollments</span>
      </section>
      <section className="panel table-panel">
        <div className="panel-head"><h2>Audience Comparison</h2><a href="#audience">Open audiences</a></div>
        {topAudiences.length ? (
          <table>
            <thead>
              <tr>
                <th>Audience</th>
                <th>Reach</th>
                <th>Open</th>
                <th>Click</th>
              </tr>
            </thead>
            <tbody>
              {topAudiences.map((audience) => (
                <tr key={audience.audience_id}>
                  <td>{audience.name}</td>
                  <td>{formatInt(audience.estimated_count)}</td>
                  <td>{formatPct(audience.open_rate)}</td>
                  <td>{formatPct(audience.click_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No audience data yet" detail="Create audiences to compare reach and engagement." actionHref="/admin/audiences" actionLabel="Open Audience Builder" />
        )}
      </section>
      <section className="panel table-panel">
        <div className="panel-head"><h2>Journey Risk</h2><a href="#automations">Open journeys</a></div>
        {journeyRisks.length ? (
          <table>
            <thead>
              <tr>
                <th>Journey</th>
                <th>Active</th>
                <th>Failures</th>
                <th>Queued</th>
              </tr>
            </thead>
            <tbody>
              {journeyRisks.map((journey) => (
                <tr key={journey.journey_id}>
                  <td>{journey.name}</td>
                  <td>{formatInt(journey.active_count)}</td>
                  <td>{formatInt(Number(journey.failed_count || 0) + Number(journey.step_failed_count || 0))}</td>
                  <td>{formatInt(journey.queued_send_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No journey data yet" detail="Build a journey to add automation reporting." actionHref="/admin/journeys" actionLabel="Open Journey Manager" />
        )}
      </section>
    </section>
  );
}

function AiStudioPage({ insights, diagnostics, dashboard, onTemplatesRefresh, onOperation }: {
  insights: Insight[];
  diagnostics: SystemDiagnostics | null;
  dashboard: DashboardState;
  onTemplatesRefresh: () => Promise<void>;
  onOperation: (notice: OperationNotice) => void;
}) {
  const openAiReady = Boolean(diagnostics?.ai.openai_configured);
  const provider = diagnostics?.ai.provider || 'auto';
  const model = diagnostics?.ai.model || 'configured model';
  const [brief, setBrief] = useState('Create a polished ecommerce email for a spring sale with personalized greeting, plan-aware conditional copy, recommendations loop, tracking open, tracking click, and unsubscribe link.');
  const [instruction, setInstruction] = useState('Make the copy more concise, add a clearer CTA, and preserve all Jinja variables.');
  const [subject, setSubject] = useState('Hello {{ first_name }}');
  const [htmlBody, setHtmlBody] = useState('<p>Hello {{ first_name }},</p>\n<p>We have a new offer for you.</p>\n{{ tracking_open }}\n<p><a href="{{ tracking_click }}">Shop now</a></p>\n<p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>');
  const [cssBody, setCssBody] = useState('.button { background: #2563eb; color: #ffffff; padding: 12px 16px; }');
  const [sampleJson, setSampleJson] = useState('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Spring bundle", "Limited offer"]\n}');
  const [status, setStatus] = useState('Ready to run an AI template workflow.');
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState<string[]>([]);
  const [recommendations, setRecommendations] = useState<AITemplateRecommendation[]>([]);
  const [workflowRecommendations, setWorkflowRecommendations] = useState<AIWorkflowRecommendation[]>([]);
  const [workflowSummary, setWorkflowSummary] = useState<string[]>([]);
  const [previewHtml, setPreviewHtml] = useState('');

  function parsedSample() {
    try {
      const parsed = JSON.parse(sampleJson || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Sample data must be a JSON object.');
      return parsed as Record<string, unknown>;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Invalid sample JSON.');
    }
  }

  async function runAiOperation(label: string, operation: () => Promise<string>) {
    setBusy(true);
    setStatus(`${label}...`);
    onOperation({ label: 'AI workflow', message: `${label}...`, tone: 'working' });
    try {
      const message = await operation();
      setStatus(message);
      onOperation({ label: 'AI workflow', message, tone: 'success' });
    } catch (error) {
      const message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setStatus(message);
      onOperation({ label: 'AI workflow', message, tone: 'warn' });
    } finally {
      setBusy(false);
    }
  }

  function applyDraft(draft: AITemplateDraft) {
    setSubject(draft.subject || subject);
    setHtmlBody(draft.html_body || htmlBody);
    setCssBody(draft.css_body || '');
    if (draft.sample_variables && Object.keys(draft.sample_variables).length) {
      setSampleJson(JSON.stringify(draft.sample_variables, null, 2));
    }
    setNotes(draft.notes || []);
  }

  async function draftTemplate() {
    await runAiOperation('Drafting template', async () => {
      const draft = await fetchJson<AITemplateDraft>('/api/v1/ai/templates/draft', {
        method: 'POST',
        body: JSON.stringify({
          brief,
          brand: { product: 'Email Engine ESP', tone: 'clear, direct, useful' },
          required_variables: ['first_name', 'tracking_open', 'tracking_click', 'unsubscribe_url'],
        }),
      });
      applyDraft(draft);
      return `Drafted template with ${draft.provider}/${draft.model}.`;
    });
  }

  async function editTemplate() {
    await runAiOperation('Editing template', async () => {
      const draft = await fetchJson<AITemplateDraft>('/api/v1/ai/templates/edit', {
        method: 'POST',
        body: JSON.stringify({
          instruction,
          current_subject: subject,
          current_html: htmlBody,
          current_css: cssBody || null,
          sample_variables: parsedSample(),
        }),
      });
      applyDraft(draft);
      return `Edited template. ${(draft.change_summary || draft.notes || []).slice(0, 2).join(' ')}`;
    });
  }

  async function recommendTemplate() {
    await runAiOperation('Loading recommendations', async () => {
      const data = await fetchJson<{ recommendations: AITemplateRecommendation[]; sample_variables: Record<string, unknown>; summary: string[] }>('/api/v1/ai/templates/recommend', {
        method: 'POST',
        body: JSON.stringify({
          current_subject: subject,
          current_html: htmlBody,
          current_css: cssBody || null,
          sample_variables: parsedSample(),
          goals: ['Improve engagement', 'Preserve dynamic variables', 'Improve deliverability readiness'],
        }),
      });
      setRecommendations(data.recommendations || []);
      if (data.sample_variables && Object.keys(data.sample_variables).length) setSampleJson(JSON.stringify(data.sample_variables, null, 2));
      return `Loaded ${formatInt(data.recommendations?.length || 0)} recommendation(s).`;
    });
  }

  async function previewTemplate() {
    await runAiOperation('Rendering preview', async () => {
      const data = await fetchJson<{ subject: string; html_body: string; errors: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({ subject, html_body: htmlBody, css_body: cssBody || null, variables: parsedSample() }),
      });
      setPreviewHtml(data.html_body || '');
      return `Rendered preview: ${data.subject}${data.errors?.length ? ` (${data.errors.join('; ')})` : ''}`;
    });
  }

  async function saveAsTemplate() {
    await runAiOperation('Saving template', async () => {
      const saved = await fetchJson<TemplateRead>('/api/v1/templates', {
        method: 'POST',
        body: JSON.stringify({
          name: `AI ESP Template ${new Date().toISOString().slice(0, 16)}`,
          subject,
          html_body: htmlBody,
          css_body: cssBody || null,
          text_body: null,
        }),
      });
      await onTemplatesRefresh();
      return `Saved template: ${saved.name}`;
    });
  }

  function workflowContext() {
    return {
      overview: dashboard.overview,
      campaigns: dashboard.campaigns.slice(0, 10),
      campaign_items: dashboard.campaignItems.slice(0, 10),
      audiences: dashboard.audiences.slice(0, 10),
      audience_items: dashboard.audienceItems.slice(0, 10),
      templates: dashboard.templates.slice(0, 10),
      send_jobs: dashboard.sendJobs.slice(0, 10),
      send_records: dashboard.sendRecords.slice(0, 10),
      suppressions: dashboard.suppressions.slice(0, 10),
      journeys: dashboard.journeys.slice(0, 10),
      journey_items: dashboard.journeyItems.slice(0, 10),
      journey_enrollments: dashboard.journeyEnrollments.slice(0, 10),
      journey_executions: dashboard.journeyExecutions.slice(0, 10),
      contacts: dashboard.contacts.slice(0, 10),
      contact_meta: dashboard.contactMeta,
      diagnostics,
    };
  }

  function normalizeWorkflowRecommendations(area: string, data: AIWorkflowAnalysis) {
    return (data.recommendations || []).map((item) => ({
      area,
      code: item.code,
      category: item.category,
      priority: item.priority,
      title: item.title,
      detail: item.detail,
      suggested_action: item.suggested_action || item.suggested_instruction || 'Review recommendation.',
      confidence: item.confidence,
    }));
  }

  async function reviewWorkflow() {
    await runAiOperation('Reviewing ESP workflow', async () => {
      const context = workflowContext();
      const goals = [
        'Identify launch blockers',
        'Find delivery and compliance risks',
        'Recommend the next best operator action',
      ];
      const [analytics, campaign, audience, delivery, journey] = await Promise.all([
        fetchJson<AIWorkflowAnalysis>('/api/v1/ai/analytics/analyze', {
          method: 'POST',
          body: JSON.stringify({ report_type: 'esp_workflow', report_context: context, goals }),
        }),
        fetchJson<AIWorkflowAnalysis>('/api/v1/ai/campaigns/analyze', {
          method: 'POST',
          body: JSON.stringify({ campaign_context: context, goals }),
        }),
        fetchJson<AIWorkflowAnalysis>('/api/v1/ai/audiences/analyze', {
          method: 'POST',
          body: JSON.stringify({ audience_context: context, goals }),
        }),
        fetchJson<AIWorkflowAnalysis>('/api/v1/ai/delivery/analyze', {
          method: 'POST',
          body: JSON.stringify({ delivery_context: context, goals }),
        }),
        fetchJson<AIWorkflowAnalysis>('/api/v1/ai/journeys/analyze', {
          method: 'POST',
          body: JSON.stringify({ journey_context: context, goals }),
        }),
      ]);
      const allRecommendations = [
        ...normalizeWorkflowRecommendations('Analytics', analytics),
        ...normalizeWorkflowRecommendations('Campaign', campaign),
        ...normalizeWorkflowRecommendations('Audience', audience),
        ...normalizeWorkflowRecommendations('Delivery', delivery),
        ...normalizeWorkflowRecommendations('Journey', journey),
      ].sort((a, b) => {
        const weight = { high: 3, medium: 2, low: 1 } as Record<string, number>;
        return (weight[b.priority] || 0) - (weight[a.priority] || 0);
      });
      setWorkflowSummary([
        ...(analytics.summary || []),
        ...(campaign.summary || []),
        ...(audience.summary || []),
        ...(delivery.summary || []),
        ...(journey.summary || []),
      ].slice(0, 6));
      setWorkflowRecommendations(allRecommendations);
      return `Workflow review loaded ${formatInt(allRecommendations.length)} recommendation(s).`;
    });
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'AI provider', value: provider, change: openAiReady ? 'OpenAI configured' : 'deterministic fallback', tone: openAiReady ? 'good' : 'warn' }} />
        <MetricCard metric={{ label: 'Model', value: model, change: 'template and analytics AI' }} />
        <MetricCard metric={{ label: 'Recommendations', value: formatInt(insights.length), change: 'current insights' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Content</span>
          <strong>Template builder</strong>
          <p>Draft templates from a prompt, modify existing HTML/Jinja, and preserve variables for preview and sending.</p>
          <a href="#templates">Open Template AI</a>
        </article>
        <article className="workflow-card">
          <span>Campaigns</span>
          <strong>Launch review</strong>
          <p>Assess template, audience, delivery, and readiness risks before sending a campaign.</p>
          <a href="#campaigns">Review campaigns</a>
        </article>
        <article className="workflow-card">
          <span>Audience</span>
          <strong>Targeting recommendations</strong>
          <p>Find missing fields, narrow segments, and targeting opportunities from audience data.</p>
          <a href="#audience">Review audiences</a>
        </article>
        <article className="workflow-card">
          <span>Performance</span>
          <strong>Analytics analysis</strong>
          <p>Generate next-best actions from campaign, audience, journey, and delivery signals.</p>
          <a href="#analytics">Analyze performance</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head"><h2>AI Template Builder</h2><a href="#templates">Open editor</a></div>
        <div className="form-grid">
          <label className="wide-field">
            Prompt
            <textarea value={brief} onChange={(event) => setBrief(event.target.value)} rows={5} />
          </label>
          <label>
            Edit instruction
            <textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} rows={5} />
          </label>
          <label>
            Subject
            <input value={subject} onChange={(event) => setSubject(event.target.value)} />
          </label>
          <label className="wide-field">
            HTML / Jinja
            <textarea value={htmlBody} onChange={(event) => setHtmlBody(event.target.value)} rows={10} />
          </label>
          <label>
            Sample data JSON
            <textarea value={sampleJson} onChange={(event) => setSampleJson(event.target.value)} rows={10} />
          </label>
          <label className="wide-field">
            CSS
            <textarea value={cssBody} onChange={(event) => setCssBody(event.target.value)} rows={5} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={draftTemplate} disabled={busy}>Draft</button>
          <button className="ghost" onClick={editTemplate} disabled={busy}>Modify</button>
          <button className="ghost" onClick={recommendTemplate} disabled={busy}>Recommendations</button>
          <button className="ghost" onClick={previewTemplate} disabled={busy}>Preview</button>
          <button className="ghost" onClick={saveAsTemplate} disabled={busy}>Save as Template</button>
          <button className="ghost" onClick={reviewWorkflow} disabled={busy}>Review Workflow</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {notes.length ? <small>{notes.slice(0, 2).join(' ')}</small> : null}
        </div>
        {previewHtml ? <iframe className="email-preview" title="AI template preview" srcDoc={previewHtml} /> : null}
      </section>
      {recommendations.length ? (
        <section className="panel table-panel full-span">
          <div className="panel-head"><h2>Template Recommendations</h2><span className="muted">{formatInt(recommendations.length)} items</span></div>
          <table>
            <thead><tr><th>Priority</th><th>Title</th><th>Detail</th><th>Suggested instruction</th></tr></thead>
            <tbody>
              {recommendations.map((item) => (
                <tr key={item.code}>
                  <td><span className="pill">{item.priority}</span></td>
                  <td>{item.title}</td>
                  <td>{item.detail}</td>
                  <td>{item.suggested_instruction}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
      {workflowRecommendations.length ? (
        <section className="panel table-panel full-span">
          <div className="panel-head"><h2>AI Workflow Review</h2><span className="muted">{formatInt(workflowRecommendations.length)} recommendations</span></div>
          {workflowSummary.length ? (
            <div className="insights">
              {workflowSummary.slice(0, 3).map((item) => (
                <article className="insight" key={item}>
                  <Icon label="Summary" />
                  <div><strong>Summary</strong><p>{item}</p></div>
                </article>
              ))}
            </div>
          ) : null}
          <table>
            <thead><tr><th>Area</th><th>Priority</th><th>Title</th><th>Detail</th><th>Suggested action</th></tr></thead>
            <tbody>
              {workflowRecommendations.map((item) => (
                <tr key={`${item.area}-${item.code}`}>
                  <td>{item.area}</td>
                  <td><span className="pill">{item.priority}</span></td>
                  <td>{item.title}</td>
                  <td>{item.detail}</td>
                  <td>{item.suggested_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
      <section className="panel full-span">
        <div className="panel-head"><h2>AI Insights</h2><a href="#analytics">Open analytics</a></div>
        <div className="insights">
          {insights.map((item) => (
            <article className={`insight ${item.tone || ''}`} key={item.title}>
              <Icon label={item.title} />
              <div><strong>{item.title}</strong><p>{item.detail}</p><button className="link-button">{item.action}</button></div>
            </article>
          ))}
        </div>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Available AI Endpoints</h2><a href="/docs">API docs</a></div>
        <table>
          <thead>
            <tr><th>Capability</th><th>Endpoint</th><th>Workbench</th></tr>
          </thead>
          <tbody>
            <tr><td>Draft template</td><td>/api/v1/ai/templates/draft</td><td><a href="#templates">Template Editor</a></td></tr>
            <tr><td>Edit template</td><td>/api/v1/ai/templates/edit</td><td><a href="#templates">Template Editor</a></td></tr>
            <tr><td>Campaign review</td><td>/api/v1/ai/campaigns/analyze</td><td><a href="#campaigns">Campaign Manager</a></td></tr>
            <tr><td>Audience review</td><td>/api/v1/ai/audiences/analyze</td><td><a href="#audience">Audience Builder</a></td></tr>
            <tr><td>Journey review</td><td>/api/v1/ai/journeys/analyze</td><td><a href="#automations">Journey Manager</a></td></tr>
            <tr><td>Delivery review</td><td>/api/v1/ai/delivery/analyze</td><td><a href="#delivery">Delivery Manager</a></td></tr>
          </tbody>
        </table>
      </section>
    </section>
  );
}

function IntegrationsPage({ diagnostics, onRefresh }: {
  diagnostics: SystemDiagnostics | null;
  onRefresh: () => Promise<void>;
}) {
  const [status, setStatus] = useState('Diagnostics loaded from system API.');
  const [busy, setBusy] = useState(false);
  const emailProvider = diagnostics?.email_provider.provider || 'unknown';
  const smtpReady = Boolean(diagnostics?.email_provider.smtp_configured);
  const sgReady = Boolean(diagnostics?.email_provider.sendgrid_configured);
  const baseUrl = diagnostics?.public_base_url || 'not configured';
  const tables = diagnostics?.database_tables || [];
  const counts = Object.entries(diagnostics?.entity_counts || {}).sort((a, b) => b[1] - a[1]);

  async function refreshDiagnostics() {
    setBusy(true);
    setStatus('Refreshing diagnostics...');
    try {
      await onRefresh();
      setStatus('Diagnostics refreshed.');
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Email provider', value: emailProvider, change: smtpReady ? 'SMTP configured' : sgReady ? 'SG configured' : 'console or pending', tone: smtpReady || sgReady || emailProvider === 'console' ? 'good' : 'warn' }} />
        <MetricCard metric={{ label: 'Public URL', value: baseUrl.replace(/^https?:\/\//, ''), change: 'tracking and unsubscribe base' }} />
        <MetricCard metric={{ label: 'Database tables', value: formatInt(diagnostics?.database_tables.length || 0), change: 'schema inventory' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Data</span>
          <strong>Data sources</strong>
          <p>Configure heterogeneous imports, preview mappings, and ingest source rows into contacts.</p>
          <a href="#data">Open Data Sources</a>
        </article>
        <article className="workflow-card">
          <span>Email</span>
          <strong>Provider readiness</strong>
          <p>Track SMTP and SG readiness without coupling the product workflow to one outbound provider.</p>
          <a href="#settings">Open diagnostics</a>
        </article>
        <article className="workflow-card">
          <span>Tracking</span>
          <strong>Domains and events</strong>
          <p>Review domain deliverability, opens, clicks, unsubscribes, and webhook event ingestion.</p>
          <a href="#analytics">Open reports</a>
        </article>
        <article className="workflow-card">
          <span>Developer</span>
          <strong>API surface</strong>
          <p>Use OpenAPI docs to align SentientMail and other clients to Email Engine contracts.</p>
          <a href="/docs">Open API docs</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head"><h2>Integration Operations</h2><a href="#settings">System console</a></div>
        <div className="button-row">
          <button className="primary" onClick={refreshDiagnostics} disabled={busy}>Refresh Diagnostics</button>
          <button className="ghost" onClick={() => { window.location.hash = '#data'; }}>Data Sources</button>
          <button className="ghost" onClick={() => { window.location.href = '/docs'; }}>OpenAPI Docs</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Integration Readiness</h2><a href="/api/v1/system/diagnostics">Raw diagnostics</a></div>
        <table>
          <thead><tr><th>Area</th><th>Status</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td>Schema</td><td><span className="pill">{diagnostics?.schema.ok ? 'ready' : 'review'}</span></td><td>{diagnostics?.schema.needs_migration ? 'Migration required' : 'Current revision is deployed'}</td></tr>
            <tr><td>SMTP</td><td><span className="pill">{smtpReady ? 'ready' : 'not configured'}</span></td><td>Managed SMTP provider path for future outbound infrastructure.</td></tr>
            <tr><td>SG</td><td><span className="pill">{sgReady ? 'ready' : 'not configured'}</span></td><td>Current third-party provider readiness, abstracted behind provider interface.</td></tr>
            <tr><td>AI</td><td><span className="pill">{diagnostics?.ai.openai_configured ? 'ready' : 'fallback'}</span></td><td>{diagnostics?.ai.model || 'Deterministic fallback available'}</td></tr>
          </tbody>
        </table>
      </section>
      <section className="panel table-panel">
        <div className="panel-head"><h2>Entity Inventory</h2><span className="muted">{formatInt(counts.length)} entities</span></div>
        {counts.length ? (
          <table>
            <thead><tr><th>Entity</th><th>Rows</th></tr></thead>
            <tbody>{counts.slice(0, 10).map(([name, count]) => <tr key={name}><td>{name}</td><td>{formatInt(count)}</td></tr>)}</tbody>
          </table>
        ) : <EmptyState title="No entity counts" detail="Diagnostics did not include entity counts." />}
      </section>
      <section className="panel table-panel">
        <div className="panel-head"><h2>Database Tables</h2><span className="muted">{formatInt(tables.length)} tables</span></div>
        {tables.length ? (
          <table>
            <thead><tr><th>Table</th><th>Columns</th></tr></thead>
            <tbody>{tables.slice(0, 12).map((table) => <tr key={table}><td>{table}</td><td>{formatInt(diagnostics?.database_table_columns?.[table]?.length || 0)}</td></tr>)}</tbody>
          </table>
        ) : <EmptyState title="No table metadata" detail="Diagnostics did not include database table data." />}
      </section>
    </section>
  );
}

function DocsPage({ diagnostics }: { diagnostics: SystemDiagnostics | null }) {
  const [checkResults, setCheckResults] = useState<Record<string, { ok: boolean; detail: string; ms: number }>>({});
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState('Workflow readiness checks have not run yet.');
  const contractGroups = [
    {
      area: 'Contacts and Data',
      purpose: 'Import heterogeneous source data, inspect contacts, and expose attributes for audience/template workflows.',
      endpoints: [
        ['GET', '/api/v1/data-sources/list', 'List configured source systems.'],
        ['POST', '/api/v1/data-sources', 'Create a source definition.'],
        ['POST', '/api/v1/data-source-mappings', 'Create field mapping into contact objects.'],
        ['POST', '/api/v1/data-sources/{id}/ingest', 'Dry-run or import source rows.'],
        ['GET', '/api/v1/audiences/contacts/list', 'List contacts.'],
        ['GET', '/api/v1/audiences/contacts/meta', 'Discover contact fields and attributes.'],
      ],
    },
    {
      area: 'Templates and AI',
      purpose: 'Render Jinja/HTML/CSS templates, inspect variables, and generate or improve content.',
      endpoints: [
        ['GET', '/api/v1/templates/list', 'List templates.'],
        ['POST', '/api/v1/templates/preview', 'Render with sample variables.'],
        ['POST', '/api/v1/templates/variables', 'Inspect variable requirements.'],
        ['POST', '/api/v1/ai/templates/draft', 'Draft a template from natural language.'],
        ['POST', '/api/v1/ai/templates/edit', 'Modify existing HTML/Jinja.'],
        ['POST', '/api/v1/ai/templates/recommend', 'Recommend template improvements.'],
      ],
    },
    {
      area: 'Audience and Campaigns',
      purpose: 'Build audiences, create campaigns, test-send, dry-run, and launch campaign queues.',
      endpoints: [
        ['GET', '/api/v1/audiences/list', 'List audiences.'],
        ['POST', '/api/v1/audiences/preview', 'Preview matched contacts.'],
        ['POST', '/api/v1/audiences/{id}/snapshots', 'Freeze audience membership.'],
        ['GET', '/api/v1/campaigns/list', 'List campaigns.'],
        ['POST', '/api/v1/campaigns/{id}/test-send', 'Send campaign test email.'],
        ['POST', '/api/v1/campaigns/{id}/launch', 'Create campaign send job.'],
      ],
    },
    {
      area: 'Delivery and Compliance',
      purpose: 'Process queued records, inspect send state, track links, and manage suppressions.',
      endpoints: [
        ['GET', '/api/v1/campaign-send-jobs/list', 'List send jobs.'],
        ['GET', '/api/v1/campaign-send-jobs/{id}/progress', 'Load job progress.'],
        ['GET', '/api/v1/email-send-records/list', 'List send records.'],
        ['POST', '/api/v1/delivery/process-queued', 'Process queued records.'],
        ['GET', '/api/v1/email-send-records/{id}/tracking-links', 'Generate tracking URLs.'],
        ['GET', '/api/v1/suppressions/list', 'List suppressions.'],
      ],
    },
    {
      area: 'Journeys and Analytics',
      purpose: 'Manage journey enrollment/execution and report on campaign, audience, journey, and domain performance.',
      endpoints: [
        ['GET', '/api/v1/journeys/list', 'List journeys and steps.'],
        ['POST', '/api/v1/journeys/{id}/enrollments', 'Enroll contact into journey.'],
        ['POST', '/api/v1/journeys/process', 'Process due enrollments.'],
        ['GET', '/api/v1/analytics/overview', 'Load global analytics summary.'],
        ['GET', '/api/v1/analytics/campaigns', 'Compare campaign performance.'],
        ['GET', '/api/v1/analytics/domains', 'Compare domain deliverability.'],
      ],
    },
  ];
  const objectRows = [
    ['Contact', 'Email Engine', 'SentientMail may create/update through contacts or data-source ingest APIs.'],
    ['Template', 'Email Engine', 'SentientMail should use template list/save/preview APIs and preserve Jinja variables.'],
    ['Audience', 'Email Engine', 'SentientMail should create rules, preview contacts, and snapshot before launch.'],
    ['Campaign', 'Email Engine', 'SentientMail should create campaign objects before test-send or launch.'],
    ['Send job / record', 'Email Engine', 'SentientMail should treat these as delivery-state read/manage objects.'],
    ['Journey', 'Email Engine', 'SentientMail should use journey/enrollment APIs for automation workflows.'],
  ];
  const smokeChecks = [
    {
      key: 'contacts',
      label: 'Contacts available',
      path: '/api/v1/audiences/contacts/meta?sample_limit=1&scan_limit=100',
      detail: 'Audience, import, and personalization workflows can discover contact fields.',
      action: 'Open Contacts',
      href: '#contacts',
    },
    {
      key: 'templates',
      label: 'Templates available',
      path: '/api/v1/templates/list?limit=1&offset=0',
      detail: 'Template editing, preview, and campaign creation can load saved templates.',
      action: 'Open Templates',
      href: '#templates',
    },
    {
      key: 'campaigns',
      label: 'Campaigns available',
      path: '/api/v1/campaigns/list?limit=1&offset=0',
      detail: 'Campaign manager can create, test, and launch campaign objects.',
      action: 'Open Campaigns',
      href: '#campaigns',
    },
    {
      key: 'delivery',
      label: 'Delivery available',
      path: '/api/v1/campaign-send-jobs/list?limit=1&offset=0',
      detail: 'Send jobs and delivery progress can be inspected after launch.',
      action: 'Open Delivery',
      href: '#delivery',
    },
    {
      key: 'analytics',
      label: 'Analytics available',
      path: '/api/v1/analytics/overview?recent_event_limit=1',
      detail: 'Reports can load summary counts, event mix, and recent activity.',
      action: 'Open Analytics',
      href: '#analytics',
    },
    {
      key: 'diagnostics',
      label: 'System ready',
      path: '/api/v1/system/diagnostics',
      detail: 'Schema and provider readiness can be checked from the product UI.',
      action: 'Open Settings',
      href: '#settings',
    },
  ];
  const passedChecks = Object.values(checkResults).filter((result) => result.ok).length;
  const totalChecks = smokeChecks.length;

  async function runSmokeChecks() {
    setChecking(true);
    setStatus('Checking core ESP workflow APIs...');
    try {
      const results = await Promise.all(smokeChecks.map(async (check) => {
        const start = performance.now();
        try {
          await fetchJson<unknown>(check.path);
          return [check.key, { ok: true, detail: 'Ready', ms: Math.round(performance.now() - start) }] as const;
        } catch (error) {
          return [check.key, {
            ok: false,
            detail: error instanceof Error ? error.message : String(error),
            ms: Math.round(performance.now() - start),
          }] as const;
        }
      }));
      const nextResults = Object.fromEntries(results);
      const okCount = Object.values(nextResults).filter((result) => result.ok).length;
      setCheckResults(nextResults);
      setStatus(`${okCount} of ${smokeChecks.length} core workflow APIs are reachable.`);
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    runSmokeChecks();
  }, []);

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Contract groups', value: formatInt(contractGroups.length), change: 'workflow surfaces' }} />
        <MetricCard metric={{ label: 'Tables', value: formatInt(diagnostics?.database_tables.length || 0), change: 'schema inventory' }} />
        <MetricCard metric={{ label: 'Schema', value: diagnostics?.schema.ok ? 'Ready' : 'Review', change: diagnostics?.schema.current_revision || 'unknown', tone: diagnostics?.schema.ok ? 'good' : 'warn' }} />
        <MetricCard metric={{ label: 'Workflow checks', value: `${passedChecks}/${totalChecks}`, change: checking ? 'checking now' : 'live APIs reachable', tone: passedChecks === totalChecks ? 'good' : 'warn' }} />
      </section>
      <section className="panel full-span">
        <div className="panel-head"><h2>Workflow Readiness</h2><span className="muted">simple health checks for the ESP experience</span></div>
        <div className={`operation-banner ${passedChecks < totalChecks && Object.keys(checkResults).length ? 'warn' : ''}`}>
          <strong>{checking ? 'Checking' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className="button-row">
          <button className="primary" onClick={runSmokeChecks} disabled={checking}>Run Checks</button>
          <button className="ghost" onClick={() => { window.location.hash = '#overview'; }}>Back to Overview</button>
        </div>
      </section>
      <section className="workflow-grid full-span">
        {smokeChecks.map((check) => {
          const result = checkResults[check.key];
          return (
            <article className={`workflow-card ${result && !result.ok ? 'warn' : ''}`} key={check.key}>
              <span>{result ? (result.ok ? 'Ready' : 'Needs attention') : 'Not checked'}</span>
              <strong>{check.label}</strong>
              <p>{result && !result.ok ? result.detail : check.detail}</p>
              <a href={check.href}>{check.action}</a>
            </article>
          );
        })}
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>OpenAPI</span>
          <strong>Interactive docs</strong>
          <p>Use FastAPI OpenAPI for request/response details and ad hoc endpoint testing.</p>
          <a href="/docs">Open API docs</a>
        </article>
        <article className="workflow-card">
          <span>SentientMail</span>
          <strong>GUI contract</strong>
          <p>SM should integrate to Email Engine API objects instead of duplicating backend state.</p>
          <a href="/esp#campaigns">Open campaigns</a>
        </article>
        <article className="workflow-card">
          <span>Diagnostics</span>
          <strong>System readiness</strong>
          <p>Schema revision and provider readiness are exposed through diagnostics.</p>
          <a href="/api/v1/system/diagnostics">Raw diagnostics</a>
        </article>
        <article className="workflow-card">
          <span>Developer</span>
          <strong>Technical console</strong>
          <p>Use the legacy admin only for debugging while the ESP workspace remains the primary product UI.</p>
          <a href="/admin">Open console</a>
        </article>
      </section>
      {contractGroups.map((group) => (
        <section className="panel table-panel full-span" key={group.area}>
          <div className="panel-head"><h2>{group.area}</h2><span className="muted">{group.purpose}</span></div>
          <table>
            <thead><tr><th>Method</th><th>Endpoint</th><th>Purpose</th></tr></thead>
            <tbody>
              {group.endpoints.map(([method, endpoint, purpose]) => (
                <tr key={`${method}-${endpoint}`}><td><span className="pill">{method}</span></td><td>{endpoint}</td><td>{purpose}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Object Ownership</h2><span className="muted">SM-to-EE integration guidance</span></div>
        <table>
          <thead><tr><th>Object</th><th>System of record</th><th>Integration note</th></tr></thead>
          <tbody>
            {objectRows.map(([object, owner, note]) => <tr key={object}><td>{object}</td><td>{owner}</td><td>{note}</td></tr>)}
          </tbody>
        </table>
      </section>
    </section>
  );
}

function SettingsPage({ diagnostics, onRefresh }: {
  diagnostics: SystemDiagnostics | null;
  onRefresh: () => Promise<void>;
}) {
  const [selectedTable, setSelectedTable] = useState('');
  const [status, setStatus] = useState('System settings view loaded.');
  const [busy, setBusy] = useState(false);
  const counts = Object.entries(diagnostics?.entity_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const tables = diagnostics?.database_tables || [];
  const tableName = selectedTable || tables[0] || '';
  const columns = tableName ? diagnostics?.database_table_columns?.[tableName] || [] : [];

  async function refreshDiagnostics() {
    setBusy(true);
    setStatus('Refreshing system diagnostics...');
    try {
      await onRefresh();
      setStatus('System diagnostics refreshed.');
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'System', value: diagnostics?.ok ? 'Healthy' : 'Review', change: diagnostics?.environment || 'environment unknown', tone: diagnostics?.ok ? 'good' : 'warn' }} />
        <MetricCard metric={{ label: 'Schema', value: diagnostics?.schema.needs_migration ? 'Migration needed' : 'Current', change: diagnostics?.schema.current_revision || 'no revision', tone: diagnostics?.schema.needs_migration ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Errors', value: formatInt(diagnostics?.errors.length || 0), change: 'diagnostic findings', tone: diagnostics?.errors.length ? 'warn' : 'good' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>System</span>
          <strong>Diagnostics</strong>
          <p>Inspect schema status, provider configuration, entity counts, tables, and columns.</p>
          <a href="#settings">Open diagnostics</a>
        </article>
        <article className="workflow-card">
          <span>Compliance</span>
          <strong>Suppressions</strong>
          <p>Manage unsubscribes, bounces, complaints, and suppression rules before campaign launch.</p>
          <a href="#compliance">Open suppressions</a>
        </article>
        <article className="workflow-card">
          <span>Testing</span>
          <strong>Tester console</strong>
          <p>Exercise API workflows, send test emails, and validate template rendering manually.</p>
          <a href="/tester">Open tester</a>
        </article>
        <article className="workflow-card">
          <span>Contracts</span>
          <strong>API docs</strong>
          <p>Review object models and endpoints used by the ESP admin and SentientMail GUI.</p>
          <a href="/docs">Open docs</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head"><h2>System Operations</h2><a href="#settings">Open diagnostics</a></div>
        <div className="form-grid">
          <label>
            Table inspector
            <select value={tableName} onChange={(event) => setSelectedTable(event.target.value)}>
              {tables.map((table) => <option value={table} key={table}>{table}</option>)}
            </select>
          </label>
          <label>
            Current revision
            <input value={diagnostics?.schema.current_revision || 'none'} readOnly />
          </label>
          <label>
            Expected revision
            <input value={diagnostics?.schema.expected_revision || 'unknown'} readOnly />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={refreshDiagnostics} disabled={busy}>Refresh Diagnostics</button>
          <button className="ghost" onClick={() => { window.location.hash = '#compliance'; }}>Suppressions</button>
          <button className="ghost" onClick={() => { window.location.href = '/tester'; }}>Tester</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Entity Counts</h2><a href="/api/v1/system/diagnostics">Raw diagnostics</a></div>
        {counts.length ? (
          <table>
            <thead><tr><th>Entity</th><th>Rows</th></tr></thead>
            <tbody>
              {counts.map(([name, count]) => <tr key={name}><td>{name}</td><td>{formatInt(count)}</td></tr>)}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No diagnostics loaded" detail="System diagnostics were not available to this page." actionHref="/admin/system" actionLabel="Open diagnostics" />
        )}
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Table Columns</h2><span className="muted">{tableName || 'No table selected'}</span></div>
        {columns.length ? (
          <table>
            <thead><tr><th>Column</th><th>Type</th><th>Nullable</th><th>Primary key</th></tr></thead>
            <tbody>
              {columns.map((column) => (
                <tr key={column.name}>
                  <td>{column.name}</td>
                  <td>{column.type}</td>
                  <td>{column.nullable ? 'yes' : 'no'}</td>
                  <td>{column.primary_key ? 'yes' : 'no'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState title="No columns loaded" detail="Select a table with column metadata." />}
      </section>
    </section>
  );
}

function SimpleModulePage({ title, detail, links }: {
  title: string;
  detail: string;
  links: Array<{ label: string; href: string }>;
}) {
  return (
    <section className="page-grid">
      <section className="panel">
        <div className="panel-head"><h2>{title}</h2></div>
        <p className="module-copy">{detail}</p>
        <div className="module-links">
          {links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}
        </div>
      </section>
    </section>
  );
}

function App() {
  const [activePage, setActivePage] = useState<PageKey>(pageFromHash);
  const [route, setRoute] = useState(routeFromHash);
  const [operationNotice, setOperationNotice] = useState<OperationNotice>({
    label: 'Workspace',
    message: 'Ready for campaign, template, and optimization workflows.',
    tone: 'success',
  });
  const [dashboard, setDashboard] = useState<DashboardState>({
    overview: null,
    campaigns: [],
    campaignItems: [],
    sendJobs: [],
    sendRecords: [],
    suppressions: [],
    dataSources: [],
    dataMappings: [],
    importJobs: [],
    contacts: [],
    contactMeta: null,
    audiences: [],
    audienceItems: [],
    templates: [],
    journeys: [],
    journeyItems: [],
    journeyEnrollments: [],
    journeyExecutions: [],
    diagnostics: null,
    aiInsights: fallbackInsights,
    loading: true,
    error: null,
  });

  useEffect(() => {
    function syncPage() {
      setActivePage(pageFromHash());
      setRoute(routeFromHash());
    }
    window.addEventListener('hashchange', syncPage);
    return () => window.removeEventListener('hashchange', syncPage);
  }, []);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const [overview, campaignData, campaignItems, sendJobData, sendRecordData, suppressionData, dataSourceData, dataMappingData, importJobData, contactData, contactMeta, audienceData, audienceItems, templateData, journeyData, journeyItems, journeyEnrollmentData, journeyExecutionData, diagnostics] = await Promise.all([
          fetchJson<AnalyticsOverview>('/api/v1/analytics/overview?recent_event_limit=25'),
          fetchJson<ListResponse<CampaignPerformance>>('/api/v1/analytics/campaigns?limit=10&offset=0'),
          fetchJson<ListResponse<CampaignRead>>('/api/v1/campaigns/list?limit=25&offset=0'),
          fetchJson<ListResponse<CampaignSendJobRead>>('/api/v1/campaign-send-jobs/list?limit=25&offset=0'),
          fetchJson<ListResponse<EmailSendRecordRead>>('/api/v1/email-send-records/list?limit=25&offset=0'),
          fetchJson<ListResponse<SuppressionRead>>('/api/v1/suppressions/list?limit=25&offset=0'),
          fetchJson<ListResponse<DataSourceRead>>('/api/v1/data-sources/list?limit=25&offset=0'),
          fetchJson<ListResponse<DataSourceMappingRead>>('/api/v1/data-source-mappings/list?limit=25&offset=0'),
          fetchJson<ListResponse<DataSourceImportJobRead>>('/api/v1/data-source-import-jobs/list?limit=25&offset=0'),
          fetchJson<ListResponse<ContactRead>>('/api/v1/audiences/contacts/list?limit=25&offset=0'),
          fetchJson<ContactMetadata>('/api/v1/audiences/contacts/meta?sample_limit=10&scan_limit=500'),
          fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
          fetchJson<ListResponse<AudienceRead>>('/api/v1/audiences/list?limit=25&offset=0'),
          fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyRead>>('/api/v1/journeys/list?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyEnrollmentRead>>('/api/v1/journey-enrollments/list?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyStepExecutionRead>>('/api/v1/journey-step-executions/list?limit=25&offset=0'),
          fetchJson<SystemDiagnostics>('/api/v1/system/diagnostics'),
        ]);
        let aiInsights = fallbackInsights;
        try {
          const ai = await fetchJson<AIAnalyticsAnalysis>('/api/v1/ai/analytics/analyze', {
            method: 'POST',
            body: JSON.stringify({
              report_type: 'esp_overview',
              report_context: {
                overview,
                campaigns: campaignData,
              },
              goals: [
                'Identify performance risks',
                'Recommend next action',
                'Improve ESP operator workflow decisions',
              ],
            }),
          });
          aiInsights = insightsFromAi(ai);
        } catch {
          aiInsights = fallbackInsights;
        }
        if (active) {
          setDashboard({
            overview,
            campaigns: campaignData.items || [],
            campaignItems: campaignItems.items || [],
            sendJobs: sendJobData.items || [],
            sendRecords: sendRecordData.items || [],
            suppressions: suppressionData.items || [],
            dataSources: dataSourceData.items || [],
            dataMappings: dataMappingData.items || [],
            importJobs: importJobData.items || [],
            contacts: contactData.items || [],
            contactMeta,
            audiences: audienceData.items || [],
            audienceItems: audienceItems.items || [],
            templates: templateData.items || [],
            journeys: journeyData.items || [],
            journeyItems: journeyItems.items || [],
            journeyEnrollments: journeyEnrollmentData.items || [],
            journeyExecutions: journeyExecutionData.items || [],
            diagnostics,
            aiInsights,
            loading: false,
            error: null,
          });
        }
      } catch (error) {
        if (active) {
          setDashboard({
            overview: null,
            campaigns: [],
            campaignItems: [],
            sendJobs: [],
            sendRecords: [],
            suppressions: [],
            dataSources: [],
            dataMappings: [],
            importJobs: [],
            contacts: [],
            contactMeta: null,
            audiences: [],
            audienceItems: [],
            templates: [],
            journeys: [],
            journeyItems: [],
            journeyEnrollments: [],
            journeyExecutions: [],
            diagnostics: null,
            aiInsights: fallbackInsights,
            loading: false,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    }

    loadDashboard();
    return () => {
      active = false;
    };
  }, []);

  const liveMetrics = useMemo(() => metricsFromOverview(dashboard.overview), [dashboard.overview]);
  const liveCampaigns = useMemo(
    () => campaignsFromPerformance(dashboard.campaigns),
    [dashboard.campaigns],
  );
  const status = pageSubtitle(activePage, dashboard);
  const content = (() => {
    if (activePage === 'campaigns') {
      return (
        <CampaignsPage
          campaigns={dashboard.campaigns}
          campaignItems={dashboard.campaignItems}
          templates={dashboard.templates}
          audiences={dashboard.audienceItems}
          route={route}
          onRefresh={async () => {
            const [campaignData, campaignItems] = await Promise.all([
              fetchJson<ListResponse<CampaignPerformance>>('/api/v1/analytics/campaigns?limit=10&offset=0'),
              fetchJson<ListResponse<CampaignRead>>('/api/v1/campaigns/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              campaigns: campaignData.items || [],
              campaignItems: campaignItems.items || [],
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'automations') {
      return (
        <AutomationsPage
          journeys={dashboard.journeys}
          journeyItems={dashboard.journeyItems}
          templates={dashboard.templates}
          contacts={dashboard.contacts}
          enrollments={dashboard.journeyEnrollments}
          executions={dashboard.journeyExecutions}
          route={route}
          onRefresh={async () => {
            const [journeyData, journeyItems, journeyEnrollmentData, journeyExecutionData, contactData] = await Promise.all([
              fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
              fetchJson<ListResponse<JourneyRead>>('/api/v1/journeys/list?limit=25&offset=0'),
              fetchJson<ListResponse<JourneyEnrollmentRead>>('/api/v1/journey-enrollments/list?limit=25&offset=0'),
              fetchJson<ListResponse<JourneyStepExecutionRead>>('/api/v1/journey-step-executions/list?limit=25&offset=0'),
              fetchJson<ListResponse<ContactRead>>('/api/v1/audiences/contacts/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              journeys: journeyData.items || [],
              journeyItems: journeyItems.items || [],
              journeyEnrollments: journeyEnrollmentData.items || [],
              journeyExecutions: journeyExecutionData.items || [],
              contacts: contactData.items || [],
            }));
          }}
        />
      );
    }
    if (activePage === 'delivery') {
      return (
        <DeliveryPage
          sendJobs={dashboard.sendJobs}
          sendRecords={dashboard.sendRecords}
          campaigns={dashboard.campaignItems}
          onRefresh={async () => {
            const [sendJobData, sendRecordData] = await Promise.all([
              fetchJson<ListResponse<CampaignSendJobRead>>('/api/v1/campaign-send-jobs/list?limit=25&offset=0'),
              fetchJson<ListResponse<EmailSendRecordRead>>('/api/v1/email-send-records/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              sendJobs: sendJobData.items || [],
              sendRecords: sendRecordData.items || [],
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'compliance') {
      return (
        <CompliancePage
          suppressions={dashboard.suppressions}
          sendRecords={dashboard.sendRecords}
          route={route}
          onRefresh={async () => {
            const suppressionData = await fetchJson<ListResponse<SuppressionRead>>('/api/v1/suppressions/list?limit=25&offset=0');
            setDashboard((current) => ({
              ...current,
              suppressions: suppressionData.items || [],
            }));
          }}
        />
      );
    }
    if (activePage === 'data') {
      return (
        <DataPage
          dataSources={dashboard.dataSources}
          mappings={dashboard.dataMappings}
          importJobs={dashboard.importJobs}
          route={route}
          onRefresh={async () => {
            const [dataSourceData, dataMappingData, importJobData] = await Promise.all([
              fetchJson<ListResponse<DataSourceRead>>('/api/v1/data-sources/list?limit=25&offset=0'),
              fetchJson<ListResponse<DataSourceMappingRead>>('/api/v1/data-source-mappings/list?limit=25&offset=0'),
              fetchJson<ListResponse<DataSourceImportJobRead>>('/api/v1/data-source-import-jobs/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              dataSources: dataSourceData.items || [],
              dataMappings: dataMappingData.items || [],
              importJobs: importJobData.items || [],
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'contacts') {
      return (
        <ContactsPage
          contacts={dashboard.contacts}
          metadata={dashboard.contactMeta}
          route={route}
          onRefresh={async () => {
            const [contactData, contactMeta] = await Promise.all([
              fetchJson<ListResponse<ContactRead>>('/api/v1/audiences/contacts/list?limit=25&offset=0'),
              fetchJson<ContactMetadata>('/api/v1/audiences/contacts/meta?sample_limit=10&scan_limit=500'),
            ]);
            setDashboard((current) => ({
              ...current,
              contacts: contactData.items || [],
              contactMeta,
            }));
          }}
        />
      );
    }
    if (activePage === 'audience') {
      return (
        <AudiencePage
          audiences={dashboard.audiences}
          audienceItems={dashboard.audienceItems}
          metadata={dashboard.contactMeta}
          route={route}
          onRefresh={async () => {
            const [audienceData, audienceItems, contactMeta] = await Promise.all([
              fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
              fetchJson<ListResponse<AudienceRead>>('/api/v1/audiences/list?limit=25&offset=0'),
              fetchJson<ContactMetadata>('/api/v1/audiences/contacts/meta?sample_limit=10&scan_limit=500'),
            ]);
            setDashboard((current) => ({
              ...current,
              audiences: audienceData.items || [],
              audienceItems: audienceItems.items || [],
              contactMeta,
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'templates') {
      return (
        <TemplatesPage
          templates={dashboard.templates}
          route={route}
          onRefresh={async () => {
            const templateData = await fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0');
            setDashboard((current) => ({
              ...current,
              templates: templateData.items || [],
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'ai-studio') {
      return (
        <AiStudioPage
          insights={dashboard.aiInsights}
          diagnostics={dashboard.diagnostics}
          dashboard={dashboard}
          onTemplatesRefresh={async () => {
            const templateData = await fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0');
            setDashboard((current) => ({ ...current, templates: templateData.items || [] }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'analytics') {
      return (
        <AnalyticsPage
          overview={dashboard.overview}
          campaigns={dashboard.campaigns}
          campaignItems={dashboard.campaignItems}
          audiences={dashboard.audiences}
          journeys={dashboard.journeys}
          onRefresh={async () => {
            const [overview, campaignData, audienceData, journeyData] = await Promise.all([
              fetchJson<AnalyticsOverview>('/api/v1/analytics/overview?recent_event_limit=25'),
              fetchJson<ListResponse<CampaignPerformance>>('/api/v1/analytics/campaigns?limit=10&offset=0'),
              fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
              fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              overview,
              campaigns: campaignData.items || [],
              audiences: audienceData.items || [],
              journeys: journeyData.items || [],
            }));
          }}
          onOperation={setOperationNotice}
        />
      );
    }
    if (activePage === 'integrations') {
      return (
        <IntegrationsPage
          diagnostics={dashboard.diagnostics}
          onRefresh={async () => {
            const diagnostics = await fetchJson<SystemDiagnostics>('/api/v1/system/diagnostics');
            setDashboard((current) => ({ ...current, diagnostics }));
          }}
        />
      );
    }
    if (activePage === 'docs') {
      return <DocsPage diagnostics={dashboard.diagnostics} />;
    }
    if (activePage === 'settings') {
      return (
        <SettingsPage
          diagnostics={dashboard.diagnostics}
          onRefresh={async () => {
            const diagnostics = await fetchJson<SystemDiagnostics>('/api/v1/system/diagnostics');
            setDashboard((current) => ({ ...current, diagnostics }));
          }}
        />
      );
    }
    return (
      <OverviewPage dashboard={dashboard} metrics={liveMetrics} campaigns={liveCampaigns} />
    );
  })();

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} />
		      <main className="workspace">
		        <Header title={pageTitle(activePage)} status={status} operation={operationNotice} activePage={activePage} />
		        {content}
		      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
