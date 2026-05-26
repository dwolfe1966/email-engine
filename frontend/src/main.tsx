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

type CampaignRead = {
  id: string;
  name: string;
  status: string;
  template_id: string;
  audience_query: Record<string, unknown>;
  scheduled_at: string | null;
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
  errors: string[];
};

type DashboardState = {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  campaignItems: CampaignRead[];
  audiences: AudiencePerformance[];
  audienceItems: AudienceRead[];
  templates: TemplateRead[];
  journeys: JourneyPerformance[];
  journeyItems: JourneyRead[];
  diagnostics: SystemDiagnostics | null;
  aiInsights: Insight[];
  loading: boolean;
  error: string | null;
};

type PageKey =
  | 'overview'
  | 'campaigns'
  | 'automations'
  | 'audience'
  | 'templates'
  | 'ai-studio'
  | 'analytics'
  | 'integrations'
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
  { label: 'Audience', key: 'audience', href: '#audience' },
  { label: 'Templates', key: 'templates', href: '#templates' },
  { label: 'AI Studio', key: 'ai-studio', href: '#ai-studio' },
  { label: 'Analytics', key: 'analytics', href: '#analytics' },
  { label: 'Integrations', key: 'integrations', href: '#integrations' },
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
  return navItems.find((item) => item.key === hash)?.key || 'overview';
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
    audience: 'Manage audiences and segmentation readiness.',
    templates: 'Create, edit, and test dynamic email templates.',
    'ai-studio': 'Use AI helpers across templates, campaigns, audiences, and analytics.',
    analytics: 'Review performance, engagement, and delivery signals.',
    integrations: 'Connect data sources, providers, and external tools.',
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

