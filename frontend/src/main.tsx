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

type DashboardState = {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  audiences: AudiencePerformance[];
  templates: TemplateRead[];
  journeys: JourneyPerformance[];
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

function CampaignsPage({ campaigns }: { campaigns: CampaignPerformance[] }) {
  return (
    <section className="page-grid">
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

function AutomationsPage({ journeys }: { journeys: JourneyPerformance[] }) {
  const failures = journeys.reduce((sum, item) =>
    sum + Number(item.failed_count || 0) + Number(item.step_failed_count || 0), 0);
  const queued = journeys.reduce((sum, item) => sum + Number(item.queued_send_count || 0), 0);
  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'Journeys', value: formatInt(journeys.length), change: 'total' }} />
        <MetricCard metric={{ label: 'Failures', value: formatInt(failures), change: 'needs review', tone: failures ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Queued sends', value: formatInt(queued), change: 'delivery backlog', tone: queued ? 'warn' : 'good' }} />
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

function AudiencePage({ audiences }: { audiences: AudiencePerformance[] }) {
  return (
    <section className="page-grid">
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

function TemplatesPage({ templates }: { templates: TemplateRead[] }) {
  return (
    <section className="page-grid cards-grid">
      {templates.length ? templates.map((template) => (
        <article className="panel entity-card" key={template.id}>
          <span>{template.category || 'template'}</span>
          <strong>{template.name}</strong>
          <p>{template.subject}</p>
          <a href={`/template-editor?template_id=${encodeURIComponent(template.id)}`}>Open editor</a>
        </article>
      )) : (
        <EmptyState title="No templates yet" detail="Seed sample templates or create one in the editor." actionHref="/template-editor" actionLabel="Open Template Editor" />
      )}
    </section>
  );
}

function AnalyticsPage({ overview, campaigns, audiences, journeys }: {
  overview: AnalyticsOverview | null;
  campaigns: CampaignPerformance[];
  audiences: AudiencePerformance[];
  journeys: JourneyPerformance[];
}) {
  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        {metricsFromOverview(overview).map((metric) => <MetricCard metric={metric} key={metric.label} />)}
      </section>
      <section className="panel">
        <div className="panel-head"><h2>Campaign Performance</h2><a href="/admin/analytics">Open analytics</a></div>
        <p className="large-number">{formatInt(campaigns.reduce((sum, item) => sum + item.sent_count, 0))}</p>
        <span className="muted">sent across {formatInt(campaigns.length)} campaigns</span>
      </section>
      <section className="panel">
        <div className="panel-head"><h2>Audience Reach</h2><a href="/admin/audiences">Open audiences</a></div>
        <p className="large-number">{formatInt(audiences.reduce((sum, item) => sum + item.estimated_count, 0))}</p>
        <span className="muted">estimated contacts across saved audiences</span>
      </section>
      <section className="panel">
        <div className="panel-head"><h2>Journey Health</h2><a href="/admin/journeys">Open journeys</a></div>
        <p className="large-number">{formatInt(journeys.reduce((sum, item) => sum + item.active_count, 0))}</p>
        <span className="muted">active journey enrollments</span>
      </section>
    </section>
  );
}

function AiStudioPage({ insights }: { insights: Insight[] }) {
  return (
    <section className="page-grid">
      <section className="panel">
        <div className="panel-head"><h2>AI Studio</h2><a href="/template-editor">Template AI</a></div>
        <div className="insights">
          {insights.map((item) => (
            <article className={`insight ${item.tone || ''}`} key={item.title}>
              <Icon label={item.title} />
              <div><strong>{item.title}</strong><p>{item.detail}</p><button className="link-button">{item.action}</button></div>
            </article>
          ))}
        </div>
      </section>
      <section className="panel quick-create">
        <h2>AI Workflows</h2>
        <a href="/template-editor">Template builder</a>
        <a href="/admin/campaigns">Campaign review</a>
        <a href="/admin/audiences">Audience recommendations</a>
        <a href="/admin/analytics">Performance analysis</a>
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
    audiences: [],
    templates: [],
    journeys: [],
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
        const [overview, campaignData, audienceData, templateData, journeyData] = await Promise.all([
          fetchJson<AnalyticsOverview>('/api/v1/analytics/overview?recent_event_limit=25'),
          fetchJson<ListResponse<CampaignPerformance>>('/api/v1/analytics/campaigns?limit=10&offset=0'),
          fetchJson<ListResponse<AudiencePerformance>>('/api/v1/analytics/audiences?limit=25&offset=0'),
          fetchJson<ListResponse<TemplateRead>>('/api/v1/templates/list?limit=25&offset=0'),
          fetchJson<ListResponse<JourneyPerformance>>('/api/v1/analytics/journeys?limit=25&offset=0'),
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
            audiences: audienceData.items || [],
            templates: templateData.items || [],
            journeys: journeyData.items || [],
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
            audiences: [],
            templates: [],
            journeys: [],
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
    if (activePage === 'campaigns') return <CampaignsPage campaigns={dashboard.campaigns} />;
    if (activePage === 'automations') return <AutomationsPage journeys={dashboard.journeys} />;
    if (activePage === 'audience') return <AudiencePage audiences={dashboard.audiences} />;
    if (activePage === 'templates') return <TemplatesPage templates={dashboard.templates} />;
    if (activePage === 'ai-studio') return <AiStudioPage insights={dashboard.aiInsights} />;
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
    if (activePage === 'integrations') {
      return (
        <SimpleModulePage
          title="Integrations"
          detail="Manage data sources, field mappings, imports, and provider configuration from the existing workbench while this product surface matures."
          links={[
            { label: 'Data Sources', href: '/admin/data-sources' },
            { label: 'System Diagnostics', href: '/admin/system' },
            { label: 'API Docs', href: '/docs' },
          ]}
        />
      );
    }
    if (activePage === 'settings') {
      return (
        <SimpleModulePage
          title="Settings"
          detail="Account, domain, compliance, authentication, and developer settings will move here as dedicated product pages."
          links={[
            { label: 'System Diagnostics', href: '/admin/system' },
            { label: 'Suppressions', href: '/admin/suppressions' },
            { label: 'API Docs', href: '/docs' },
          ]}
        />
      );
    }
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
