import { StrictMode } from 'react';
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
  revenue: string;
};

const navItems = [
  'Overview',
  'Campaigns',
  'Automations',
  'Audience',
  'Templates',
  'AI Studio',
  'Analytics',
  'Integrations',
  'Settings',
];

const metrics: Metric[] = [
  { label: 'Total sends', value: '128,540', change: '+18.4%' },
  { label: 'Open rate', value: '42.6%', change: '+7.3%' },
  { label: 'Click rate', value: '8.7%', change: '+3.6%' },
  { label: 'Revenue', value: '$24,780', change: '+21.6%' },
  { label: 'New contacts', value: '3,256', change: '+12.5%' },
];

const insights: Insight[] = [
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

const campaigns: Campaign[] = [
  {
    name: 'Spring Sale Announcement',
    status: 'Sent',
    sent: '32,450',
    openRate: '45.1%',
    clickRate: '9.1%',
    revenue: '$8,743',
  },
  {
    name: 'New Product Launch',
    status: 'Sent',
    sent: '28,124',
    openRate: '41.3%',
    clickRate: '8.3%',
    revenue: '$6,231',
  },
  {
    name: 'Weekly Newsletter',
    status: 'Sent',
    sent: '67,966',
    openRate: '42.0%',
    clickRate: '8.5%',
    revenue: '$9,806',
  },
];

const chartLines = [
  'M0,138 C40,86 64,98 94,76 C128,50 144,44 177,66 C205,84 228,46 256,36 C285,28 306,52 344,42 C373,36 396,18 430,30 C462,44 480,12 520,24',
  'M0,172 C42,142 74,154 104,128 C138,100 160,122 192,110 C224,98 238,72 274,88 C312,106 330,124 360,108 C396,90 416,72 448,92 C480,112 500,74 520,68',
  'M0,205 C52,184 78,198 112,176 C142,156 164,172 190,158 C228,134 252,150 282,136 C316,118 344,142 374,130 C414,112 448,122 520,98',
  'M0,235 C44,220 82,230 118,212 C156,194 182,206 214,192 C252,174 282,190 312,178 C348,160 388,176 424,158 C464,138 490,152 520,134',
];

function Icon({ label }: { label: string }) {
  return <span className="icon" aria-hidden="true">{label.slice(0, 1)}</span>;
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="mark">E</div>
        <span>Email Engine</span>
      </div>
      <nav>
        {navItems.map((item) => (
          <a className={item === 'Overview' ? 'active' : ''} href={`#${item.toLowerCase().replaceAll(' ', '-')}`} key={item}>
            <Icon label={item} />
            <span>{item}</span>
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

function Header() {
  return (
    <header className="topbar">
      <div>
        <h1>Overview</h1>
        <p>Welcome back. Here is what is happening across your ESP.</p>
      </div>
      <div className="topbar-actions">
        <label className="search">
          <span>Search</span>
          <input placeholder="Search campaigns, contacts, templates..." />
        </label>
        <button className="ghost">May 1 - May 31, 2026</button>
        <button className="primary">Create Campaign</button>
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

function InsightsPanel() {
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

function CampaignTable() {
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
            <th>Revenue</th>
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
              <td>{campaign.revenue}</td>
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

function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="workspace">
        <Header />
        <section className="metric-grid">
          {metrics.map((metric) => <MetricCard metric={metric} key={metric.label} />)}
        </section>
        <section className="dashboard-grid">
          <PerformanceChart />
          <InsightsPanel />
        </section>
        <section className="lower-grid">
          <CampaignTable />
          <QuickCreate />
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