function Header({ title, status }: { title: string; status: string }) {
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{status}</p>
      </div>
      <div className="topbar-actions">
        <label className="search">
          <span>Search</span>
          <input placeholder="Search campaigns, contacts, templates..." />
        </label>
        <button className="ghost">May 1 - May 31, 2026</button>
        <button className="primary" onClick={() => { window.location.href = '/admin/campaigns'; }}>Create Campaign</button>
      </div>
    </header>
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
        <a href="/admin/analytics">Open analytics</a>
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
        <a href="/admin/analytics">View all</a>
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
        <a href="/admin/campaigns">Manage campaigns</a>
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
      <a href="/admin/campaigns">Email Campaign</a>
      <a href="/admin/journeys">Automation</a>
      <a href="/admin/audiences">Segment</a>
      <a href="/template-editor">Template</a>
    </section>
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

function CampaignsPage({ campaigns, campaignItems, templates, audiences, onRefresh }: {
  campaigns: CampaignPerformance[];
  campaignItems: CampaignRead[];
  templates: TemplateRead[];
  audiences: AudienceRead[];
  onRefresh: () => Promise<void>;
}) {
  const [campaignName, setCampaignName] = useState('ESP Test Campaign');
  const [templateId, setTemplateId] = useState('');
  const [audienceId, setAudienceId] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [testEmail, setTestEmail] = useState('');
  const [variablesJson, setVariablesJson] = useState('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
  const [operationStatus, setOperationStatus] = useState('Ready to create a draft campaign.');
  const [operationBusy, setOperationBusy] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');

  useEffect(() => {
    if (!templateId && templates.length) setTemplateId(templates[0].id);
    if (!audienceId && audiences.length) setAudienceId(audiences[0].id);
    if (!selectedCampaignId && campaignItems.length) setSelectedCampaignId(campaignItems[0].id);
  }, [audienceId, audiences, campaignItems, selectedCampaignId, templateId, templates]);

  const totalRequested = campaigns.reduce((sum, item) => sum + Number(item.requested_count || 0), 0);
  const totalSent = campaigns.reduce((sum, item) => sum + Number(item.sent_count || 0), 0);
  const totalFailures = campaigns.reduce((sum, item) => sum + Number(item.failed_count || 0), 0);
  const bestOpen = campaigns.reduce<CampaignPerformance | null>((best, item) =>
    !best || Number(item.open_rate || 0) > Number(best.open_rate || 0) ? item : best, null);
  const selectedAudience = audiences.find((item) => item.id === audienceId);
  const selectedCampaign = campaignItems.find((item) => item.id === selectedCampaignId);

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
    try {
      const message = await operation();
      setOperationStatus(message);
      await onRefresh();
    } catch (error) {
      setOperationStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setOperationBusy(false);
    }
  }

  async function createDraftCampaign() {
    await runOperation('Creating draft campaign', async () => {
      if (!templateId) throw new Error('Select a template.');
      const payload = {
        name: campaignName.trim() || `ESP Campaign ${new Date().toISOString()}`,
        template_id: templateId,
        audience_query: selectedAudience?.rule_tree || {},
      };
      const created = await fetchJson<CampaignRead>('/api/v1/campaigns', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setSelectedCampaignId(created.id);
      return `Created draft campaign: ${created.name}`;
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

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Campaigns', value: formatInt(campaigns.length), change: 'live rows' }} />
        <MetricCard metric={{ label: 'Requested', value: formatInt(totalRequested), change: 'targeted sends' }} />
        <MetricCard metric={{ label: 'Sent', value: formatInt(totalSent), change: 'processed sends' }} />
        <MetricCard metric={{ label: 'Failures', value: formatInt(totalFailures), change: 'delivery issues', tone: totalFailures ? 'warn' : 'good' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Next action</span>
          <strong>Create campaign</strong>
          <p>Use the workbench to attach template, audience, test variables, and launch readiness checks.</p>
          <a href="/admin/campaigns">Open Campaign Manager</a>
        </article>
        <article className="workflow-card">
          <span>Content</span>
          <strong>Template builder</strong>
          <p>Generate or edit dynamic Jinja templates before pairing them with campaign audiences.</p>
          <a href="/template-editor">Open Template Editor</a>
        </article>
        <article className={`workflow-card ${totalFailures ? 'warn' : ''}`}>
          <span>Health</span>
          <strong>{totalFailures ? 'Delivery review needed' : 'No failures visible'}</strong>
          <p>{totalFailures ? 'Review failed records before scaling sends.' : 'No campaign failures are visible in this page of results.'}</p>
          <a href="/admin/delivery">Open Delivery Manager</a>
        </article>
        <article className="workflow-card">
          <span>Benchmark</span>
          <strong>{bestOpen ? `${formatPct(bestOpen.open_rate)} open rate` : 'No benchmark yet'}</strong>
          <p>{bestOpen ? `${bestOpen.name} is the current open-rate benchmark.` : 'Send a test campaign to establish a benchmark.'}</p>
          <a href="/admin/analytics">Open Analytics</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>ESP Campaign Workflow</h2>
          <a href="/admin/campaigns">Advanced workbench</a>
        </div>
        <div className="form-grid">
          <label>
            Campaign name
            <input value={campaignName} onChange={(event) => setCampaignName(event.target.value)} />
          </label>
          <label>
            Existing campaign
            <select value={selectedCampaignId} onChange={(event) => setSelectedCampaignId(event.target.value)}>
              <option value="">Create new draft</option>
              {campaignItems.map((campaign) => (
                <option value={campaign.id} key={campaign.id}>{campaign.name} ({campaign.status})</option>
              ))}
            </select>
          </label>
          <label>
            Template
            <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
              <option value="">Select template</option>
              {templates.map((template) => (
                <option value={template.id} key={template.id}>{template.name}</option>
              ))}
            </select>
          </label>
          <label>
            Audience
            <select value={audienceId} onChange={(event) => setAudienceId(event.target.value)}>
              <option value="">Select audience</option>
              {audiences.map((audience) => (
                <option value={audience.id} key={audience.id}>{audience.name} ({formatInt(audience.estimated_count)})</option>
              ))}
            </select>
          </label>
          <label>
            Test recipient
            <input value={testEmail} onChange={(event) => setTestEmail(event.target.value)} placeholder="you@example.com" />
          </label>
          <label className="wide-field">
            Test variables JSON
            <textarea value={variablesJson} onChange={(event) => setVariablesJson(event.target.value)} rows={8} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={createDraftCampaign} disabled={operationBusy || !templateId}>Create Draft</button>
          <button className="ghost" onClick={validateCampaign} disabled={operationBusy || !selectedCampaignId}>Validate</button>
          <button className="ghost" onClick={previewTestEmail} disabled={operationBusy || !selectedCampaignId}>Preview Test</button>
          <button className="ghost" onClick={sendTestEmail} disabled={operationBusy || !selectedCampaignId}>Send Test Email</button>
          <button className="ghost" onClick={dryRunLaunch} disabled={operationBusy || !selectedCampaignId}>Dry-Run Launch</button>
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
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <h2>Campaign Manager</h2>
          <a href="/admin/campaigns">Open workbench</a>
        </div>
        {campaigns.length ? (
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
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr key={campaign.campaign_id}>
                  <td>{campaign.name}</td>
                  <td><span className="pill">{campaign.status}</span></td>
                  <td>{formatInt(campaign.requested_count)}</td>
                  <td>{formatInt(campaign.sent_count)}</td>
                  <td>{formatPct(campaign.open_rate)}</td>
                  <td>{formatPct(campaign.click_rate)}</td>
                  <td>{formatInt(campaign.failed_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No campaigns yet" detail="Create a campaign in the workbench, then it will appear here." actionHref="/admin/campaigns" actionLabel="Create campaign" />
        )}
      </section>
    </section>
  );
}

function AutomationsPage({ journeys, journeyItems, templates, onRefresh }: {
  journeys: JourneyPerformance[];
  journeyItems: JourneyRead[];
  templates: TemplateRead[];
  onRefresh: () => Promise<void>;
}) {
  const [selectedJourneyId, setSelectedJourneyId] = useState('');
  const [name, setName] = useState('ESP Journey Draft');
  const [description, setDescription] = useState('Created from the ESP automation workflow.');
  const [entryRuleJson, setEntryRuleJson] = useState('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
  const [exitRuleJson, setExitRuleJson] = useState('{}');
  const [templateId, setTemplateId] = useState('');
  const [stepName, setStepName] = useState('Send welcome email');
  const [status, setStatus] = useState('Ready to create or update a journey.');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedJourneyId && journeyItems.length) loadJourneyIntoEditor(journeyItems[0]);
    if (!templateId && templates.length) setTemplateId(templates[0].id);
  }, [journeyItems, selectedJourneyId, templateId, templates]);

  const failures = journeys.reduce((sum, item) =>
    sum + Number(item.failed_count || 0) + Number(item.step_failed_count || 0), 0);
  const queued = journeys.reduce((sum, item) => sum + Number(item.queued_send_count || 0), 0);
  const active = journeys.reduce((sum, item) => sum + Number(item.active_count || 0), 0);
  const completed = journeys.reduce((sum, item) => sum + Number(item.completed_count || 0), 0);
  const mostActive = journeys.reduce<JourneyPerformance | null>((best, item) =>
    !best || Number(item.active_count || 0) > Number(best.active_count || 0) ? item : best, null);
  const riskiest = journeys.reduce<JourneyPerformance | null>((worst, item) => {
    const itemFailures = Number(item.failed_count || 0) + Number(item.step_failed_count || 0);
    const worstFailures = Number(worst?.failed_count || 0) + Number(worst?.step_failed_count || 0);
    return !worst || itemFailures > worstFailures ? item : worst;
  }, null);

  const selectedJourney = journeyItems.find((item) => item.id === selectedJourneyId);

  function loadJourneyIntoEditor(journey: JourneyRead) {
    setSelectedJourneyId(journey.id);
    setName(journey.name);
    setDescription(journey.description || '');
    setEntryRuleJson(JSON.stringify(journey.entry_rule_tree || {}, null, 2));
    setExitRuleJson(JSON.stringify(journey.exit_rule_tree || {}, null, 2));
    setStatus(`Loaded journey: ${journey.name}`);
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

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Journeys', value: formatInt(journeys.length), change: 'total' }} />
        <MetricCard metric={{ label: 'Active', value: formatInt(active), change: 'active enrollments' }} />
        <MetricCard metric={{ label: 'Completed', value: formatInt(completed), change: 'finished enrollments' }} />
        <MetricCard metric={{ label: 'Failures', value: formatInt(failures), change: 'needs review', tone: failures ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Queued sends', value: formatInt(queued), change: 'delivery backlog', tone: queued ? 'warn' : 'good' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Build</span>
          <strong>Journey builder</strong>
          <p>Create trigger, wait, branch, and send steps with the admin journey graph.</p>
          <a href="/admin/journeys">Open Journey Manager</a>
        </article>
        <article className="workflow-card">
          <span>Health</span>
          <strong>{mostActive ? mostActive.name : 'No active journey'}</strong>
          <p>{mostActive ? `${formatInt(mostActive.active_count)} active enrollments are currently moving through this journey.` : 'Create or activate a journey to start tracking enrollments.'}</p>
          <a href="/admin/journeys">Review active journeys</a>
        </article>
        <article className={`workflow-card ${failures ? 'warn' : ''}`}>
          <span>Risk</span>
          <strong>{failures ? `${formatInt(failures)} failures` : 'No failures visible'}</strong>
          <p>{failures && riskiest ? `${riskiest.name} has the highest visible failure count.` : 'No journey execution failures are visible in this page of results.'}</p>
          <a href="/admin/journeys">Inspect executions</a>
        </article>
        <article className={`workflow-card ${queued ? 'warn' : ''}`}>
          <span>Queue</span>
          <strong>{formatInt(queued)} queued sends</strong>
          <p>{queued ? 'Process queued journey messages and review delivery status before scaling.' : 'Journey send queue is clear for the visible journey set.'}</p>
          <a href="/admin/delivery">Open Delivery Manager</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>ESP Journey Workflow</h2>
          <a href="/admin/journeys">Advanced builder</a>
        </div>
        <div className="form-grid">
          <label>
            Existing journey
            <select value={selectedJourneyId} onChange={(event) => {
              const journey = journeyItems.find((item) => item.id === event.target.value);
              if (journey) loadJourneyIntoEditor(journey);
              else setSelectedJourneyId('');
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
          <label className="wide-field">
            Entry rule JSON
            <textarea value={entryRuleJson} onChange={(event) => setEntryRuleJson(event.target.value)} rows={8} />
          </label>
          <label>
            Exit rule JSON
            <textarea value={exitRuleJson} onChange={(event) => setExitRuleJson(event.target.value)} rows={8} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveJourney} disabled={busy}>Save Journey</button>
          <button className="ghost" onClick={addSendStep} disabled={busy || !selectedJourneyId || !templateId}>Add Send Step</button>
          <button className="ghost" onClick={processDue} disabled={busy}>Process Due</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {selectedJourney?.steps?.length ? <small>{selectedJourney.steps.map((step) => `${step.position + 1}. ${step.name}`).join(' | ')}</small> : null}
        </div>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <h2>Automation Journeys</h2>
          <a href="/admin/journeys">Open journey builder</a>
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
              </tr>
            </thead>
            <tbody>
              {journeys.map((journey) => (
                <tr key={journey.journey_id}>
                  <td>{journey.name}</td>
                  <td><span className="pill">{journey.status}</span></td>
                  <td>{formatInt(journey.enrollment_count)}</td>
                  <td>{formatInt(journey.active_count)}</td>
                  <td>{formatInt(journey.completed_count)}</td>
                  <td>{formatInt(Number(journey.failed_count || 0) + Number(journey.step_failed_count || 0))}</td>
                  <td>{formatInt(journey.queued_send_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No journeys yet" detail="Build an automation journey and AI review it from Journey Manager." actionHref="/admin/journeys" actionLabel="Open Journey Manager" />
        )}
      </section>
    </section>
  );
}

function AudiencePage({ audiences, audienceItems, onRefresh }: {
  audiences: AudiencePerformance[];
  audienceItems: AudienceRead[];
  onRefresh: () => Promise<void>;
}) {
  const [selectedAudienceId, setSelectedAudienceId] = useState('');
  const [name, setName] = useState('ESP Audience Draft');
  const [description, setDescription] = useState('Created from the ESP audience workflow.');
  const [ruleJson, setRuleJson] = useState('{\n  "field": "email",\n  "comparator": "contains",\n  "value": "@"\n}');
  const [status, setStatus] = useState('Ready to create or preview an audience.');
  const [busy, setBusy] = useState(false);
  const [matchedCount, setMatchedCount] = useState<number | null>(null);
  const [sampleContacts, setSampleContacts] = useState<ContactRead[]>([]);

  useEffect(() => {
    if (!selectedAudienceId && audienceItems.length) {
      loadAudienceIntoEditor(audienceItems[0]);
    }
  }, [audienceItems, selectedAudienceId]);

  const estimated = audiences.reduce((sum, item) => sum + Number(item.estimated_count || 0), 0);
  const sent = audiences.reduce((sum, item) => sum + Number(item.sent_count || 0), 0);
  const bestAudience = audiences.reduce<AudiencePerformance | null>((best, item) =>
    !best || Number(item.open_rate || 0) > Number(best.open_rate || 0) ? item : best, null);

  function loadAudienceIntoEditor(audience: AudienceRead) {
    setSelectedAudienceId(audience.id);
    setName(audience.name);
    setDescription(audience.description || '');
    setRuleJson(JSON.stringify(audience.rule_tree || {}, null, 2));
    setMatchedCount(audience.estimated_count);
    setSampleContacts([]);
    setStatus(`Loaded audience: ${audience.name}`);
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

  async function runAudienceOperation(label: string, operation: () => Promise<string>) {
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

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Audiences', value: formatInt(audiences.length), change: 'saved segments' }} />
        <MetricCard metric={{ label: 'Estimated reach', value: formatInt(estimated), change: 'matched contacts' }} />
        <MetricCard metric={{ label: 'Sent', value: formatInt(sent), change: 'campaign sends' }} />
        <MetricCard metric={{ label: 'Best open rate', value: bestAudience ? formatPct(bestAudience.open_rate) : '0%', change: bestAudience?.name || 'no activity' }} />
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Import</span>
          <strong>Audience import</strong>
          <p>Upload CSV contacts, preview mappings, and create contacts for segmentation.</p>
          <a href="/admin/audience-import">Import contacts</a>
        </article>
        <article className="workflow-card">
          <span>Segment</span>
          <strong>Audience builder</strong>
          <p>Preview matching contacts and tune field constraints before campaign launch.</p>
          <a href="/admin/audiences">Open builder</a>
        </article>
        <article className="workflow-card">
          <span>AI</span>
          <strong>Audience review</strong>
          <p>Use AI recommendations to find unknown fields, zero-match rules, and targeting risks.</p>
          <a href="/admin/audiences">Review audience</a>
        </article>
        <article className="workflow-card">
          <span>Snapshots</span>
          <strong>Save launch state</strong>
          <p>Create audience snapshots before larger sends so launch targeting is auditable.</p>
          <a href="/admin/audiences">Create snapshot</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>ESP Audience Workflow</h2>
          <a href="/admin/audiences">Advanced builder</a>
        </div>
        <div className="form-grid">
          <label>
            Existing audience
            <select value={selectedAudienceId} onChange={(event) => {
              const audience = audienceItems.find((item) => item.id === event.target.value);
              if (audience) loadAudienceIntoEditor(audience);
              else setSelectedAudienceId('');
            }}>
              <option value="">Create new audience</option>
              {audienceItems.map((audience) => (
                <option value={audience.id} key={audience.id}>{audience.name} ({formatInt(audience.estimated_count)})</option>
              ))}
            </select>
          </label>
          <label>
            Audience name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Matched contacts
            <input value={matchedCount === null ? 'Not previewed' : formatInt(matchedCount)} readOnly />
          </label>
          <label className="wide-field">
            Description
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label className="wide-field">
            Rule JSON
            <textarea value={ruleJson} onChange={(event) => setRuleJson(event.target.value)} rows={10} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveAudience} disabled={busy}>Save Audience</button>
          <button className="ghost" onClick={previewAudience} disabled={busy}>Preview Contacts</button>
          <button className="ghost" onClick={snapshotAudience} disabled={busy || !selectedAudienceId}>Create Snapshot</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        {sampleContacts.length ? (
          <section className="panel table-panel nested-panel">
            <div className="panel-head"><h2>Matched Contacts Preview</h2></div>
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
          </section>
        ) : null}
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head">
          <h2>Audiences</h2>
          <a href="/admin/audiences">Open audience builder</a>
        </div>
        {audiences.length ? (
          <table>
            <thead>
              <tr>
                <th>Audience</th>
                <th>Status</th>
                <th>Estimated</th>
                <th>Sent</th>
                <th>Open rate</th>
                <th>Click rate</th>
              </tr>
            </thead>
            <tbody>
              {audiences.map((audience) => (
                <tr key={audience.audience_id}>
                  <td>{audience.name}</td>
                  <td><span className="pill">{audience.status}</span></td>
                  <td>{formatInt(audience.estimated_count)}</td>
                  <td>{formatInt(audience.sent_count)}</td>
                  <td>{formatPct(audience.open_rate)}</td>
                  <td>{formatPct(audience.click_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="No audiences yet" detail="Import contacts or create a dynamic audience rule set." actionHref="/admin/audience-import" actionLabel="Import audience" />
        )}
      </section>
    </section>
  );
}

function TemplatesPage({ templates, onRefresh }: { templates: TemplateRead[]; onRefresh: () => Promise<void> }) {
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

  useEffect(() => {
    if (!selectedTemplateId && templates.length) {
      loadTemplateIntoEditor(templates[0]);
    }
  }, [selectedTemplateId, templates]);

  function loadTemplateIntoEditor(template: TemplateRead) {
    setSelectedTemplateId(template.id);
    setName(template.name);
    setSubject(template.subject);
    setHtmlBody(template.html_body || '');
    setCssBody(template.css_body || '');
    setPreviewHtml('');
    setStatus(`Loaded template: ${template.name}`);
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
    try {
      const message = await operation();
      setStatus(message);
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
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
      await onRefresh();
      return `Saved template: ${saved.name}`;
    });
  }

  async function previewTemplate() {
    await runTemplateOperation('Rendering preview', async () => {
      const data = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject,
          html_body: htmlBody,
          css_body: cssBody || null,
          variables: parsedVariables(),
        }),
      });
      setPreviewHtml(data.html_body || '');
      const issueText = data.errors?.length ? ` ${data.errors.join('; ')}` : '';
      return `Rendered preview: ${data.subject}.${issueText}`;
    });
  }

  async function inspectVariables() {
    await runTemplateOperation('Inspecting variables', async () => {
      const data = await fetchJson<{ variables: TemplateVariable[]; sample_variables: Record<string, unknown>; errors: string[] }>('/api/v1/templates/variables', {
        method: 'POST',
        body: JSON.stringify({
          subject,
          html_body: htmlBody,
          css_body: cssBody || null,
          variables: parsedVariables(),
        }),
      });
      setVariables(data.variables || []);
      if (data.sample_variables && Object.keys(data.sample_variables).length) {
        setVariablesJson(JSON.stringify(data.sample_variables, null, 2));
      }
      return `Detected ${formatInt(data.variables?.length || 0)} variable(s).`;
    });
  }

  async function seedSamples() {
    await runTemplateOperation('Seeding sample templates', async () => {
      const data = await fetchJson<TemplateRead[]>('/api/v1/templates/samples', { method: 'POST' });
      await onRefresh();
      return `Sample templates ready: ${formatInt(data.length)} templates.`;
    });
  }

  return (
    <section className="page-grid">
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Create</span>
          <strong>Template editor</strong>
          <p>Edit Jinja/HTML, sample variables, preview rendering, and send test emails.</p>
          <a href="/template-editor">Open editor</a>
        </article>
        <article className="workflow-card">
          <span>AI</span>
          <strong>Generate content</strong>
          <p>Use AI to draft, modify, and improve templates while preserving dynamic variables.</p>
          <a href="/template-editor">Open AI tools</a>
        </article>
        <article className="workflow-card">
          <span>Design</span>
          <strong>WYSIWYG blocks</strong>
          <p>Use design blocks for headings, paragraphs, buttons, images, dividers, and raw HTML.</p>
          <a href="/template-editor">Open design tab</a>
        </article>
        <article className="workflow-card">
          <span>Samples</span>
          <strong>Seed examples</strong>
          <p>Load ecommerce, subscription, and social templates to validate dynamic language support.</p>
          <a href="/template-editor">Seed samples</a>
        </article>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>ESP Template Workflow</h2>
          <a href="/template-editor">Advanced editor</a>
        </div>
        <div className="form-grid">
          <label>
            Existing template
            <select value={selectedTemplateId} onChange={(event) => {
              const template = templates.find((item) => item.id === event.target.value);
              if (template) loadTemplateIntoEditor(template);
              else setSelectedTemplateId('');
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
            <textarea value={htmlBody} onChange={(event) => setHtmlBody(event.target.value)} rows={12} />
          </label>
          <label>
            Sample variables JSON
            <textarea value={variablesJson} onChange={(event) => setVariablesJson(event.target.value)} rows={12} />
          </label>
          <label className="wide-field">
            CSS
            <textarea value={cssBody} onChange={(event) => setCssBody(event.target.value)} rows={7} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" onClick={saveTemplate} disabled={busy}>Save Template</button>
          <button className="ghost" onClick={previewTemplate} disabled={busy}>Preview</button>
          <button className="ghost" onClick={inspectVariables} disabled={busy}>Inspect Variables</button>
          <button className="ghost" onClick={seedSamples} disabled={busy}>Seed Samples</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {variables.length ? <small>{variables.map((item) => item.name).join(', ')}</small> : null}
        </div>
        {previewHtml ? (
          <iframe className="email-preview" title="Template preview" srcDoc={previewHtml} />
        ) : null}
      </section>
      <section className="cards-grid full-span">
        {templates.length ? templates.map((template) => (
          <article className="panel entity-card" key={template.id}>
            <span>{template.category || 'template'}</span>
            <strong>{template.name}</strong>
            <p>{template.subject}</p>
            <button className="link-button" onClick={() => loadTemplateIntoEditor(template)}>Load in ESP editor</button>
          </article>
        )) : (
          <EmptyState title="No templates yet" detail="Seed sample templates or create one in the editor." actionHref="/template-editor" actionLabel="Open Template Editor" />
        )}
      </section>
    </section>
  );
}

function AnalyticsPage({ overview, campaigns, audiences, journeys }: {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  audiences: AudiencePerformance[];
  journeys: JourneyPerformance[];
}) {
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
  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        {metricsFromOverview(overview).map((metric) => <MetricCard metric={metric} key={metric.label} />)}
      </section>
      <section className="workflow-grid full-span">
        <article className="workflow-card">
          <span>Engagement</span>
          <strong>{formatPct(totalOpens / Math.max(totalSent, 1))} open rate</strong>
          <p>{formatInt(totalOpens)} opens from {formatInt(totalSent)} campaign sends in the current result set.</p>
          <a href="/admin/analytics">Open engagement report</a>
        </article>
        <article className="workflow-card">
          <span>Conversion</span>
          <strong>{formatPct(totalClicks / Math.max(totalSent, 1))} click rate</strong>
          <p>{formatInt(totalClicks)} clicks are visible across the loaded campaign performance data.</p>
          <a href="/admin/analytics">Open click report</a>
        </article>
        <article className="workflow-card">
          <span>Audience</span>
          <strong>{formatInt(totalAudienceReach)} reachable</strong>
          <p>Saved audiences are ready for campaign comparison and targeting analysis.</p>
          <a href="/admin/audiences">Compare audiences</a>
        </article>
        <article className="workflow-card">
          <span>Automation</span>
          <strong>{formatInt(activeEnrollments)} active enrollments</strong>
          <p>Journey health can be reviewed beside campaign and audience performance.</p>
          <a href="/admin/journeys">Open journeys</a>
        </article>
      </section>
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Campaign Performance</h2><a href="/admin/analytics">Open analytics</a></div>
        <p className="large-number">{formatInt(totalSent)}</p>
        <span className="muted">sent across {formatInt(campaigns.length)} campaigns</span>
      </section>
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Audience Reach</h2><a href="/admin/audiences">Open audiences</a></div>
        <p className="large-number">{formatInt(totalAudienceReach)}</p>
        <span className="muted">estimated contacts across saved audiences</span>
      </section>
      <section className="panel summary-panel">
        <div className="panel-head"><h2>Journey Health</h2><a href="/admin/journeys">Open journeys</a></div>
        <p className="large-number">{formatInt(activeEnrollments)}</p>
        <span className="muted">active journey enrollments</span>
      </section>
      <section className="panel table-panel full-span">
        <div className="panel-head"><h2>Top Campaigns</h2><a href="/admin/campaigns">Manage campaigns</a></div>
        {topCampaigns.length ? (
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
                <tr key={campaign.campaign_id}>
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
        ) : (
          <EmptyState title="No campaign analytics yet" detail="Launch a test campaign to populate campaign comparison reports." actionHref="/admin/campaigns" actionLabel="Open Campaign Manager" />
        )}
      </section>
      <section className="panel table-panel">
        <div className="panel-head"><h2>Audience Comparison</h2><a href="/admin/audiences">Open audiences</a></div>
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
        <div className="panel-head"><h2>Journey Risk</h2><a href="/admin/journeys">Open journeys</a></div>
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

function AiStudioPage({ insights, diagnostics }: { insights: Insight[]; diagnostics: SystemDiagnostics | null }) {
  const openAiReady = Boolean(diagnostics?.ai.openai_configured);
  const provider = diagnostics?.ai.provider || 'auto';
  const model = diagnostics?.ai.model || 'configured model';
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
          <a href="/template-editor">Open Template AI</a>
        </article>
        <article className="workflow-card">
          <span>Campaigns</span>
          <strong>Launch review</strong>
          <p>Assess template, audience, delivery, and readiness risks before sending a campaign.</p>
          <a href="/admin/campaigns">Review campaigns</a>
        </article>
        <article className="workflow-card">
          <span>Audience</span>
          <strong>Targeting recommendations</strong>
          <p>Find missing fields, narrow segments, and targeting opportunities from audience data.</p>
          <a href="/admin/audiences">Review audiences</a>
        </article>
        <article className="workflow-card">
          <span>Performance</span>
          <strong>Analytics analysis</strong>
          <p>Generate next-best actions from campaign, audience, journey, and delivery signals.</p>
          <a href="/admin/analytics">Analyze performance</a>
        </article>
      </section>
      <section className="panel full-span">
        <div className="panel-head"><h2>AI Insights</h2><a href="/admin/analytics">Open analytics</a></div>
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
            <tr><td>Draft template</td><td>/api/v1/ai/templates/draft</td><td><a href="/template-editor">Template Editor</a></td></tr>
            <tr><td>Edit template</td><td>/api/v1/ai/templates/edit</td><td><a href="/template-editor">Template Editor</a></td></tr>
            <tr><td>Campaign review</td><td>/api/v1/ai/campaigns/analyze</td><td><a href="/admin/campaigns">Campaign Manager</a></td></tr>
            <tr><td>Audience review</td><td>/api/v1/ai/audiences/analyze</td><td><a href="/admin/audiences">Audience Builder</a></td></tr>
            <tr><td>Journey review</td><td>/api/v1/ai/journeys/analyze</td><td><a href="/admin/journeys">Journey Manager</a></td></tr>
            <tr><td>Delivery review</td><td>/api/v1/ai/delivery/analyze</td><td><a href="/admin/delivery">Delivery Manager</a></td></tr>
          </tbody>
        </table>
      </section>
    </section>
  );
}

function IntegrationsPage({ diagnostics }: { diagnostics: SystemDiagnostics | null }) {
  const emailProvider = diagnostics?.email_provider.provider || 'unknown';
  const smtpReady = Boolean(diagnostics?.email_provider.smtp_configured);
  const sgReady = Boolean(diagnostics?.email_provider.sendgrid_configured);
  const baseUrl = diagnostics?.public_base_url || 'not configured';
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
          <a href="/admin/data-sources">Open Data Sources</a>
        </article>
        <article className="workflow-card">
          <span>Email</span>
          <strong>Provider readiness</strong>
          <p>Track SMTP and SG readiness without coupling the product workflow to one outbound provider.</p>
          <a href="/admin/system">Open diagnostics</a>
        </article>
        <article className="workflow-card">
          <span>Tracking</span>
          <strong>Domains and events</strong>
          <p>Review domain deliverability, opens, clicks, unsubscribes, and webhook event ingestion.</p>
          <a href="/admin/analytics">Open reports</a>
        </article>
        <article className="workflow-card">
          <span>Developer</span>
          <strong>API surface</strong>
          <p>Use OpenAPI docs to align SentientMail and other clients to Email Engine contracts.</p>
          <a href="/docs">Open API docs</a>
        </article>
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
    </section>
  );
}

function SettingsPage({ diagnostics }: { diagnostics: SystemDiagnostics | null }) {
  const counts = Object.entries(diagnostics?.entity_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
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
          <a href="/admin/system">Open diagnostics</a>
        </article>
        <article className="workflow-card">
          <span>Compliance</span>
          <strong>Suppressions</strong>
          <p>Manage unsubscribes, bounces, complaints, and suppression rules before campaign launch.</p>
          <a href="/admin/suppressions">Open suppressions</a>
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
  const [dashboard, setDashboard] = useState<DashboardState>({
    overview: null,
    campaigns: [],
    campaignItems: [],
    audiences: [],
    audienceItems: [],
    templates: [],
    journeys: [],
    journeyItems: [],
    diagnostics: null,
    aiInsights: fallbackInsights,
    loading: true,
    error: null,
  });

  useEffect(() => {
    function syncPage() {
      setActivePage(pageFromHash());
    }
    window.addEventListener('hashchange', syncPage);
    return () => window.removeEventListener('hashchange', syncPage);
  }, []);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const [overview, campaignData, campaignItems, audienceData, audienceItems, templateData, journeyData, journeyItems, diagnostics] = await Promise.all([
          fetchJson<AnalyticsOverview>('/api/v1/analytics/overview?recent_event_limit=25'),
          fetchJson<ListResponse<CampaignPerformance>>('/api/v1/analytics/campaigns?limit=10&offset=0'),
          fetchJson<ListResponse<CampaignRead>>('/api/v1/campaigns/list?limit=25&offset=0'),
          fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
          fetchJson<ListResponse<AudienceRead>>('/api/v1/audiences/list?limit=25&offset=0'),
          fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyRead>>('/api/v1/journeys/list?limit=25&offset=0'),
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
            audiences: audienceData.items || [],
            audienceItems: audienceItems.items || [],
            templates: templateData.items || [],
            journeys: journeyData.items || [],
            journeyItems: journeyItems.items || [],
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
            audiences: [],
            audienceItems: [],
            templates: [],
            journeys: [],
            journeyItems: [],
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
        />
      );
    }
    if (activePage === 'automations') {
      return (
        <AutomationsPage
          journeys={dashboard.journeys}
          journeyItems={dashboard.journeyItems}
          templates={dashboard.templates}
          onRefresh={async () => {
            const [journeyData, journeyItems] = await Promise.all([
              fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
              fetchJson<ListResponse<JourneyRead>>('/api/v1/journeys/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              journeys: journeyData.items || [],
              journeyItems: journeyItems.items || [],
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
          onRefresh={async () => {
            const [audienceData, audienceItems] = await Promise.all([
              fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
              fetchJson<ListResponse<AudienceRead>>('/api/v1/audiences/list?limit=25&offset=0'),
            ]);
            setDashboard((current) => ({
              ...current,
              audiences: audienceData.items || [],
              audienceItems: audienceItems.items || [],
            }));
          }}
        />
      );
    }
    if (activePage === 'templates') {
      return (
        <TemplatesPage
          templates={dashboard.templates}
          onRefresh={async () => {
            const templateData = await fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0');
            setDashboard((current) => ({
              ...current,
              templates: templateData.items || [],
            }));
          }}
        />
      );
    }
    if (activePage === 'ai-studio') return <AiStudioPage insights={dashboard.aiInsights} diagnostics={dashboard.diagnostics} />;
    if (activePage === 'analytics') {
      return (
        <AnalyticsPage
          overview={dashboard.overview}
          campaigns={dashboard.campaigns}
          audiences={dashboard.audiences}
          journeys={dashboard.journeys}
        />
      );
    }
    if (activePage === 'integrations') return <IntegrationsPage diagnostics={dashboard.diagnostics} />;
    if (activePage === 'settings') return <SettingsPage diagnostics={dashboard.diagnostics} />;
    return (
      <>
        <section className="metric-grid">
          {liveMetrics.map((metric) => <MetricCard metric={metric} key={metric.label} />)}
        </section>
        <section className="dashboard-grid">
          <PerformanceChart />
          <InsightsPanel insights={dashboard.aiInsights} />
        </section>
        <section className="lower-grid">
          <CampaignTable campaigns={liveCampaigns} />
          <QuickCreate />
        </section>
      </>
    );
  })();

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} />
      <main className="workspace">
        <Header title={pageTitle(activePage)} status={status} />
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
