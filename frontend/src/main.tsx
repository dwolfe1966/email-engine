import { StrictMode, forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState, type CSSProperties, type DragEvent, type FormEvent, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { autocompletion, type CompletionContext } from '@codemirror/autocomplete';
import { html } from '@codemirror/lang-html';
import { basicSetup } from 'codemirror';
import { EditorSelection, EditorState, RangeSetBuilder } from '@codemirror/state';
import { Decoration, keymap, type DecorationSet, EditorView, ViewPlugin, type ViewUpdate } from '@codemirror/view';
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

type OverviewAction = {
  title: string;
  detail: string;
  href: string;
  tone: 'good' | 'warn';
};

type OperationNotice = {
  label: string;
  message: string;
  tone?: 'working' | 'success' | 'warn';
};

type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  role: string;
};

type AuthResponse = {
  user: AuthUser;
};

type OperatorUser = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  failed_login_count: number;
  locked_until: string | null;
  created_at: string;
};

type TemplateCodeEditorHandle = {
  focus: () => void;
  getSelectionRange: () => { from: number; to: number };
  setSelectionRange: (from: number, to: number) => void;
};

type TemplateEditSnapshot = {
  name: string;
  subject: string;
  htmlBody: string;
  cssBody: string;
  designDocJson: string;
};

type TemplateDesignBlock = {
  id: string;
  type: string;
  text?: string;
  html?: string;
  code?: string;
  className?: string;
  level?: number;
  align?: string;
  color?: string;
  href?: string;
  bg?: string;
  radius?: number;
  padding_y?: number;
  padding_x?: number;
  ordered?: boolean;
  items?: string[];
  table_headers?: string[];
  table_rows?: string[][];
  social_links?: Array<{ label: string; url: string }>;
  src?: string;
  alt?: string;
  width?: number;
  height?: number;
  gap?: number;
  mobile_stack?: 'stack' | 'keep' | 'reverse';
  children?: TemplateDesignBlock[];
};

type TemplateDesignDocument = {
  blocks: TemplateDesignBlock[];
};

type TemplateDesignHistoryEntry = {
  document: TemplateDesignDocument;
  selectedBlockId: string;
};

type DesignPaneWidths = {
  hierarchy: number;
  inspector: number;
};

const DEFAULT_DESIGN_PANE_WIDTHS: DesignPaneWidths = { hierarchy: 180, inspector: 300 };
const DESIGN_PANE_WIDTHS_STORAGE_KEY = 'email-engine.designPaneWidths';
const DESIGN_CANVAS_ZOOM_STORAGE_KEY = 'email-engine.designCanvasZoom';
const TEMPLATE_DRAFT_STORAGE_PREFIX = 'email-engine.templateDraft.';
const DESIGN_CANVAS_ZOOM_OPTIONS = [
  { label: '75%', value: '0.75' },
  { label: '100%', value: '1' },
  { label: '125%', value: '1.25' },
  { label: 'Fit', value: 'fit' },
] as const;

function readStoredDesignPaneWidths(): DesignPaneWidths {
  if (typeof window === 'undefined') return DEFAULT_DESIGN_PANE_WIDTHS;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(DESIGN_PANE_WIDTHS_STORAGE_KEY) || '');
    return {
      hierarchy: typeof parsed?.hierarchy === 'number' ? parsed.hierarchy : DEFAULT_DESIGN_PANE_WIDTHS.hierarchy,
      inspector: typeof parsed?.inspector === 'number' ? parsed.inspector : DEFAULT_DESIGN_PANE_WIDTHS.inspector,
    };
  } catch {
    return DEFAULT_DESIGN_PANE_WIDTHS;
  }
}

function readStoredDesignCanvasZoom(): string {
  if (typeof window === 'undefined') return '1';
  const stored = window.localStorage.getItem(DESIGN_CANVAS_ZOOM_STORAGE_KEY);
  return DESIGN_CANVAS_ZOOM_OPTIONS.some((option) => option.value === stored) ? stored || '1' : '1';
}

type TemplateLocalDraft = {
  name: string;
  subject: string;
  htmlBody: string;
  cssBody: string;
  designDoc: TemplateDesignDocument;
  editorMode: 'edit' | 'design' | 'preview';
  updatedAt: number;
};

function templateDraftStorageKey(templateId: string) {
  return `${TEMPLATE_DRAFT_STORAGE_PREFIX}${templateId || 'new'}`;
}

type TemplateCodeEditorProps = {
  value: string;
  onChange: (value: string) => void;
  onSelectionChange?: (from: number, to: number) => void;
  completions?: string[];
  cssClasses?: string[];
  onSave?: () => void;
  onFormat?: () => void;
};

const jinjaDecorations = ViewPlugin.fromClass(class {
  decorations: DecorationSet;

  constructor(view: EditorView) {
    this.decorations = this.buildDecorations(view);
  }

  update(update: ViewUpdate) {
    if (update.docChanged || update.viewportChanged) {
      this.decorations = this.buildDecorations(update.view);
    }
  }

  buildDecorations(view: EditorView) {
    const builder = new RangeSetBuilder<Decoration>();
    const matcher = /({#[\s\S]*?#}|{%-?[\s\S]*?-?%}|{{[\s\S]*?}})/g;
    for (const { from, to } of view.visibleRanges) {
      const text = view.state.doc.sliceString(from, to);
      matcher.lastIndex = 0;
      let match: RegExpExecArray | null;
      while ((match = matcher.exec(text))) {
        const token = match[0];
        const className = token.startsWith('{{')
          ? 'cm-jinja-variable'
          : token.startsWith('{#')
            ? 'cm-jinja-comment'
            : 'cm-jinja-block';
        builder.add(from + match.index, from + match.index + token.length, Decoration.mark({ class: className }));
      }
    }
    return builder.finish();
  }
}, {
  decorations: (plugin) => plugin.decorations,
});

const templateEditorTheme = EditorView.theme({
  '&': {
    border: '1px solid #d7e1ef',
    borderRadius: '8px',
    overflow: 'hidden',
    backgroundColor: '#ffffff',
    fontSize: '13px',
  },
  '.cm-content': {
    minHeight: '300px',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
  },
  '.cm-scroller': {
    minHeight: '300px',
    maxHeight: '520px',
  },
  '.cm-gutters': {
    backgroundColor: '#f8fafc',
    color: '#718096',
    borderRight: '1px solid #e2e8f0',
  },
  '.cm-activeLineGutter, .cm-activeLine': {
    backgroundColor: '#f1f7ff',
  },
  '.cm-focused': {
    outline: '2px solid rgba(79, 70, 229, 0.18)',
  },
});

const TemplateCodeEditor = forwardRef<TemplateCodeEditorHandle, TemplateCodeEditorProps>(function TemplateCodeEditor(
  { value, onChange, onSelectionChange, completions = [], cssClasses = [], onSave, onFormat },
  ref,
) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  const onSelectionChangeRef = useRef(onSelectionChange);
  const completionsRef = useRef(completions);
  const cssClassesRef = useRef(cssClasses);
  const onSaveRef = useRef(onSave);
  const onFormatRef = useRef(onFormat);

  onChangeRef.current = onChange;
  onSelectionChangeRef.current = onSelectionChange;
  completionsRef.current = completions;
  cssClassesRef.current = cssClasses;
  onSaveRef.current = onSave;
  onFormatRef.current = onFormat;

  useImperativeHandle(ref, () => ({
    focus: () => viewRef.current?.focus(),
    getSelectionRange: () => {
      const selection = viewRef.current?.state.selection.main;
      return { from: selection?.from ?? value.length, to: selection?.to ?? value.length };
    },
    setSelectionRange: (from: number, to: number) => {
      const view = viewRef.current;
      if (!view) return;
      view.dispatch({
        selection: EditorSelection.range(from, to),
        scrollIntoView: true,
      });
      view.focus();
    },
  }), [value.length]);

  useEffect(() => {
    if (!hostRef.current) return;
    const completionSource = (context: CompletionContext) => {
      const word = context.matchBefore(/[\w.{%-]*/);
      if (!word || (word.from === word.to && !context.explicit)) return null;
      const variableOptions = completionsRef.current.map((label) => ({
        label,
        detail: 'variable',
        type: 'variable',
        apply: `{{ ${label} }}`,
      }));
      const classOptions = cssClassesRef.current.map((label) => ({
        label,
        detail: 'CSS class',
        type: 'class',
        apply: label,
      }));
      const snippetOptions = [
        { label: 'if', detail: 'Jinja block', type: 'keyword', apply: '{% if condition %}\n  \n{% endif %}' },
        { label: 'ifelse', detail: 'Jinja branch', type: 'keyword', apply: '{% if condition %}\n  \n{% else %}\n  \n{% endif %}' },
        { label: 'for', detail: 'Jinja loop', type: 'keyword', apply: '{% for item in items %}\n  {{ item }}\n{% endfor %}' },
        { label: 'set', detail: 'Jinja assignment', type: 'keyword', apply: '{% set name = value %}' },
        { label: 'unsubscribe_url', detail: 'native variable', type: 'variable', apply: '{{ unsubscribe_url }}' },
        { label: 'tracking_click', detail: 'native variable', type: 'variable', apply: '{{ tracking_click }}' },
        { label: 'tracking_open', detail: 'native variable', type: 'variable', apply: '{{ tracking_open }}' },
      ];
      const htmlOptions = [
        { label: 'email-container', detail: 'wrapper class', type: 'class', apply: 'email-container' },
        { label: 'email-copy', detail: 'text class', type: 'class', apply: 'email-copy' },
        { label: 'email-title', detail: 'heading class', type: 'class', apply: 'email-title' },
        { label: 'button', detail: 'CTA class', type: 'class', apply: 'button' },
      ];
      return {
        from: word.from,
        options: [...variableOptions, ...classOptions, ...htmlOptions, ...snippetOptions],
      };
    };
    const view = new EditorView({
      parent: hostRef.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          html(),
          jinjaDecorations,
          autocompletion({ override: [completionSource] }),
          templateEditorTheme,
          EditorView.lineWrapping,
          keymap.of([
            {
              key: 'Mod-s',
              run: () => {
                onSaveRef.current?.();
                return true;
              },
            },
            {
              key: 'Shift-Mod-f',
              run: () => {
                onFormatRef.current?.();
                return true;
              },
            },
          ]),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              onChangeRef.current(update.state.doc.toString());
            }
            if (update.selectionSet || update.docChanged) {
              const selection = update.state.selection.main;
              onSelectionChangeRef.current?.(selection.from, selection.to);
            }
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current === value) return;
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
    });
  }, [value]);

  return <div className="template-code-editor" ref={hostRef} />;
});

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

type DomainDeliveryPolicyRead = {
  id: string;
  domain: string;
  route_id: string | null;
  max_per_minute: number | null;
  max_concurrent: number | null;
  warmup_stage: string | null;
  paused_until: string | null;
  metadata_json: Record<string, unknown>;
};

type DomainReputationDashboardRead = {
  domain: string;
  route_id: string | null;
  route_name: string | null;
  route_type: string | null;
  warmup_stage: string | null;
  ip_pool: string | null;
  max_per_minute: number | null;
  max_concurrent: number | null;
  paused_until: string | null;
  authentication_status: string;
  reputation_status: string;
  throttle_status: string;
  compliance_status: string;
  compliance_reason: string | null;
  bounce_rate: number;
  complaint_rate: number;
  send_record_count: number;
  recommendations: string[];
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

type CampaignLaunchResult = {
  job_id: string;
  campaign_id: string;
  audience_snapshot_id: string | null;
  status: string;
  requested_count: number;
  queued_count: number;
  suppressed_count: number;
  dry_run: boolean;
};

type CampaignTestSendResult = {
  provider: string;
  provider_message_id: string | null;
  status_code: number;
  subject: string | null;
  campaign_id: string;
  template_id: string;
  send_job_id: string;
  send_record_id: string;
  contact_id: string;
  to_email?: string;
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
  dead_lettered_count: number;
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

const queuedDeliveryStatuses = ['queued', 'deferred'];
const acceptedDeliveryStatuses = ['sent', 'submitted', 'delivered'];
const failedDeliveryStatuses = ['failed', 'bounced'];
const suppressedDeliveryStatuses = ['suppressed', 'complained', 'unsubscribed'];
const blockedDeliveryStatuses = [
  ...failedDeliveryStatuses,
  ...suppressedDeliveryStatuses,
  'skipped',
  'dead_lettered',
];

function countRecordsByStatus(records: EmailSendRecordRead[], statuses: string[]) {
  return records.filter((record) => statuses.includes(record.status)).length;
}

type DeliveryRun = {
  claimed_count: number;
  sent_count: number;
  failed_count: number;
  processed_record_ids: string[];
  skipped_count: number;
  skipped_record_ids: string[];
};

type DeliveryAttemptRead = {
  id: string;
  send_record_id: string;
  send_job_id: string | null;
  campaign_id: string | null;
  attempt_number: number;
  provider: string | null;
  route_type: string | null;
  route_key: string | null;
  status: string;
  provider_message_id: string | null;
  smtp_response_code: number | null;
  smtp_response: string | null;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
};

type ProviderFeedbackEventRead = {
  id: string;
  provider: string;
  source: string;
  event_name: string;
  email: string;
  provider_message_id: string | null;
  idempotency_key: string;
  payload_json: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  received_at: string;
};

type ManagedSmtpReadinessCheckRead = {
  id: string;
  source: string;
  check_type: string;
  status: string;
  domain: string | null;
  host: string | null;
  summary: string | null;
  result_json: Record<string, unknown>;
  created_at: string;
};

type ManagedSmtpReadinessSummaryRead = {
  total_count: number;
  ok_count: number;
  warning_count: number;
  failed_count: number;
  latest_check: ManagedSmtpReadinessCheckRead | null;
  latest_success: ManagedSmtpReadinessCheckRead | null;
};

type ManagedSmtpReadinessTrendRead = {
  sample_size: number;
  ok_count: number;
  warning_count: number;
  failed_count: number;
  ok_rate: number;
  failure_rate: number;
  trend: string;
  alert_status: string;
  alert_reasons: string[];
  latest_window_failure_rate: number;
  previous_window_failure_rate: number;
  recent_checks: ManagedSmtpReadinessCheckRead[];
};

type ManagedSmtpReadinessAlertsRead = {
  alert_status: string;
  alert_reasons: string[];
  alert_count: number;
  trend: ManagedSmtpReadinessTrendRead;
  alert_checks: ManagedSmtpReadinessCheckRead[];
};

type ManagedSmtpReadinessNotificationRead = {
  should_notify: boolean;
  severity: string;
  title: string;
  message: string;
  dedupe_key: string;
  alert_status: string;
  alert_reasons: string[];
  alert_count: number;
  latest_alert_check: ManagedSmtpReadinessCheckRead | null;
  alerts: ManagedSmtpReadinessAlertsRead;
};

type ManagedSmtpResolvedRoute = {
  domain: string;
  delivery_route_id: string;
  delivery_route_name: string;
  domain_policy_id: string;
  ip_pool_id: string;
  ip_pool_name: string;
  ip_pool_type: string;
  mta_node_id: string;
  mta_node_name: string;
  provider_account_id: string;
  provider: string;
  hostname: string;
  public_ipv4: string | null;
  submission_host: string;
  submission_port: number;
  auth_secret_ref: string | null;
  envelope_sender_domain: string | null;
  dkim_selector: string | null;
  telemetry_tags: Record<string, unknown>;
};

type ManagedSmtpRouteResolutionRead = {
  ok: boolean;
  route: ManagedSmtpResolvedRoute | null;
  reason: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  } | null;
};

type MtaInventoryCounts = {
  total: number;
  pending: number;
  active: number;
  paused: number;
  draining: number;
  failed: number;
  retired: number;
  suspended: number;
};

type MtaProviderAccountRead = {
  id: string;
  name: string;
  provider: string;
  status: string;
  account_ref: string | null;
  region: string | null;
  abuse_contact_email: string | null;
  support_case_ref: string | null;
  port25_status: string;
  rdns_status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type MtaNodeRead = {
  id: string;
  provider_account_id: string;
  name: string;
  hostname: string;
  public_ipv4: string | null;
  status: string;
  submission_host: string | null;
  submission_port: number;
  last_readiness_at: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type MtaIpPoolNodeRead = {
  id: string;
  ip_pool_id: string;
  mta_node_id: string;
  priority: number;
  weight: number;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type ManagedSmtpDeploymentNodeSummary = {
  node: MtaNodeRead;
  provider_account: MtaProviderAccountRead | null;
  pool_memberships: MtaIpPoolNodeRead[];
  readiness_summary: ManagedSmtpReadinessSummaryRead;
};

type ManagedSmtpDeploymentSummaryRead = {
  provider_accounts: MtaInventoryCounts;
  nodes: MtaInventoryCounts;
  ip_pools: MtaInventoryCounts;
  pool_nodes: MtaInventoryCounts;
  submission_credentials_configured: boolean;
  submission_tls_enabled: boolean;
  managed_smtp_route_count: number;
  managed_smtp_domain_policy_count: number;
  recent_nodes: ManagedSmtpDeploymentNodeSummary[];
};

type ManagedSmtpFirstSendChecklistItem = {
  key: string;
  label: string;
  status: string;
  value: string;
  detail: string;
  blocking: boolean;
};

type ManagedSmtpFirstSendRead = {
  ok: boolean;
  status: string;
  blockers: string[];
  items: ManagedSmtpFirstSendChecklistItem[];
  deployment_summary: ManagedSmtpDeploymentSummaryRead;
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

type TemplateDocumentRead = {
  template_id: string;
  version_id: string | null;
  version_number: number | null;
  document_json: Record<string, unknown>;
};

type TemplateDocumentImportRead = {
  document_json: Record<string, unknown>;
  block_count: number;
  raw_block_count: number;
};

type TemplateVersionRead = {
  id: string;
  template_id: string;
  version_number: number;
  subject: string;
  html_body: string;
  css_body: string | null;
  text_body: string | null;
  document_json: Record<string, unknown>;
  is_current: boolean;
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

const AI_ACTION_BRIEF_STORAGE_KEY = 'esp_ai_action_brief';

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

function RowActionMenu({ openHref, onDelete, onArchive }: {
  openHref: string;
  onDelete?: () => void;
  onArchive?: () => void;
}) {
  return (
    <details className="row-action-menu" onClick={(event) => event.stopPropagation()}>
      <summary>Actions</summary>
      <div>
        <a href={openHref}>Open</a>
        <button type="button" onClick={onDelete || (() => window.alert('Delete is not wired for this entity yet.'))}>Delete</button>
        <button type="button" onClick={onArchive || (() => window.alert('Archive is not wired for this entity yet.'))}>Archive</button>
      </div>
    </details>
  );
}

function formatInt(value: number | undefined) {
  return Number(value || 0).toLocaleString();
}

function escapeTemplateText(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function decodeTemplateText(value: unknown) {
  return String(value ?? '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/&nbsp;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/<[^>]+>/g, '')
    .trim();
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

class AuthRequiredError extends Error {
  constructor(message = 'Not authenticated') {
    super(message);
    this.name = 'AuthRequiredError';
  }
}

let authRequiredHandler: (() => void) | null = null;

function onAuthRequired(handler: (() => void) | null) {
  authRequiredHandler = handler;
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  const detail =
    data && typeof data === 'object' && 'detail' in data
      ? String((data as { detail?: unknown }).detail || '')
      : text;
  if (response.status === 401) {
    authRequiredHandler?.();
    throw new AuthRequiredError(detail || 'Not authenticated');
  }
  if (!response.ok) {
    throw new Error(detail || `${path} failed`);
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

function initialsForUser(user: AuthUser | null) {
  const source = user?.display_name || user?.email || 'Operator';
  return source
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'OP';
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

function Header({
  title,
  status,
  operation,
  activePage,
  user,
  onLogout,
}: {
  title: string;
  status: string;
  operation: OperationNotice;
  activePage: PageKey;
  user: AuthUser | null;
  onLogout: () => void;
}) {
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
        <div className="topbar-profile">
          <div className="avatar topbar-avatar">{initialsForUser(user)}</div>
          <div>
            <strong>{user?.display_name || 'Operator'}</strong>
            <span>{user?.email || 'email-engine.app'}</span>
          </div>
          {user ? <button type="button" className="profile-logout" onClick={onLogout}>Sign out</button> : null}
        </div>
      </div>
    </header>
  );
}

function LoginScreen({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = await fetchJson<AuthResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      onLogin(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand login-brand">
          <div className="mark">E</div>
          <span>Email Engine</span>
        </div>
        <form className="login-form" onSubmit={submitLogin}>
          <h1>Sign in</h1>
          <label>
            Email
            <input
              autoComplete="email"
              autoFocus
              inputMode="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <div className="login-error">{error}</div> : null}
          <button className="primary" disabled={submitting} type="submit">
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
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
    <section className="panel table-panel overview-campaigns">
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

function OverviewStatusStrip({
  provider,
  providerReady,
  schemaOk,
  queuedRecords,
  failedRecords,
  failedImports,
  activeEnrollments,
}: {
  provider: string;
  providerReady: boolean;
  schemaOk: boolean;
  queuedRecords: number;
  failedRecords: number;
  failedImports: number;
  activeEnrollments: number;
}) {
  return (
    <section className="overview-status-strip">
      <a className={providerReady ? 'good' : 'warn'} href="#integrations">
        <span>Provider</span>
        <strong>{providerLabel(provider)}</strong>
      </a>
      <a className={schemaOk ? 'good' : 'warn'} href="#settings">
        <span>System</span>
        <strong>{schemaOk ? 'Schema ready' : 'Schema review'}</strong>
      </a>
      <a className={queuedRecords || failedRecords ? 'warn' : 'good'} href="#delivery">
        <span>Delivery</span>
        <strong>{formatInt(queuedRecords)} queued / {formatInt(failedRecords)} failed</strong>
      </a>
      <a className={failedImports ? 'warn' : 'good'} href="#data">
        <span>Imports</span>
        <strong>{formatInt(failedImports)} failed</strong>
      </a>
      <a className="good" href="#automations">
        <span>Journeys</span>
        <strong>{formatInt(activeEnrollments)} active</strong>
      </a>
    </section>
  );
}

function NextActionPanel({ actions }: { actions: OverviewAction[] }) {
  const primary = actions.find((item) => item.tone === 'warn') || actions[0];
  return (
    <section className={`panel overview-next-action ${primary.tone}`}>
      <div className="panel-head"><h2>Recommended next action</h2><a href={primary.href}>Open</a></div>
      <strong>{primary.title}</strong>
      <p>{primary.detail}</p>
      <div className="overview-action-list">
        {actions.slice(0, 4).map((item) => (
          <a className={item.tone} href={item.href} key={item.title}>
            <span>{item.title}</span>
            <small>{item.detail}</small>
          </a>
        ))}
      </div>
    </section>
  );
}

function OverviewPage({ dashboard, metrics, campaigns }: {
  dashboard: DashboardState;
  metrics: Metric[];
  campaigns: Campaign[];
}) {
  const queuedRecords = countRecordsByStatus(dashboard.sendRecords, queuedDeliveryStatuses);
  const failedRecords = countRecordsByStatus(dashboard.sendRecords, failedDeliveryStatuses);
  const activeJobs = dashboard.sendJobs.filter((job) => !['completed', 'failed', 'cancelled'].includes(job.status)).length;
  const failedImports = dashboard.importJobs.filter((job) => job.status === 'failed').length;
  const importedRows = dashboard.importJobs.reduce((sum, job) => sum + Number(job.imported_count || 0), 0);
  const activeEnrollments = dashboard.journeyEnrollments.filter((enrollment) => enrollment.status === 'active').length;
  const failedExecutions = dashboard.journeyExecutions.filter((execution) => execution.status === 'failed').length;
  const attributeKeys = dashboard.contactMeta?.attribute_keys || [];
  const topSource = dashboard.contactMeta?.sources?.[0];
  const provider = dashboard.diagnostics?.email_provider.provider || 'unknown';
  const smtpReady = Boolean(dashboard.diagnostics?.email_provider.smtp_configured);
  const sendgridReady = Boolean(dashboard.diagnostics?.email_provider.sendgrid_configured);
  const aiReady = Boolean(dashboard.diagnostics?.ai.openai_configured);
  const providerReady = Boolean(
    smtpReady ||
    sendgridReady ||
    provider === 'console',
  );
  const schemaOk = Boolean(dashboard.diagnostics?.schema.ok);
  const activeDataSources = dashboard.dataSources.filter((source) => source.status === 'active').length;
  const providerLinkedSuppressions = dashboard.suppressions.filter((item) => item.provider_message_id).length;
  const readinessMetrics = metrics.slice(0, 4);
  const riskItems: OverviewAction[] = [
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
  const workflowLinks = [
    { label: 'Import contacts', href: '#data', detail: `${formatInt(dashboard.dataSources.length)} sources` },
    { label: 'Create template', href: '#templates', detail: `${formatInt(dashboard.templates.length)} templates` },
    { label: 'Build audience', href: '#audience', detail: `${formatInt(dashboard.audienceItems.length)} audiences` },
    { label: 'Launch campaign', href: '#campaigns', detail: `${formatInt(dashboard.campaignItems.length)} campaigns` },
    { label: 'Review reports', href: '#analytics', detail: `${formatInt(dashboard.overview?.event_count || 0)} events` },
  ];
  const overviewTriageAction = !schemaOk
    ? {
      tone: 'warn',
      title: 'Resolve schema readiness',
      detail: 'System schema should be current before treating dashboard workflow state as production-ready.',
      actionLabel: 'Open Settings',
      href: '#settings',
    }
    : !providerReady
      ? {
        tone: 'warn',
        title: 'Configure outbound provider',
        detail: 'Campaign launch and test-send workflows need a configured delivery provider path.',
        actionLabel: 'Open Integrations',
        href: '#integrations',
      }
      : !smtpReady
        ? {
          tone: 'warn',
          title: 'Plan owned SMTP',
          detail: 'Owned SMTP remains a platform foundation gap even while provider adapters are available.',
          actionLabel: 'Open Integrations',
          href: '#integrations',
        }
        : queuedRecords || failedRecords || activeJobs
          ? {
            tone: 'warn',
            title: 'Review delivery pressure',
            detail: `${formatInt(queuedRecords)} queued, ${formatInt(failedRecords)} failed, and ${formatInt(activeJobs)} active job(s) need delivery follow-up.`,
            actionLabel: 'Open Delivery',
            href: '#delivery',
          }
          : failedImports
            ? {
              tone: 'warn',
              title: 'Review import failures',
              detail: `${formatInt(failedImports)} failed import job(s) can affect contacts, audiences, and personalization.`,
              actionLabel: 'Open Data Sources',
              href: '#data',
            }
            : failedExecutions
              ? {
                tone: 'warn',
                title: 'Review journey failures',
                detail: `${formatInt(failedExecutions)} failed journey execution(s) need automation or delivery review.`,
                actionLabel: 'Open Journeys',
                href: '#automations',
              }
              : !aiReady
                ? {
                  tone: 'warn',
                  title: 'Configure AI handoff',
                  detail: 'AI Studio is available in fallback mode; configure OpenAI for production agent workflows.',
                  actionLabel: 'Open AI Studio',
                  href: '#ai-studio',
                }
                : {
                  tone: 'good',
                  title: 'Workspace ready',
                  detail: 'Schema, provider, owned SMTP, delivery, imports, journeys, and AI handoff are clear.',
                  actionLabel: 'Open Reports',
                  href: '#analytics',
                };
  const overviewTriageItems = [
    {
      label: 'Provider',
      value: providerReady ? providerLabel(provider) : 'Pending',
      detail: smtpReady ? 'Owned SMTP configured' : sendgridReady ? 'Provider adapter ready' : 'No outbound path configured',
      tone: providerReady ? 'good' : 'warn',
    },
    {
      label: 'Owned SMTP',
      value: smtpReady ? 'Ready' : 'Gap',
      detail: smtpReady ? 'Managed SMTP path configured' : 'First-class SMTP foundation still missing',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Delivery',
      value: `${formatInt(queuedRecords)} / ${formatInt(failedRecords)}`,
      detail: `${formatInt(activeJobs)} active send job(s) loaded`,
      tone: queuedRecords || failedRecords || activeJobs ? 'warn' : 'good',
    },
    {
      label: 'Imports',
      value: formatInt(failedImports),
      detail: `${formatInt(importedRows)} imported row(s) loaded`,
      tone: failedImports ? 'warn' : 'good',
    },
    {
      label: 'AI handoff',
      value: aiReady ? 'Ready' : 'Fallback',
      detail: dashboard.diagnostics?.ai.model || 'Deterministic fallback available',
      tone: aiReady ? 'good' : 'warn',
    },
  ];
  const platformFoundationItems = [
    {
      label: 'Data model',
      value: activeDataSources ? 'Active' : 'Gap',
      detail: activeDataSources ? `${formatInt(activeDataSources)} active source(s), ${formatInt(attributeKeys.length)} attribute key(s)` : 'Activate data sources and model client-owned entities.',
      tone: activeDataSources ? 'good' : 'warn',
    },
    {
      label: 'Send engine',
      value: smtpReady ? 'Owned SMTP' : providerReady ? 'Adapter' : 'Gap',
      detail: smtpReady ? 'Owned SMTP path configured' : providerReady ? 'Provider adapter available; owned SMTP still missing' : 'SMTP server, queues, and throttle controls still need foundation work.',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Feedback loop',
      value: providerLinkedSuppressions ? 'Linked' : dashboard.suppressions.length ? 'Manual' : 'Gap',
      detail: providerLinkedSuppressions ? `${formatInt(providerLinkedSuppressions)} provider-linked suppression(s)` : 'Bounce and complaint events need durable webhook-backed feedback.',
      tone: providerLinkedSuppressions ? 'good' : 'warn',
    },
    {
      label: 'Agent layer',
      value: aiReady ? 'Configured' : 'Fallback',
      detail: aiReady ? `${dashboard.diagnostics?.ai.provider || 'AI'} ${dashboard.diagnostics?.ai.model || ''}` : 'Production agents need OpenAI configuration and persistent workflow memory.',
      tone: aiReady ? 'good' : 'warn',
    },
  ];

  return (
    <>
      <section className="overview-hero">
        <div>
          <span>Executive overview</span>
          <h2>Email program command center</h2>
          <p>Live campaign, audience, delivery, and system health in one workspace.</p>
        </div>
        <div className="overview-hero-actions">
          <a className="primary" href="#campaigns/new">Create Campaign</a>
          <a className="ghost" href="#analytics">Open Reports</a>
        </div>
      </section>
      <section className="metric-grid overview-metrics">
        {readinessMetrics.map((metric) => <MetricCard metric={metric} key={metric.label} />)}
      </section>
      <OverviewStatusStrip
        activeEnrollments={activeEnrollments}
        failedImports={failedImports}
        failedRecords={failedRecords}
        provider={provider}
        providerReady={providerReady}
        queuedRecords={queuedRecords}
        schemaOk={schemaOk}
      />
      <section className={`overview-triage-panel ${overviewTriageAction.tone}`}>
        <div className="overview-triage-head">
          <div>
            <span>Workspace triage</span>
            <strong>{overviewTriageAction.title}</strong>
            <small>{overviewTriageAction.detail}</small>
          </div>
          <a className={overviewTriageAction.tone === 'warn' ? 'primary' : 'ghost'} href={overviewTriageAction.href}>{overviewTriageAction.actionLabel}</a>
        </div>
        <div className="overview-triage-list">
          {overviewTriageItems.map((item) => (
            <article className={`overview-triage-row ${item.tone}`} key={item.label}>
              <div>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="overview-foundation-panel">
        <div className="panel-head compact-head">
          <div>
            <h3>Platform Foundations</h3>
            <span className="muted">Data model, send engine, feedback loop, and agent layer readiness.</span>
          </div>
          <a href="#integrations">Open Integrations</a>
        </div>
        <div className="overview-foundation-strip">
          {platformFoundationItems.map((item) => (
            <article className={`overview-foundation-item ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="overview-main-grid">
        <NextActionPanel actions={riskItems} />
        <section className="panel overview-audience-card">
          <div className="panel-head"><h2>Audience readiness</h2><a href="#contacts">Contacts</a></div>
          <p className="large-number">{formatInt(dashboard.contactMeta?.total || dashboard.contacts.length)}</p>
          <span className="muted">contacts across {formatInt(dashboard.contactMeta?.sources.length || 0)} sources</span>
          <div className="module-links">
            <a href="#contacts">{formatInt(attributeKeys.length)} attribute keys</a>
            <a href="#audience">{formatInt(dashboard.audienceItems.length)} audiences</a>
            <a href="#data">{topSource ? `${topSource.source}: ${formatInt(topSource.count)}` : 'No top source'}</a>
          </div>
        </section>
        <section className="panel overview-workflows">
          <div className="panel-head"><h2>Run workflow</h2><a href="#docs">API docs</a></div>
          <div>
            {workflowLinks.map((item) => (
              <a href={item.href} key={item.label}>
                <span>{item.label}</span>
                <small>{item.detail}</small>
              </a>
            ))}
          </div>
        </section>
      </section>
      <section className="overview-lower-grid">
        <CampaignTable campaigns={campaigns} />
        <section className="panel overview-snapshot">
          <div className="panel-head"><h2>Platform snapshot</h2><a href="#settings">Settings</a></div>
          <dl>
            <div><dt>Provider</dt><dd>{providerLabel(provider)}</dd></div>
            <div><dt>Schema</dt><dd>{dashboard.diagnostics?.schema.current_revision || 'unknown'}</dd></div>
            <div><dt>Send jobs</dt><dd>{formatInt(activeJobs)} active</dd></div>
            <div><dt>Imported rows</dt><dd>{formatInt(importedRows)}</dd></div>
          </dl>
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
  const [lastLaunchResult, setLastLaunchResult] = useState<CampaignLaunchResult | null>(null);
  const [lastTestSendResult, setLastTestSendResult] = useState<CampaignTestSendResult | null>(null);
  const [aiCampaignSummary, setAiCampaignSummary] = useState<string[]>([]);
  const [aiCampaignRecommendations, setAiCampaignRecommendations] = useState<AIWorkflowAnalysis['recommendations']>([]);

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
  const isPersistedCampaign = Boolean(selectedCampaignId);
  const isCreatingCampaign = !isPersistedCampaign;
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
  const readyCount = readinessCards.filter((item) => item.ready).length;
  const readinessScore = Math.round((readyCount / Math.max(readinessCards.length, 1)) * 100);
  const validationErrors = workflowStatus?.validation?.errors || [];
  const validationWarnings = workflowStatus?.validation?.warnings || [];
  const latestJob = workflowStatus?.latest_send_job;
  const latestRequested = Number(latestJob?.requested_count || selectedCampaignPerformance?.requested_count || 0);
  const latestProcessed = Number((selectedCampaignPerformance?.sent_count || 0) + (selectedCampaignPerformance?.failed_count || 0) + (latestJob?.suppressed_count || 0));
  const latestProgressPct = latestRequested ? Math.min(100, Math.round((latestProcessed / latestRequested) * 100)) : 0;
  const nextCampaignAction = !selectedCampaignId
    ? 'Save the draft campaign before preview, test send, or launch.'
    : !selectedTemplate
      ? 'Choose a template for the campaign.'
      : !selectedAudience
        ? 'Choose an audience and confirm contact volume.'
        : !workflowStatus
          ? 'Run readiness before launch.'
          : validationErrors.length
            ? 'Resolve validation errors before sending.'
            : !testEmail.trim()
              ? 'Enter a test recipient and send a test email.'
              : 'Ready for test send or dry-run launch.';
  const campaignNextStep = !workflowStatus
    ? {
      label: 'Run readiness',
      detail: 'Load validation, audience, analytics, and latest delivery state before launch.',
      actionLabel: 'Refresh Readiness',
      run: loadCampaignWorkflowStatus,
    }
    : validationErrors.length
      ? {
        label: 'Fix validation blockers',
        detail: `${formatInt(validationErrors.length)} error(s) must be cleared before sending.`,
        actionLabel: 'Check Audience',
        run: validateCampaign,
      }
      : !testEmail.trim()
        ? {
          label: 'Preview test content',
          detail: 'Review rendered campaign content, then add a recipient for test send.',
          actionLabel: 'Preview Email',
          run: previewTestEmail,
        }
        : {
          label: 'Dry-run launch',
          detail: 'Simulate launch volume and suppression counts before production queueing.',
          actionLabel: 'Dry-Run Launch',
          run: dryRunLaunch,
        };
  const campaignTriageAction = !selectedCampaignId
    ? {
      tone: 'warn',
      title: 'Create campaign draft',
      detail: 'Save the campaign before previewing, test sending, dry-running, or launching.',
      actionLabel: 'Create Campaign',
      run: createDraftCampaign,
      disabled: operationBusy || !templateId,
    }
    : !selectedTemplate
      ? {
        tone: 'warn',
        title: 'Choose template',
        detail: 'Campaign launch needs a saved template with subject, HTML, tracking, and unsubscribe content.',
        actionLabel: 'Open Templates',
        run: () => { window.location.hash = '#templates'; },
        disabled: operationBusy,
      }
      : !selectedAudience
        ? {
          tone: 'warn',
          title: 'Choose audience',
          detail: 'Campaign launch needs a saved audience so volume, suppressions, and snapshots can be checked.',
          actionLabel: 'Open Audiences',
          run: () => { window.location.hash = '#audience'; },
          disabled: operationBusy,
        }
        : !workflowStatus
          ? {
            tone: 'warn',
            title: 'Run readiness',
            detail: 'Load validation, audience, analytics, and latest delivery state before sending.',
            actionLabel: 'Refresh Readiness',
            run: loadCampaignWorkflowStatus,
            disabled: operationBusy,
          }
          : validationErrors.length
            ? {
              tone: 'warn',
              title: 'Fix validation blockers',
              detail: `${formatInt(validationErrors.length)} validation error(s) must be cleared before test send or launch.`,
              actionLabel: 'Check Audience',
              run: validateCampaign,
              disabled: operationBusy,
            }
            : !lastTestSendResult
              ? {
                tone: 'warn',
                title: 'Send proof email',
                detail: testEmail.trim() ? 'Send a proof to confirm rendered content and provider handoff.' : 'Add a test recipient before proofing this campaign.',
                actionLabel: testEmail.trim() ? 'Send Test' : 'Preview Email',
                run: testEmail.trim() ? sendTestEmail : previewTestEmail,
                disabled: operationBusy,
              }
              : !lastLaunchResult
                ? {
                  tone: 'warn',
                  title: 'Dry-run launch',
                  detail: 'Simulate launch volume, queued count, and suppression impact before production queueing.',
                  actionLabel: 'Dry-Run Launch',
                  run: dryRunLaunch,
                  disabled: operationBusy,
                }
                : latestJob
                  ? {
                    tone: 'good',
                    title: 'Monitor delivery',
                    detail: `${latestJob.status} job loaded; continue delivery follow-up from Delivery Manager.`,
                    actionLabel: 'Open Delivery',
                    run: () => { window.location.hash = '#delivery'; },
                    disabled: operationBusy,
                  }
                  : {
                    tone: 'good',
                    title: 'Campaign ready',
                    detail: 'Draft, content, audience, readiness, proof, and dry-run checks are ready.',
                    actionLabel: 'Open Analytics',
                    run: () => { window.location.hash = '#analytics'; },
                    disabled: operationBusy,
                  };
  const campaignTriageItems = [
    {
      label: 'Draft',
      value: selectedCampaignId ? 'Saved' : 'Unsaved',
      detail: selectedCampaign?.status || 'Create or select a campaign',
      tone: selectedCampaignId ? 'good' : 'warn',
    },
    {
      label: 'Content',
      value: selectedTemplate ? 'Template' : 'Missing',
      detail: selectedTemplate?.name || 'No template selected',
      tone: selectedTemplate ? 'good' : 'warn',
    },
    {
      label: 'Audience',
      value: selectedAudience ? formatInt(selectedAudience.estimated_count) : 'Missing',
      detail: selectedAudience?.name || 'No audience selected',
      tone: selectedAudience ? 'good' : 'warn',
    },
    {
      label: 'Readiness',
      value: workflowStatus ? `${formatInt(validationErrors.length)} error(s)` : 'Not run',
      detail: workflowStatus ? `${formatInt(validationWarnings.length)} warning(s) loaded` : 'Refresh readiness before send',
      tone: workflowStatus && !validationErrors.length ? 'good' : 'warn',
    },
    {
      label: 'Proof and launch',
      value: lastLaunchResult ? 'Dry-run' : lastTestSendResult ? 'Proof sent' : 'Pending',
      detail: lastLaunchResult ? `${formatInt(lastLaunchResult.queued_count)} queued in last result` : lastTestSendResult ? `${lastTestSendResult.status_code} from ${lastTestSendResult.provider}` : 'Send proof, then dry-run launch',
      tone: lastLaunchResult || lastTestSendResult ? 'good' : 'warn',
    },
  ];
  const launchFoundationItems = [
    {
      label: 'Template contract',
      value: selectedTemplate ? 'Selected' : 'Gap',
      detail: selectedTemplate ? `${selectedTemplate.subject || selectedTemplate.name}` : 'Select a saved template before proof or launch.',
      tone: selectedTemplate ? 'good' : 'warn',
    },
    {
      label: 'Audience snapshot',
      value: selectedAudience ? formatInt(selectedAudience.estimated_count) : 'Gap',
      detail: selectedAudience ? `${selectedAudience.name} reach estimate before dry-run.` : 'Choose an audience so launch volume and suppressions can be checked.',
      tone: selectedAudience ? 'good' : 'warn',
    },
    {
      label: 'Send engine handoff',
      value: latestJob ? latestJob.status : lastLaunchResult ? 'Dry-run' : 'Pending',
      detail: latestJob ? `${formatInt(latestJob.queued_count)} queued in latest job.` : lastLaunchResult ? `${formatInt(lastLaunchResult.queued_count)} queued in dry-run result.` : 'Run dry-run launch before production queueing.',
      tone: latestJob || lastLaunchResult ? 'good' : 'warn',
    },
    {
      label: 'Suppression impact',
      value: lastLaunchResult ? formatInt(lastLaunchResult.suppressed_count) : 'Unknown',
      detail: lastLaunchResult ? 'Suppression count loaded from launch simulation.' : 'Dry-run to reveal opt-out, bounce, and complaint suppression impact.',
      tone: lastLaunchResult ? 'good' : 'warn',
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
      const data = await fetchJson<CampaignTestSendResult>(`/api/v1/campaigns/${selectedCampaignId}/test-send`, {
        method: 'POST',
        body: JSON.stringify({ to_email: testEmail.trim(), variables: parsedVariables() }),
      });
      setLastTestSendResult({ ...data, to_email: testEmail.trim() });
      return `Test send ${data.status_code < 400 ? 'sent' : 'failed'}${data.provider_message_id ? ` (${data.provider_message_id})` : ''}.`;
    });
  }

  async function dryRunLaunch() {
    await runOperation('Running dry-run launch', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<CampaignLaunchResult>(`/api/v1/campaigns/${selectedCampaignId}/launch`, {
        method: 'POST',
        body: JSON.stringify({ audience_id: audienceId || null, variables: parsedVariables(), dry_run: true }),
      });
      setLastLaunchResult(data);
      return `Dry run complete. ${formatInt(data.requested_count)} requested, ${formatInt(data.queued_count)} queued, ${formatInt(data.suppressed_count)} suppressed.`;
    });
  }

  async function reviewCampaignWithAi() {
    await runOperation('Running AI Campaign Review', async () => {
      if (!selectedCampaignId) throw new Error('Create or select a campaign first.');
      const data = await fetchJson<AIWorkflowAnalysis>('/api/v1/ai/campaigns/analyze', {
        method: 'POST',
        body: JSON.stringify({
          campaign_context: {
            campaign: selectedCampaign || { id: selectedCampaignId, name: campaignName },
            template: selectedTemplate || { id: templateId },
            audience: selectedAudience || { id: audienceId },
            performance: selectedCampaignPerformance,
            workflow_status: workflowStatus,
            last_test_send: lastTestSendResult,
            last_launch_result: lastLaunchResult,
            validation: workflowStatus?.validation || { errors: validationErrors, warnings: validationWarnings },
            latest_send_job: latestJob,
            triage: {
              title: campaignTriageAction.title,
              detail: campaignTriageAction.detail,
              readiness_score: readinessScore,
              queued_records: latestJob?.queued_count,
              validation_errors: validationErrors,
              validation_warnings: validationWarnings,
            },
          },
          goals: [
            'Assess campaign launch readiness',
            'Find template, audience, validation, suppression, and delivery risks',
            'Recommend the next operator action before production launch',
          ],
        }),
      });
      setAiCampaignSummary(data.summary || []);
      setAiCampaignRecommendations(data.recommendations || []);
      return `AI Campaign Review loaded ${formatInt(data.recommendations?.length || 0)} recommendation(s).`;
    });
  }

  async function deleteCampaignRow(campaign: CampaignRead) {
    if (!window.confirm(`Delete campaign "${campaign.name}"?`)) return;
    await runOperation('Deleting campaign', async () => {
      await fetchJson<{ id: string }>(`/api/v1/campaigns/${campaign.id}`, { method: 'DELETE' });
      if (selectedCampaignId === campaign.id) setSelectedCampaignId('');
      return `Deleted campaign: ${campaign.name}.`;
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
	                      onDoubleClick={() => { window.location.hash = `#campaigns/${campaign.id}`; }}
	                    >
                      <td>{campaign.name}</td>
                      <td><span className="pill">{campaign.status}</span></td>
                      <td>{formatInt(performance?.requested_count)}</td>
                      <td>{formatInt(performance?.sent_count)}</td>
                      <td>{performance ? formatPct(performance.open_rate) : '-'}</td>
                      <td>{performance ? formatPct(performance.click_rate) : '-'}</td>
                      <td>{formatInt(performance?.failed_count)}</td>
                      <td><RowActionMenu openHref={`#campaigns/${campaign.id}`} onDelete={() => deleteCampaignRow(campaign)} /></td>
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
      <section className={`campaign-triage-panel full-span ${campaignTriageAction.tone}`}>
        <div className="campaign-triage-head">
          <div>
            <span>Campaign triage</span>
            <strong>{campaignTriageAction.title}</strong>
            <small>{campaignTriageAction.detail}</small>
          </div>
          <button className={campaignTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={campaignTriageAction.run} disabled={campaignTriageAction.disabled}>{campaignTriageAction.actionLabel}</button>
        </div>
        <div className="campaign-triage-list">
          {campaignTriageItems.map((item) => (
            <article className={`campaign-triage-row ${item.tone}`} key={item.label}>
              <div>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      {isPersistedCampaign ? (
        <section className="panel full-span campaign-launch-panel">
          <div className="panel-head">
            <div>
              <h2>Launch command</h2>
              <span className="muted">Readiness, latest send job, and next action</span>
            </div>
            <button className="ghost" onClick={loadCampaignWorkflowStatus} disabled={operationBusy}>Refresh Readiness</button>
          </div>
          <div className="launch-command-grid">
            <div className="launch-score">
              <span>Readiness</span>
              <strong>{readinessScore}%</strong>
              <div><i style={{ width: `${readinessScore}%` }} /></div>
              <p>{readyCount} of {readinessCards.length} checks ready</p>
            </div>
            <div className="launch-score">
              <span>Latest job</span>
              <strong>{latestJob?.status || 'No job loaded'}</strong>
              <div><i style={{ width: `${latestProgressPct}%` }} /></div>
              <p>{latestRequested ? `${formatInt(latestProcessed)} of ${formatInt(latestRequested)} processed` : 'Run readiness or launch dry-run to inspect delivery state'}</p>
            </div>
            <div className="launch-next-action">
              <span>Guided next step</span>
              <strong>{campaignNextStep.label}</strong>
              <p>{nextCampaignAction}</p>
              <small>{campaignNextStep.detail}</small>
              <button className="primary" onClick={campaignNextStep.run} disabled={operationBusy}>{campaignNextStep.actionLabel}</button>
              <p>{validationErrors.length ? `${formatInt(validationErrors.length)} errors must be fixed.` : validationWarnings.length ? `${formatInt(validationWarnings.length)} warnings to review.` : 'No blockers loaded.'}</p>
            </div>
          </div>
          <div className="campaign-foundation-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Launch Foundations</h3>
                <span className="muted">Template contract, audience snapshot, send engine handoff, and suppression impact.</span>
              </div>
              <button className="link-button" type="button" onClick={dryRunLaunch} disabled={operationBusy}>Dry-Run Launch</button>
            </div>
            <div className="campaign-foundation-grid">
              {launchFoundationItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </div>
          {lastLaunchResult ? (
            <div className={`launch-result-card ${lastLaunchResult.dry_run ? 'dry-run' : ''}`}>
              <div>
                <span>{lastLaunchResult.dry_run ? 'Dry-run result' : 'Launch result'}</span>
                <strong>{lastLaunchResult.status}</strong>
                <small>Job {lastLaunchResult.job_id.slice(0, 8)}{lastLaunchResult.audience_snapshot_id ? ` | Snapshot ${lastLaunchResult.audience_snapshot_id.slice(0, 8)}` : ''}</small>
              </div>
              <div><span>Requested</span><strong>{formatInt(lastLaunchResult.requested_count)}</strong></div>
              <div><span>Queued</span><strong>{formatInt(lastLaunchResult.queued_count)}</strong></div>
              <div><span>Suppressed</span><strong>{formatInt(lastLaunchResult.suppressed_count)}</strong></div>
              <a href="#delivery">Open delivery</a>
            </div>
          ) : null}
          {lastTestSendResult ? (
            <div className="test-send-result-card">
              <div>
                <span>Test send result</span>
                <strong>{lastTestSendResult.status_code < 400 ? 'Sent' : 'Review'}</strong>
                <small>{lastTestSendResult.to_email || 'Test recipient'} | {lastTestSendResult.provider}</small>
              </div>
              <div><span>Status</span><strong>{lastTestSendResult.status_code}</strong></div>
              <div><span>Provider ID</span><strong>{lastTestSendResult.provider_message_id || '-'}</strong></div>
              <div><span>Record</span><strong>{lastTestSendResult.send_record_id.slice(0, 8)}</strong></div>
              <a href="#delivery">Open delivery</a>
            </div>
          ) : null}
          {validationErrors.length || validationWarnings.length ? (
            <div className="launch-issue-list">
              {validationErrors.map((item) => <p className="warn" key={`error-${item}`}>Error: {item}</p>)}
              {validationWarnings.map((item) => <p key={`warning-${item}`}>Warning: {item}</p>)}
            </div>
          ) : null}
          <div className="campaign-ai-review-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>AI Campaign Review</h3>
                <span className="muted">{aiCampaignRecommendations?.length ? `${formatInt(aiCampaignRecommendations.length)} recommendation(s)` : 'Review launch readiness, audience fit, template risk, and delivery handoff.'}</span>
              </div>
              <button className="link-button" type="button" onClick={reviewCampaignWithAi} disabled={operationBusy}>Run AI Review</button>
            </div>
            {aiCampaignSummary.length ? (
              <div className="campaign-ai-summary">
                {aiCampaignSummary.slice(0, 4).map((item) => <span key={item}>{item}</span>)}
              </div>
            ) : null}
            {aiCampaignRecommendations?.length ? (
              <div className="recommendation-list">
                {aiCampaignRecommendations.slice(0, 5).map((item) => (
                  <article key={item.code}>
                    <span className="pill">{item.priority}</span>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                    <small>{item.suggested_action || item.suggested_instruction || 'Review recommendation.'}</small>
                  </article>
                ))}
              </div>
            ) : (
              <div className="ai-empty-state">
                <strong>No AI campaign review loaded</strong>
                <span>Run AI Campaign Review after loading readiness to prioritize validation, audience, template, and launch follow-up.</span>
              </div>
            )}
          </div>
        </section>
      ) : null}
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
        <div className="campaign-action-bar">
          <div>
            <strong>Draft</strong>
            <button className="primary" onClick={createDraftCampaign} disabled={operationBusy || !templateId}>{isCreatingCampaign ? 'Create Campaign' : 'Save Changes'}</button>
          </div>
          {isPersistedCampaign ? (
            <>
              <div>
                <strong>Review</strong>
                <button className="ghost" onClick={loadCampaignWorkflowStatus} disabled={operationBusy}>Readiness</button>
                <button className="ghost" onClick={validateCampaign} disabled={operationBusy}>Check Audience</button>
                <button className="ghost" onClick={previewTestEmail} disabled={operationBusy}>Preview Email</button>
                <button className="ghost" onClick={reviewCampaignWithAi} disabled={operationBusy}>AI Campaign Review</button>
              </div>
              <div>
                <strong>Send</strong>
                <button className="ghost" onClick={sendTestEmail} disabled={operationBusy}>Send Test</button>
                <button className="ghost" onClick={dryRunLaunch} disabled={operationBusy}>Dry-Run Launch</button>
              </div>
            </>
          ) : null}
        </div>
        <div className={`operation-banner ${operationStatus.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{operationBusy ? 'Working' : 'Status'}</strong>
          <span>{operationStatus}</span>
          {selectedCampaign ? <small>Selected: {selectedCampaign.name}</small> : null}
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
  const [aiJourneySummary, setAiJourneySummary] = useState<string[]>([]);
  const [aiJourneyRecommendations, setAiJourneyRecommendations] = useState<AIWorkflowAnalysis['recommendations']>([]);
  const [status, setStatus] = useState('Ready to create or update a journey.');
  const [busy, setBusy] = useState(false);
  const routeParts = route.split('/');
  const routeJourneyId = routeParts[0] === 'automations' && routeParts[1] && routeParts[1] !== 'new' ? routeParts[1] : '';
  const isDetailPage = routeParts[0] === 'automations' && Boolean(routeParts[1]);
  const isNewJourney = routeParts[0] === 'automations' && routeParts[1] === 'new';

  useEffect(() => {
    if (isNewJourney) {
      resetJourneyEditor();
    } else if (routeJourneyId) {
      const journey = journeyItems.find((item) => item.id === routeJourneyId);
      if (journey && selectedJourneyId !== journey.id) loadJourneyIntoEditor(journey);
    } else if (!selectedJourneyId && journeyItems.length) {
      loadJourneyIntoEditor(journeyItems[0]);
    }
    if (!templateId && templates.length) setTemplateId(templates[0].id);
    if (!contactId && contacts.length) setContactId(contacts[0].id);
  }, [contactId, contacts, isNewJourney, journeyItems, routeJourneyId, selectedJourneyId, templateId, templates]);

  const failures = journeys.reduce((sum, item) =>
    sum + Number(item.failed_count || 0) + Number(item.step_failed_count || 0), 0);
  const queued = journeys.reduce((sum, item) => sum + Number(item.queued_send_count || 0), 0);
  const active = journeys.reduce((sum, item) => sum + Number(item.active_count || 0), 0);
  const completed = journeys.reduce((sum, item) => sum + Number(item.completed_count || 0), 0);
  const selectedJourney = journeyItems.find((item) => item.id === selectedJourneyId);
  const selectedJourneyPerformance = journeys.find((item) => item.journey_id === selectedJourneyId);
  const isPersistedJourney = Boolean(selectedJourneyId);
  const isCreatingJourney = !isPersistedJourney;
  const selectedContact = contacts.find((item) => item.id === contactId);
  const visibleEnrollments = selectedJourneyId
    ? enrollments.filter((item) => item.journey_id === selectedJourneyId)
    : enrollments;
  const visibleExecutions = selectedJourneyId
    ? executions.filter((item) => item.journey_id === selectedJourneyId)
    : executions;
  const failedExecutions = visibleExecutions.filter((item) => item.status === 'failed').length;
  const activeEnrollments = visibleEnrollments.filter((item) => item.status === 'active').length;
  const dueEnrollments = visibleEnrollments.filter((item) => item.status === 'active' && item.due_at).length;
  const selectedStepCount = selectedJourney?.steps?.length || 0;
  const selectedFailures = Number(selectedJourneyPerformance?.failed_count || 0) + Number(selectedJourneyPerformance?.step_failed_count || 0);
  const selectedQueuedSends = Number(selectedJourneyPerformance?.queued_send_count || 0);
  const journeyTriageAction = failures || failedExecutions
    ? {
      tone: 'warn',
      title: 'Review journey failures',
      detail: `${formatInt(failures || failedExecutions)} failure signal(s) need step, contact, or delivery review.`,
      actionLabel: 'Open Delivery',
      run: () => { window.location.hash = '#delivery'; },
      disabled: busy,
    }
    : queued
      ? {
        tone: 'warn',
        title: 'Process queued sends',
        detail: `${formatInt(queued)} queued journey send(s) should be monitored in delivery.`,
        actionLabel: 'Open Delivery',
        run: () => { window.location.hash = '#delivery'; },
        disabled: busy,
      }
      : dueEnrollments || active
        ? {
          tone: 'warn',
          title: 'Process due enrollments',
          detail: `${formatInt(dueEnrollments || active)} active enrollment(s) are ready for the next journey step.`,
          actionLabel: 'Process Due',
          run: processDue,
          disabled: busy,
        }
        : !selectedJourneyId
          ? {
            tone: 'warn',
            title: 'Select or create journey',
            detail: 'Choose a journey before adding steps, enrolling contacts, or processing due work.',
            actionLabel: 'Create Journey',
            run: () => { window.location.hash = '#automations/new'; },
            disabled: busy,
          }
          : selectedStepCount === 0
            ? {
              tone: 'warn',
              title: 'Add first send step',
              detail: 'The selected journey has no send steps configured yet.',
              actionLabel: 'Add Send Step',
              run: addSendStep,
              disabled: busy || !templateId,
            }
            : {
              tone: 'good',
              title: 'Journey ready',
              detail: 'No loaded failure, queue, or due-enrollment pressure needs immediate action.',
              actionLabel: 'Refresh',
              run: onRefresh,
              disabled: busy,
            };
  const journeyTriageItems = [
    {
      label: 'Failure pressure',
      value: formatInt(selectedJourneyId ? selectedFailures : failures),
      detail: failedExecutions ? `${formatInt(failedExecutions)} visible failed execution(s)` : 'No failed executions visible',
      tone: (selectedJourneyId ? selectedFailures : failures) ? 'warn' : 'good',
    },
    {
      label: 'Queued sends',
      value: formatInt(selectedJourneyId ? selectedQueuedSends : queued),
      detail: queued ? 'Monitor generated send records in Delivery Manager' : 'No journey send backlog visible',
      tone: (selectedJourneyId ? selectedQueuedSends : queued) ? 'warn' : 'good',
    },
    {
      label: 'Active enrollments',
      value: formatInt(selectedJourneyId ? activeEnrollments : active),
      detail: dueEnrollments ? `${formatInt(dueEnrollments)} due or scheduled enrollment(s)` : 'No due enrollment pressure visible',
      tone: dueEnrollments || activeEnrollments ? 'warn' : 'good',
    },
    {
      label: 'Builder readiness',
      value: selectedJourneyId ? `${formatInt(selectedStepCount)} step(s)` : 'No journey',
      detail: selectedJourneyId ? 'Save changes before enrollment testing' : 'Select or create a journey to continue',
      tone: selectedJourneyId && selectedStepCount ? 'good' : 'warn',
    },
  ];
  const entryRuleValid = (() => {
    try {
      parseJsonObject(entryRuleJson, 'entry rule');
      return true;
    } catch {
      return false;
    }
  })();
  const journeyFoundationItems = [
    {
      label: 'Orchestration queue',
      value: formatInt(selectedJourneyId ? visibleEnrollments.length : enrollments.length),
      detail: dueEnrollments || queued
        ? 'Due enrollments and generated sends need durable worker monitoring.'
        : 'Queue processing is visible, but production durability remains a foundation concern.',
      tone: dueEnrollments || queued ? 'warn' : 'good',
    },
    {
      label: 'Event triggers',
      value: entryRuleValid ? 'Rule ready' : 'Gap',
      detail: entryRuleValid
        ? 'Entry rules can seed enrollment logic while connector-backed event triggers are expanded.'
        : 'Real-time event and data-source triggers still need connector-backed activation.',
      tone: entryRuleValid ? 'good' : 'warn',
    },
    {
      label: 'Send handoff',
      value: selectedStepCount && templateId ? 'Configured' : 'Gap',
      detail: selectedStepCount && templateId
        ? 'Send steps can hand off to templates and Delivery Manager.'
        : 'Add a send step with a template before journey delivery can run.',
      tone: selectedStepCount && templateId ? 'good' : 'warn',
    },
    {
      label: 'Feedback loop',
      value: visibleExecutions.length ? `${formatInt(visibleExecutions.length)} executions` : 'Gap',
      detail: visibleExecutions.length
        ? 'Execution history is available for journey review.'
        : 'Bounce, engagement, and delivery feedback should feed journey decisions.',
      tone: visibleExecutions.length ? 'good' : 'warn',
    },
  ];

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

  async function reviewJourneyWithAi() {
    await runJourneyOperation('Running AI Journey Review', async () => {
      if (!selectedJourneyId) throw new Error('Save or select a journey first.');
      const graph = await fetchJson<Record<string, unknown>>(`/api/v1/journeys/${selectedJourneyId}/graph`);
      const data = await fetchJson<AIWorkflowAnalysis>('/api/v1/ai/journeys/analyze', {
        method: 'POST',
        body: JSON.stringify({
          journey_context: {
            journey: selectedJourney || selectedJourneyPerformance || { id: selectedJourneyId },
            graph,
            enrollments: { items: visibleEnrollments },
            executions: { items: visibleExecutions },
            triage: {
              title: journeyTriageAction.title,
              detail: journeyTriageAction.detail,
              failures,
              queued_sends: queued,
              active_enrollments: activeEnrollments,
              failed_executions: failedExecutions,
            },
          },
          goals: [
            'Assess journey structure and execution readiness',
            'Find failed steps, missing send configuration, and queued send follow-up',
            'Recommend the next operator action for the journey manager',
          ],
        }),
      });
      setAiJourneySummary(data.summary || []);
      setAiJourneyRecommendations(data.recommendations || []);
      return `AI Journey Review loaded ${formatInt(data.recommendations?.length || 0)} recommendation(s).`;
    });
  }

  async function deleteJourneyRow(journey: JourneyPerformance) {
    if (!window.confirm(`Delete journey "${journey.name}"?`)) return;
    await runJourneyOperation('Deleting journey', async () => {
      await fetchJson<{ id: string }>(`/api/v1/journeys/${journey.journey_id}`, { method: 'DELETE' });
      if (selectedJourneyId === journey.journey_id) resetJourneyEditor();
      return `Deleted journey: ${journey.name}.`;
    });
  }

  async function archiveJourneyRow(journey: JourneyPerformance) {
    await runJourneyOperation('Archiving journey', async () => {
      await fetchJson<JourneyRead>(`/api/v1/journeys/${journey.journey_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'archived' }),
      });
      return `Archived journey: ${journey.name}.`;
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
        <section className={`journey-triage-panel full-span ${journeyTriageAction.tone}`}>
          <div className="journey-triage-head">
            <div>
              <span>Journey triage</span>
              <strong>{journeyTriageAction.title}</strong>
              <small>{journeyTriageAction.detail}</small>
            </div>
            <button className={journeyTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={journeyTriageAction.run} disabled={journeyTriageAction.disabled}>{journeyTriageAction.actionLabel}</button>
          </div>
          <div className="journey-triage-grid">
            {journeyTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="journey-foundation-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Journey Foundations</h3>
              <span className="muted">Orchestration queues, event triggers, send handoff, and feedback readiness.</span>
            </div>
            <a href="#delivery">Open Delivery</a>
          </div>
          <div className="journey-foundation-grid">
            {journeyFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
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
	                      onDoubleClick={() => { window.location.hash = `#automations/${journey.journey_id}`; }}
	                    >
                      <td>{journey.name}</td>
                      <td><span className="pill">{journey.status}</span></td>
                      <td>{formatInt(journey.enrollment_count)}</td>
                      <td>{formatInt(journey.active_count)}</td>
                      <td>{formatInt(journey.completed_count)}</td>
                      <td>{formatInt(Number(journey.failed_count || 0) + Number(journey.step_failed_count || 0))}</td>
                      <td>{formatInt(journey.queued_send_count)}</td>
                      <td><RowActionMenu openHref={`#automations/${journey.journey_id}`} onDelete={() => deleteJourneyRow(journey)} onArchive={() => archiveJourneyRow(journey)} /></td>
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
      <section className={`journey-triage-panel full-span ${journeyTriageAction.tone}`}>
        <div className="journey-triage-head">
          <div>
            <span>Journey triage</span>
            <strong>{journeyTriageAction.title}</strong>
            <small>{journeyTriageAction.detail}</small>
          </div>
          <button className={journeyTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={journeyTriageAction.run} disabled={journeyTriageAction.disabled}>{journeyTriageAction.actionLabel}</button>
        </div>
        <div className="journey-triage-grid">
          {journeyTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="journey-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Journey Foundations</h3>
            <span className="muted">Orchestration queues, event triggers, send handoff, and feedback readiness.</span>
          </div>
          <a href="#delivery">Open Delivery</a>
        </div>
        <div className="journey-foundation-grid">
          {journeyFoundationItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel full-span campaign-workbench">
        <div className="panel-head">
          <h2>{selectedJourney ? 'Journey Builder' : 'Create Journey'}</h2>
          <div className="button-row">
            <a href="#automations">Back to automations</a>
            <a href="#delivery">Open delivery</a>
          </div>
        </div>
        <div className="campaign-action-bar">
          <div>
            <strong>Journey</strong>
            <button className="primary" onClick={saveJourney} disabled={busy}>{isCreatingJourney ? 'Create Journey' : 'Save Changes'}</button>
          </div>
          {isPersistedJourney ? (
            <>
              <div>
                <strong>Builder</strong>
                <button className="ghost" onClick={addSendStep} disabled={busy || !templateId}>Add Send Step</button>
              </div>
              <div>
                <strong>Run</strong>
                <button className="ghost" onClick={enrollContact} disabled={busy || !contactId}>Enroll Contact</button>
                <button className="ghost" onClick={processDue} disabled={busy}>Process Due</button>
                <button className="ghost" onClick={reviewJourneyWithAi} disabled={busy}>AI Journey Review</button>
              </div>
            </>
          ) : null}
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
          {selectedJourney?.steps?.length ? <small>{selectedJourney.steps.map((step) => `${step.position + 1}. ${step.name}`).join(' | ')}</small> : null}
          {selectedContact ? <small>Selected contact: {selectedContact.email}</small> : null}
        </div>
        {isPersistedJourney ? (
          <div className="journey-ai-review-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>AI Journey Review</h3>
                <span className="muted">{aiJourneyRecommendations?.length ? `${formatInt(aiJourneyRecommendations.length)} recommendation(s)` : 'Review selected journey structure, enrollments, and executions.'}</span>
              </div>
              <button className="link-button" type="button" onClick={reviewJourneyWithAi} disabled={busy}>Run AI Review</button>
            </div>
            {aiJourneySummary.length ? (
              <div className="journey-ai-summary">
                {aiJourneySummary.slice(0, 4).map((item) => <span key={item}>{item}</span>)}
              </div>
            ) : null}
            {aiJourneyRecommendations?.length ? (
              <div className="recommendation-list">
                {aiJourneyRecommendations.slice(0, 5).map((item) => (
                  <article key={item.code}>
                    <span className="pill">{item.priority}</span>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                    <small>{item.suggested_action || item.suggested_instruction || 'Review recommendation.'}</small>
                  </article>
                ))}
              </div>
            ) : (
              <div className="ai-empty-state">
                <strong>No AI journey review loaded</strong>
                <span>Run AI Journey Review after selecting a journey to prioritize step fixes, queued sends, and enrollment follow-up.</span>
              </div>
            )}
          </div>
        ) : null}
        <div className="form-grid">
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

function AudiencePage({ audiences, audienceItems, campaigns, metadata, route, onRefresh, onOperation }: {
  audiences: AudiencePerformance[];
  audienceItems: AudienceRead[];
  campaigns: CampaignRead[];
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
  const [aiAudienceSummary, setAiAudienceSummary] = useState<string[]>([]);
  const [aiAudienceRecommendations, setAiAudienceRecommendations] = useState<AIWorkflowAnalysis['recommendations']>([]);

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
  const isPersistedAudience = Boolean(selectedAudienceId);
  const isCreatingAudience = !isPersistedAudience;
  const ruleJsonValid = isRuleJsonValid();
  const selectedAudienceRuleKey = selectedAudience ? stableAudienceRuleKey(selectedAudience.rule_tree || {}) : '';
  const selectedAudienceCampaigns = selectedAudienceRuleKey
    ? campaigns.filter((campaign) => stableAudienceRuleKey(campaign.audience_query || {}) === selectedAudienceRuleKey)
    : [];
  const selectedAudienceActiveCampaigns = selectedAudienceCampaigns.filter((campaign) => campaign.status !== 'archived');
  const campaignAwareSummary = selectedAudience
    ? {
      tone: selectedAudienceActiveCampaigns.length ? 'good' : 'warn',
      title: selectedAudienceActiveCampaigns.length ? 'Campaign usage found' : 'No campaign usage yet',
      detail: selectedAudienceActiveCampaigns.length
        ? `${formatInt(selectedAudienceActiveCampaigns.length)} active campaign(s) use this audience rule.`
        : 'No active campaigns currently use this audience rule snapshot.',
      latest: selectedAudienceActiveCampaigns[0]?.name || 'No linked campaign',
    }
    : {
      tone: 'warn',
      title: 'Save audience first',
      detail: 'Campaign usage appears after the audience is saved and selected.',
      latest: 'No linked campaign',
    };
  const availableFields = metadata?.fields || [];
  const attributeKeys = metadata?.attribute_keys || [];
  const attributeFields = attributeKeys.map((key) => `attributes.${key}`);
  const fieldHints = [...availableFields, ...attributeFields].slice(0, 24);
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
  const parsedRulePreview = (() => {
    try {
      return parsedRuleTree();
    } catch {
      return null;
    }
  })();
  const activeRuleField = typeof parsedRulePreview?.field === 'string' ? parsedRulePreview.field : '';
  const activeRuleComparator = typeof parsedRulePreview?.comparator === 'string' ? parsedRulePreview.comparator : '';
  const activeRuleValue = parsedRulePreview && 'value' in parsedRulePreview ? parsedRulePreview.value : undefined;
  const matchRate = metadata?.total && matchedCount !== null ? matchedCount / Math.max(metadata.total, 1) : null;
  const selectedFieldProfile = activeRuleField ? fieldProfileForField(activeRuleField) : null;
  const highlightedFieldProfiles = fieldHints.slice(0, 6).map(fieldProfileForField);
  const audienceImpactSummary = matchedCount === null
    ? {
      tone: 'warn',
      title: 'Preview needed',
      detail: 'Run preview to estimate reach and inspect sample contacts before using this rule.',
      reach: 'Not previewed',
      sample: sampleContacts.length ? `${formatInt(sampleContacts.length)} sample(s)` : 'No samples',
    }
    : matchedCount <= 0
      ? {
        tone: 'warn',
        title: 'No matched contacts',
        detail: 'The rule is valid, but it needs a different field, comparator, value, or more imported contacts.',
        reach: '0 matched',
        sample: 'No samples',
      }
      : matchRate !== null && matchRate >= 0.8
        ? {
          tone: 'warn',
          title: 'Very broad audience',
          detail: 'This rule reaches most known contacts. Confirm that broad targeting is intentional before launch.',
          reach: `${formatPct(matchRate)} of contacts`,
          sample: `${formatInt(sampleContacts.length)} sample(s)`,
        }
        : matchRate !== null && matchRate <= 0.01
          ? {
            tone: 'warn',
            title: 'Very narrow audience',
            detail: 'This rule reaches a small slice of known contacts. Check samples before investing in a campaign.',
            reach: `${formatPct(matchRate)} of contacts`,
            sample: `${formatInt(sampleContacts.length)} sample(s)`,
          }
          : {
            tone: 'good',
            title: 'Audience impact ready',
            detail: 'Matched contacts and sample rows are available for rule review.',
            reach: matchRate === null ? `${formatInt(matchedCount)} matched` : `${formatPct(matchRate)} of contacts`,
            sample: `${formatInt(sampleContacts.length)} sample(s)`,
          };
  const audienceNextAction = !name.trim()
    ? {
      tone: 'warn',
      title: 'Name the audience',
      detail: 'Add a clear audience name before saving or previewing campaign reach.',
      actionLabel: 'Review Setup',
      run: () => setStatus('Add an audience name in setup before saving.'),
    }
    : !ruleJsonValid
      ? {
        tone: 'warn',
        title: 'Fix rule JSON',
        detail: 'The rule must be a JSON object before preview or save can run.',
        actionLabel: 'Review Rule',
        run: () => setStatus('Fix the audience rule JSON before previewing.'),
      }
      : matchedCount === null
        ? {
          tone: 'warn',
          title: 'Preview audience reach',
          detail: 'Preview this rule to confirm matched count and sample contacts.',
          actionLabel: 'Preview Contacts',
          run: previewAudience,
        }
        : matchedCount <= 0
          ? {
            tone: 'warn',
            title: 'Adjust rule or import contacts',
            detail: 'This rule currently matches no contacts, so it is not campaign-ready.',
            actionLabel: 'Import Contacts',
            run: () => { window.location.hash = '#data'; },
          }
          : !selectedAudienceId
            ? {
              tone: 'warn',
              title: 'Save campaign-ready audience',
              detail: `${formatInt(matchedCount)} contact(s) matched. Save the audience so campaigns can use it.`,
              actionLabel: 'Save Audience',
              run: saveAudience,
            }
            : {
              tone: 'good',
              title: 'Snapshot before launch',
              detail: `${formatInt(matchedCount)} contact(s) matched. Create a stable snapshot before campaign launch.`,
              actionLabel: 'Create Snapshot',
              run: snapshotAudience,
            };
  const audienceTriageAction = !metadata?.total
    ? {
      tone: 'warn',
      title: 'Import contact data',
      detail: 'Audience rules need contact fields and sample rows before targeting can be trusted.',
      actionLabel: 'Open Data Sources',
      run: () => { window.location.hash = '#data'; },
      disabled: busy,
    }
    : !name.trim()
      ? {
        tone: 'warn',
        title: 'Name the audience',
        detail: 'Add a clear audience name before preview, save, snapshot, or campaign use.',
        actionLabel: 'Review Setup',
        run: () => setStatus('Add an audience name in setup before saving.'),
        disabled: busy,
      }
      : !ruleJsonValid
        ? {
          tone: 'warn',
          title: 'Fix rule JSON',
          detail: 'Audience targeting rules must be valid JSON objects before preview or save can run.',
          actionLabel: 'Review Rule',
          run: () => setStatus('Fix the audience rule JSON before previewing.'),
          disabled: busy,
        }
        : matchedCount === null
          ? {
            tone: 'warn',
            title: 'Preview audience reach',
            detail: 'Run preview to validate matched count and sample contacts before campaign use.',
            actionLabel: 'Preview Contacts',
            run: previewAudience,
            disabled: busy,
          }
          : matchedCount <= 0
            ? {
              tone: 'warn',
              title: 'Adjust rule or import contacts',
              detail: 'This audience currently has no reachable contacts for campaign launch.',
              actionLabel: 'Import Contacts',
              run: () => { window.location.hash = '#data'; },
              disabled: busy,
            }
            : !selectedAudienceId
              ? {
                tone: 'warn',
                title: 'Save audience',
                detail: `${formatInt(matchedCount)} contact(s) matched. Save the audience before campaign assignment.`,
                actionLabel: 'Save Audience',
                run: saveAudience,
                disabled: busy,
              }
              : !selectedAudienceActiveCampaigns.length
                ? {
                  tone: 'warn',
                  title: 'Create campaign handoff',
                  detail: 'This audience is saved and previewed, but no active campaign currently uses its rule.',
                  actionLabel: 'Open Campaigns',
                  run: () => { window.location.hash = '#campaigns'; },
                  disabled: busy,
                }
                : {
                  tone: 'good',
                  title: 'Snapshot before launch',
                  detail: `${formatInt(matchedCount)} contact(s) matched and campaign usage exists. Snapshot before launch.`,
                  actionLabel: 'Create Snapshot',
                  run: snapshotAudience,
                  disabled: busy,
                };
  const audienceTriageItems = [
    {
      label: 'Contact data',
      value: formatInt(metadata?.total || 0),
      detail: `${formatInt(availableFields.length + attributeKeys.length)} fields available`,
      tone: metadata?.total ? 'good' : 'warn',
    },
    {
      label: 'Rule',
      value: ruleJsonValid ? 'Valid' : 'Invalid',
      detail: activeRuleField || 'No field selected',
      tone: ruleJsonValid ? 'good' : 'warn',
    },
    {
      label: 'Preview',
      value: matchedCount === null ? 'Not run' : formatInt(matchedCount),
      detail: matchRate === null ? 'Preview before campaign use' : `${formatPct(matchRate)} of known contacts`,
      tone: matchedCount !== null && matchedCount > 0 ? 'good' : 'warn',
    },
    {
      label: 'Samples',
      value: formatInt(sampleContacts.length),
      detail: sampleContacts.length ? 'Matched sample contacts loaded' : 'No preview samples loaded',
      tone: sampleContacts.length || matchedCount !== null ? 'good' : 'warn',
    },
    {
      label: 'Campaign handoff',
      value: formatInt(selectedAudienceActiveCampaigns.length),
      detail: selectedAudienceId ? 'Active campaign usage for this rule' : 'Save audience before campaign use',
      tone: selectedAudienceId && selectedAudienceActiveCampaigns.length ? 'good' : 'warn',
    },
  ];
  const audienceFoundationItems = [
    {
      label: 'Contact attributes',
      value: attributeKeys.length ? `${formatInt(attributeKeys.length)} keys` : 'Gap',
      detail: attributeKeys.length
        ? 'Audience rules can use loaded contact fields and attributes.'
        : 'Import richer contact attributes before relying on segmentation.',
      tone: attributeKeys.length ? 'good' : 'warn',
    },
    {
      label: 'Client entities',
      value: 'Gap',
      detail: 'Client-owned entities and relationships still need canonical storage before multi-entity audiences.',
      tone: 'warn',
    },
    {
      label: 'Snapshot contract',
      value: selectedAudienceId ? 'Ready' : 'Pending',
      detail: selectedAudienceId
        ? 'Create a stable snapshot before campaign launch.'
        : 'Save the audience before creating a stable campaign snapshot.',
      tone: selectedAudienceId ? 'good' : 'warn',
    },
    {
      label: 'Campaign usage',
      value: formatInt(selectedAudienceActiveCampaigns.length),
      detail: selectedAudienceActiveCampaigns.length
        ? 'Active campaign handoff exists for this audience rule.'
        : 'Connect this audience to a campaign before launch review.',
      tone: selectedAudienceActiveCampaigns.length ? 'good' : 'warn',
    },
  ];
  const audienceSegmentationContractItems = [
    {
      label: 'Field contract',
      value: fieldHints.length ? `${formatInt(fieldHints.length)} fields` : 'Gap',
      detail: 'Audience rules need typed contact, attribute, and client-entity fields with examples and coverage metadata.',
      tone: fieldHints.length ? 'good' : 'warn',
    },
    {
      label: 'Entity join contract',
      value: 'Gap',
      detail: 'Multi-entity targeting needs relationship joins across contacts, accounts, stores, orders, memberships, and custom objects.',
      tone: 'warn',
    },
    {
      label: 'Consent filter contract',
      value: metadata?.total ? 'Contact-level' : 'Gap',
      detail: 'Audience previews should expose suppression, unsubscribe, bounce, and complaint exclusions before activation.',
      tone: metadata?.total ? 'warn' : 'warn',
    },
    {
      label: 'Impact contract',
      value: matchedCount === null ? 'Not previewed' : `${formatInt(matchedCount)} matched`,
      detail: 'Segment impact needs match count, sample contacts, match-rate banding, and warnings for broad or narrow reach.',
      tone: matchedCount !== null && matchedCount > 0 ? 'good' : 'warn',
    },
    {
      label: 'Snapshot contract',
      value: selectedAudienceId ? 'Ready' : 'Pending',
      detail: 'Activation should use immutable audience snapshots with rule version, contact count, and source metadata.',
      tone: selectedAudienceId ? 'good' : 'warn',
    },
    {
      label: 'Handoff contract',
      value: selectedAudienceActiveCampaigns.length ? 'Linked' : 'Gap',
      detail: 'Campaign and journey handoffs need stable audience IDs, snapshot references, and downstream usage visibility.',
      tone: selectedAudienceActiveCampaigns.length ? 'good' : 'warn',
    },
  ];

  function stableAudienceRuleKey(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(stableAudienceRuleKey).join(',')}]`;
    if (value && typeof value === 'object') {
      return `{${Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => `${JSON.stringify(key)}:${stableAudienceRuleKey(child)}`)
        .join(',')}}`;
    }
    return JSON.stringify(value);
  }

  function contactFieldValue(contact: ContactRead, field: string) {
    if (field.startsWith('attributes.')) {
      return contact.attributes[field.replace(/^attributes\./, '')];
    }
    return (contact as unknown as Record<string, unknown>)[field];
  }

  function displayFieldValue(value: unknown) {
    if (Array.isArray(value)) return value.slice(0, 2).map((item) => String(item)).join(', ');
    if (value && typeof value === 'object') return JSON.stringify(value).slice(0, 48);
    return String(value ?? '').slice(0, 48);
  }

  function fieldProfileForField(field: string) {
    const values = (metadata?.sample_contacts || [])
      .map((contact) => contactFieldValue(contact, field))
      .filter((value) => value !== undefined && value !== null && String(value).trim() !== '');
    const uniqueValues = Array.from(new Set(values.map(displayFieldValue))).slice(0, 3);
    return {
      field,
      kind: field.startsWith('attributes.') ? 'Attribute field' : 'Contact field',
      coverage: metadata?.sample_contacts?.length ? values.length / Math.max(metadata.sample_contacts.length, 1) : null,
      examples: uniqueValues,
      sampleCount: values.length,
    };
  }

  function sampleValueForField(field: string) {
    const contact = metadata?.sample_contacts?.find((item) => {
      if (field.startsWith('attributes.')) {
        const key = field.replace(/^attributes\./, '');
        return item.attributes && item.attributes[key] !== undefined && item.attributes[key] !== null;
      }
      return (item as unknown as Record<string, unknown>)[field] !== undefined && (item as unknown as Record<string, unknown>)[field] !== null;
    });
    if (!contact) return '';
    return displayFieldValue(contactFieldValue(contact, field)).slice(0, 32);
  }

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

  async function reviewAudienceWithAi() {
    await runAudienceOperation('Running AI Audience Review', async () => {
      const data = await fetchJson<AIWorkflowAnalysis>('/api/v1/ai/audiences/analyze', {
        method: 'POST',
        body: JSON.stringify({
          audience_context: {
            audience: selectedAudience || { id: selectedAudienceId || null, name },
            performance: selectedAudiencePerformance,
            rule_tree: ruleJsonValid ? parsedRuleTree() : null,
            metadata,
            preview: {
              matched_count: matchedCount,
              match_rate: matchRate,
              sample_contacts: sampleContacts,
            },
            campaigns: selectedAudienceCampaigns,
            active_campaigns: selectedAudienceActiveCampaigns,
            impact: audienceImpactSummary,
            campaign_awareness: campaignAwareSummary,
            triage: {
              title: audienceTriageAction.title,
              detail: audienceTriageAction.detail,
              contact_total: metadata?.total || 0,
              available_fields: availableFields,
              attribute_keys: attributeKeys,
            },
          },
          goals: [
            'Assess audience targeting readiness',
            'Find rule, data coverage, match volume, and campaign handoff risks',
            'Recommend the next operator action before campaign launch',
          ],
        }),
      });
      setAiAudienceSummary(data.summary || []);
      setAiAudienceRecommendations(data.recommendations || []);
      return `AI Audience Review loaded ${formatInt(data.recommendations?.length || 0)} recommendation(s).`;
    });
  }

  async function deleteAudienceRow(audience: AudienceRead) {
    if (!window.confirm(`Delete audience "${audience.name}"?`)) return;
    await runAudienceOperation('Deleting audience', async () => {
      await fetchJson<{ id: string }>(`/api/v1/audiences/${audience.id}`, { method: 'DELETE' });
      if (selectedAudienceId === audience.id) resetAudienceEditor();
      await onRefresh();
      return `Deleted audience: ${audience.name}.`;
    });
  }

  async function archiveAudienceRow(audience: AudienceRead) {
    await runAudienceOperation('Archiving audience', async () => {
      await fetchJson<AudienceRead>(`/api/v1/audiences/${audience.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'archived' }),
      });
      await onRefresh();
      return `Archived audience: ${audience.name}.`;
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
        <section className={`audience-triage-panel full-span ${audienceTriageAction.tone}`}>
          <div className="audience-triage-head">
            <div>
              <span>Audience triage</span>
              <strong>{audienceTriageAction.title}</strong>
              <small>{audienceTriageAction.detail}</small>
            </div>
            <button className={audienceTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={audienceTriageAction.run} disabled={audienceTriageAction.disabled}>{audienceTriageAction.actionLabel}</button>
          </div>
          <div className="audience-triage-grid">
            {audienceTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="audience-foundation-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Audience Foundations</h3>
              <span className="muted">Contact attributes, client entities, snapshots, and campaign usage readiness.</span>
            </div>
            <a href="#data">Open Data</a>
          </div>
          <div className="audience-foundation-grid">
            {audienceFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="audience-segmentation-contract-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Audience Segmentation Contract</h3>
              <span className="muted">Field metadata, entity joins, consent filters, impact checks, snapshots, and campaign handoff requirements.</span>
            </div>
            <a href="#contacts">Open Contacts</a>
          </div>
          <div className="audience-segmentation-contract-grid">
            {audienceSegmentationContractItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
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
	                      onDoubleClick={() => { window.location.hash = `#audience/${audience.id}`; }}
	                    >
                      <td>{audience.name}</td>
                      <td><span className="pill">{audience.status}</span></td>
                      <td>{formatInt(performance?.estimated_count ?? audience.estimated_count)}</td>
                      <td>{formatInt(performance?.sent_count)}</td>
                      <td>{performance ? formatPct(performance.open_rate) : '-'}</td>
                      <td>{performance ? formatPct(performance.click_rate) : '-'}</td>
                      <td><RowActionMenu openHref={`#audience/${audience.id}`} onDelete={() => deleteAudienceRow(audience)} onArchive={() => archiveAudienceRow(audience)} /></td>
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
      <section className={`audience-triage-panel full-span ${audienceTriageAction.tone}`}>
        <div className="audience-triage-head">
          <div>
            <span>Audience triage</span>
            <strong>{audienceTriageAction.title}</strong>
            <small>{audienceTriageAction.detail}</small>
          </div>
          <button className={audienceTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={audienceTriageAction.run} disabled={audienceTriageAction.disabled}>{audienceTriageAction.actionLabel}</button>
        </div>
        <div className="audience-triage-grid">
          {audienceTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="audience-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Audience Foundations</h3>
            <span className="muted">Contact attributes, client entities, snapshots, and campaign usage readiness.</span>
          </div>
          <a href="#data">Open Data</a>
        </div>
        <div className="audience-foundation-grid">
          {audienceFoundationItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="audience-segmentation-contract-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Audience Segmentation Contract</h3>
            <span className="muted">Field metadata, entity joins, consent filters, impact checks, snapshots, and campaign handoff requirements.</span>
          </div>
          <a href="#contacts">Open Contacts</a>
        </div>
        <div className="audience-segmentation-contract-grid">
          {audienceSegmentationContractItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
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
      <section className={`audience-campaign-awareness full-span ${campaignAwareSummary.tone}`}>
        <div>
          <span>Campaign awareness</span>
          <strong>{campaignAwareSummary.title}</strong>
          <small>{campaignAwareSummary.detail}</small>
        </div>
        <div>
          <span>Latest campaign</span>
          <strong>{campaignAwareSummary.latest}</strong>
          <small>{selectedAudienceCampaigns.length ? `${formatInt(selectedAudienceCampaigns.length)} total campaign(s)` : 'Create a campaign from this audience when ready'}</small>
        </div>
        <a href="#campaigns">Open Campaigns</a>
      </section>
      <section className="audience-builder-map full-span" aria-label="Audience builder summary">
        <article className={metadata?.total ? 'good' : 'warn'}>
          <span>Contact data</span>
          <strong>{formatInt(metadata?.total || 0)} contacts</strong>
          <small>{formatInt(availableFields.length + attributeKeys.length)} fields available</small>
        </article>
        <article className={ruleJsonValid ? 'good' : 'warn'}>
          <span>Rule</span>
          <strong>{activeRuleField || 'No field selected'}</strong>
          <small>{activeRuleComparator || 'Choose comparator'}{activeRuleValue !== undefined ? ` ${String(activeRuleValue).slice(0, 28)}` : ''}</small>
        </article>
        <article className={matchedCount === null ? 'warn' : matchedCount > 0 ? 'good' : 'warn'}>
          <span>Preview impact</span>
          <strong>{matchedCount === null ? 'Not previewed' : `${formatInt(matchedCount)} matched`}</strong>
          <small>{matchRate === null ? 'Run preview' : `${formatPct(matchRate)} of known contacts`}</small>
        </article>
        <article className={selectedAudienceId && Number(matchedCount || 0) > 0 ? 'good' : 'warn'}>
          <span>Next action</span>
          <strong>{audienceNextAction.title}</strong>
          <small>{audienceNextAction.detail}</small>
        </article>
      </section>
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
        <div className="campaign-action-bar">
          <div>
            <strong>Audience</strong>
            <button className="primary" onClick={saveAudience} disabled={busy}>{isCreatingAudience ? 'Create Audience' : 'Save Changes'}</button>
          </div>
          <div>
            <strong>Preview</strong>
            <button className="ghost" onClick={previewAudience} disabled={busy}>Preview Contacts</button>
            {isPersistedAudience ? <button className="ghost" onClick={snapshotAudience} disabled={busy}>Create Snapshot</button> : null}
            <button className="ghost" onClick={reviewAudienceWithAi} disabled={busy}>AI Audience Review</button>
          </div>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className={`audience-next-action ${audienceNextAction.tone}`}>
          <div>
            <span>Guided audience next step</span>
            <strong>{audienceNextAction.title}</strong>
            <small>{audienceNextAction.detail}</small>
          </div>
          <button className={audienceNextAction.tone === 'good' ? 'ghost' : 'primary'} type="button" onClick={audienceNextAction.run} disabled={busy}>{audienceNextAction.actionLabel}</button>
        </div>
        <div className="audience-ai-review-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>AI Audience Review</h3>
              <span className="muted">{aiAudienceRecommendations?.length ? `${formatInt(aiAudienceRecommendations.length)} recommendation(s)` : 'Review targeting rule, data coverage, match volume, and campaign handoff.'}</span>
            </div>
            <button className="link-button" type="button" onClick={reviewAudienceWithAi} disabled={busy}>Run AI Review</button>
          </div>
          {aiAudienceSummary.length ? (
            <div className="audience-ai-summary">
              {aiAudienceSummary.slice(0, 4).map((item) => <span key={item}>{item}</span>)}
            </div>
          ) : null}
          {aiAudienceRecommendations?.length ? (
            <div className="recommendation-list">
              {aiAudienceRecommendations.slice(0, 5).map((item) => (
                <article key={item.code}>
                  <span className="pill">{item.priority}</span>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  <small>{item.suggested_action || item.suggested_instruction || 'Review recommendation.'}</small>
                </article>
              ))}
            </div>
          ) : (
            <div className="ai-empty-state">
              <strong>No AI audience review loaded</strong>
              <span>Run AI Audience Review after previewing reach to prioritize data coverage, targeting, and campaign handoff.</span>
            </div>
          )}
        </div>
        <div className={`audience-impact-summary ${audienceImpactSummary.tone}`}>
          <div>
            <span>Rule impact</span>
            <strong>{audienceImpactSummary.title}</strong>
            <small>{audienceImpactSummary.detail}</small>
          </div>
          <div>
            <span>Reach</span>
            <strong>{audienceImpactSummary.reach}</strong>
            <small>{matchedCount === null ? 'Preview pending' : `${formatInt(matchedCount)} contact(s)`}</small>
          </div>
          <div>
            <span>Samples</span>
            <strong>{audienceImpactSummary.sample}</strong>
            <small>{sampleContacts.length ? 'Inspect rows below' : 'Preview returns examples'}</small>
          </div>
        </div>
        <div className="workflow-section">
          <h3>1. Setup</h3>
          <div className="form-grid">
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
          <div className="audience-field-intel">
            <div>
              <span>Selected field</span>
              <strong>{selectedFieldProfile?.field || 'No field selected'}</strong>
              <small>{selectedFieldProfile ? `${selectedFieldProfile.kind} · ${selectedFieldProfile.coverage === null ? 'No samples' : `${formatPct(selectedFieldProfile.coverage)} sample coverage`}` : 'Choose a field chip to build a starter rule.'}</small>
            </div>
            <div>
              <span>Examples</span>
              <strong>{selectedFieldProfile?.examples.length ? selectedFieldProfile.examples.join(' · ') : 'No examples'}</strong>
              <small>{selectedFieldProfile ? `${formatInt(selectedFieldProfile.sampleCount)} sample contact(s) include this field` : `${formatInt(metadata?.sample_contacts?.length || 0)} sample contact(s) loaded`}</small>
            </div>
          </div>
          {fieldHints.length ? (
            <div className="audience-field-picker">
              <div className="field-profile-strip" aria-label="Field sample coverage">
                {highlightedFieldProfiles.map((profile) => (
                  <button type="button" className={activeRuleField === profile.field ? 'field-profile selected' : 'field-profile'} key={profile.field} onClick={() => insertFieldRule(profile.field)}>
                    <span>{profile.kind}</span>
                    <strong>{profile.field}</strong>
                    <small>{profile.coverage === null ? 'No samples' : `${formatPct(profile.coverage)} coverage`}</small>
                  </button>
                ))}
              </div>
              <div className="field-chip-row" aria-label="Available contact fields">
                {availableFields.slice(0, 12).map((field) => (
                  <button type="button" className={activeRuleField === field ? 'field-chip selected' : 'field-chip'} key={field} onClick={() => insertFieldRule(field)}>
                    <span>{field}</span>
                    {sampleValueForField(field) ? <small>{sampleValueForField(field)}</small> : null}
                  </button>
                ))}
              </div>
              {attributeFields.length ? (
                <div className="field-chip-row" aria-label="Available attribute fields">
                  {attributeFields.slice(0, 12).map((field) => (
                    <button type="button" className={activeRuleField === field ? 'field-chip selected attribute' : 'field-chip attribute'} key={field} onClick={() => insertFieldRule(field)}>
                      <span>{field}</span>
                      {sampleValueForField(field) ? <small>{sampleValueForField(field)}</small> : null}
                    </button>
                  ))}
                </div>
              ) : null}
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
        {sampleContacts.length ? (
          <div className="workflow-section">
            <h3>Matched Contacts Preview</h3>
            <table>
              <thead><tr><th>Email</th><th>Name</th><th>Source</th><th>Attributes</th><th>Status</th></tr></thead>
              <tbody>
                {sampleContacts.map((contact) => (
                  <tr key={contact.id}>
                    <td>{contact.email}</td>
                    <td>{[contact.first_name, contact.last_name].filter(Boolean).join(' ') || '-'}</td>
                    <td>{contact.source || '-'}</td>
                    <td>{Object.entries(contact.attributes || {}).slice(0, 3).map(([key, value]) => `${key}: ${String(value)}`).join(', ') || '-'}</td>
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
  const defaultTemplateSnapshot: TemplateEditSnapshot = {
    name: 'ESP Template Draft',
    subject: 'Hello {{ first_name }}',
    htmlBody: '<div class="email-container">\n  <p class="email-copy">Hello {{ first_name }},</p>\n  <p class="email-copy">Welcome to Email Engine.</p>\n</div>',
    cssBody: 'body { font-family: Arial, sans-serif; color: #111827; }\np { line-height: 1.5; }',
    designDocJson: '{"blocks":[]}',
  };
  const routeParts = route.split('/');
  const routeTemplateId = routeParts[0] === 'templates' && routeParts[1] && routeParts[1] !== 'new'
    ? routeParts[1]
    : '';
  const isDetailPage = routeParts[0] === 'templates' && Boolean(routeParts[1]);
  const isNewTemplate = routeParts[0] === 'templates' && routeParts[1] === 'new';
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [name, setName] = useState('ESP Template Draft');
  const [subject, setSubject] = useState('Hello {{ first_name }}');
  const [htmlBody, setHtmlBody] = useState(defaultTemplateSnapshot.htmlBody);
  const [cssBody, setCssBody] = useState('body { font-family: Arial, sans-serif; color: #111827; }\np { line-height: 1.5; }');
  const [savedTemplateSnapshot, setSavedTemplateSnapshot] = useState<TemplateEditSnapshot>(defaultTemplateSnapshot);
  const [variablesJson, setVariablesJson] = useState('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
  const [status, setStatus] = useState('Ready to edit or preview a template.');
  const [busy, setBusy] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewSubject, setPreviewSubject] = useState('');
  const [previewFreshness, setPreviewFreshness] = useState<'empty' | 'current' | 'stale'>('empty');
  const [previewViewport, setPreviewViewport] = useState<'desktop' | 'mobile'>('desktop');
  const [variables, setVariables] = useState<TemplateVariable[]>([]);
  const [templateRenderResult, setTemplateRenderResult] = useState<{
    label: string;
    subject: string;
    ok: boolean;
    errors: string[];
    variableCount: number;
    cssGapCount: number;
    sourceMode: 'edit' | 'design';
  } | null>(null);
  const [aiInstruction, setAiInstruction] = useState('Improve clarity, preserve all Jinja variables, add a stronger CTA, and keep the design email-safe.');
  const [aiInstructionMode, setAiInstructionMode] = useState('Custom');
  const [aiRecommendations, setAiRecommendations] = useState<AITemplateRecommendation[]>([]);
  const [aiNotes, setAiNotes] = useState<string[]>([]);
  const [pendingAiDraft, setPendingAiDraft] = useState<AITemplateDraft | null>(null);
  const [appliedAiDraftLabel, setAppliedAiDraftLabel] = useState('');
  const [templateVersions, setTemplateVersions] = useState<TemplateVersionRead[]>([]);
  const [selectedVersionReviewId, setSelectedVersionReviewId] = useState('');
  const [editorMode, setEditorMode] = useState<'edit' | 'design' | 'preview'>('edit');
  const [previewSourceMode, setPreviewSourceMode] = useState<'edit' | 'design'>('edit');
  const [designDoc, setDesignDoc] = useState<TemplateDesignDocument>({ blocks: [] });
  const [designDocEdited, setDesignDocEdited] = useState(false);
  const [designUndoStack, setDesignUndoStack] = useState<TemplateDesignHistoryEntry[]>([]);
  const [designRedoStack, setDesignRedoStack] = useState<TemplateDesignHistoryEntry[]>([]);
  const [selectedDesignBlockId, setSelectedDesignBlockId] = useState('');
  const [designInspectorFocusNonce, setDesignInspectorFocusNonce] = useState(0);
  const [draggedPaletteBlockType, setDraggedPaletteBlockType] = useState('');
  const [designHierarchyOpen, setDesignHierarchyOpen] = useState(true);
  const [designInspectorOpen, setDesignInspectorOpen] = useState(true);
  const [designPaneWidths, setDesignPaneWidths] = useState<DesignPaneWidths>(readStoredDesignPaneWidths);
  const [designCanvasZoom, setDesignCanvasZoom] = useState(readStoredDesignCanvasZoom);
  const [localTemplateDraft, setLocalTemplateDraft] = useState<TemplateLocalDraft | null>(null);
  const [templateFeedbackOpen, setTemplateFeedbackOpen] = useState(true);
  const [collapsedDesignTreeIds, setCollapsedDesignTreeIds] = useState<string[]>([]);
  const [activeDesignTreeAddId, setActiveDesignTreeAddId] = useState('');
  const [designTreeDropTarget, setDesignTreeDropTarget] = useState<{ id: string; position: 'before' | 'after' | 'inside' } | null>(null);
  const [htmlToolsOpen, setHtmlToolsOpen] = useState(false);
  const [cssToolsOpen, setCssToolsOpen] = useState(false);
  const htmlEditorRef = useRef<TemplateCodeEditorHandle | null>(null);
  const cssEditorRef = useRef<HTMLTextAreaElement | null>(null);
  const cssEditorSectionRef = useRef<HTMLDivElement | null>(null);
  const designInspectorRef = useRef<HTMLElement | null>(null);
  const designHierarchyRef = useRef<HTMLElement | null>(null);
  const [selectedCssClass, setSelectedCssClass] = useState('');
  const [cssClassKind, setCssClassKind] = useState<'container' | 'section' | 'button' | 'text' | 'image'>('container');
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
  const isPersistedTemplate = Boolean(selectedTemplateId);
  const isCreatingTemplate = !isPersistedTemplate;
  useEffect(() => {
    window.localStorage.setItem(DESIGN_PANE_WIDTHS_STORAGE_KEY, JSON.stringify(designPaneWidths));
  }, [designPaneWidths]);
  useEffect(() => {
    window.localStorage.setItem(DESIGN_CANVAS_ZOOM_STORAGE_KEY, designCanvasZoom);
  }, [designCanvasZoom]);
  const currentTemplateSnapshot: TemplateEditSnapshot = {
    name,
    subject,
    htmlBody,
    cssBody,
    designDocJson: designDocEdited ? semanticDesignDocJson(designDoc) : savedTemplateSnapshot.designDocJson,
  };
  const hasUnsavedTemplateChanges = currentTemplateSnapshot.name !== savedTemplateSnapshot.name
    || currentTemplateSnapshot.subject !== savedTemplateSnapshot.subject
    || currentTemplateSnapshot.htmlBody !== savedTemplateSnapshot.htmlBody
    || currentTemplateSnapshot.cssBody !== savedTemplateSnapshot.cssBody
    || currentTemplateSnapshot.designDocJson !== savedTemplateSnapshot.designDocJson;
  useEffect(() => {
    if (!hasUnsavedTemplateChanges) return;
    const draft: TemplateLocalDraft = {
      name,
      subject,
      htmlBody,
      cssBody,
      designDoc: cloneDesignDocument(designDoc),
      editorMode,
      updatedAt: Date.now(),
    };
    window.localStorage.setItem(templateDraftStorageKey(selectedTemplateId), JSON.stringify(draft));
    setLocalTemplateDraft(draft);
  }, [cssBody, designDoc, editorMode, hasUnsavedTemplateChanges, htmlBody, name, selectedTemplateId, subject]);
  const aiInstructionPresets = [
    {
      label: 'Tighten copy',
      instruction: 'Make the copy more concise and clearer, preserve all Jinja variables, and keep the same offer and structure.',
    },
    {
      label: 'Stronger CTA',
      instruction: 'Improve the call to action, make the next step obvious, preserve all Jinja variables, and keep the layout email-safe.',
    },
    {
      label: 'Personalize',
      instruction: 'Increase personalization using the available variables, preserve all existing Jinja logic, and avoid inventing unsupported variables.',
    },
    {
      label: 'Deliverability',
      instruction: 'Improve deliverability readiness by reducing spammy language, preserving required compliance content, and keeping HTML email-safe.',
    },
  ];
  function chooseAiInstructionPreset(label: string, instruction: string) {
    setAiInstruction(instruction);
    setAiInstructionMode(label);
  }
  const previewStatusText = previewFreshness === 'current'
    ? 'Preview reflects current sample data.'
    : previewFreshness === 'stale'
      ? 'Preview is stale. Use the Preview tab to refresh.'
      : 'Use the Preview tab to detect variables and render.';
  const templateCategories = new Set(templates.map((template) => template.category || 'template'));
  const detectedVariableNames = variables.map((item) => item.name);
  function extractHtmlClassNames(source: string) {
    return Array.from(source.matchAll(/class=["']([^"']+)["']/g))
    .flatMap((match) => match[1].split(/\s+/).filter(Boolean))
    .filter((className, index, all) => all.indexOf(className) === index)
    .sort();
  }

  function cssHasRuleForClass(source: string, className: string) {
    if (!className) return false;
    const escaped = className.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`\\.${escaped}\\s*\\{[^}]*\\}`, 'm').test(source);
  }

  function designBlockClassNames(blocks: TemplateDesignBlock[]): string[] {
    return blocks.flatMap((block) => [
      ...String(block.className || '').split(/\s+/).filter(Boolean),
      ...designBlockClassNames(block.children || []),
    ]);
  }

  const designClassNames = Array.from(new Set(designBlockClassNames(designDoc.blocks)))
    .sort();
  const designBlockSummary = (() => {
    const allBlocks = flattenDesignBlocks(designDoc.blocks);
    const rawBlocks = allBlocks.filter((block) => block.type === 'html' || block.type === 'raw');
    const editableBlocks = allBlocks.length - rawBlocks.length;
    const editablePercent = allBlocks.length ? Math.round((editableBlocks / allBlocks.length) * 100) : 0;
    return { allBlocks, rawBlocks, editableBlocks, editablePercent };
  })();
  const designImportConfidence = !designBlockSummary.allBlocks.length
    ? {
      tone: 'warn',
      title: 'No import',
      detail: 'Import source or add blocks to inspect editability.',
    }
    : designBlockSummary.rawBlocks.length
      ? {
        tone: 'warn',
        title: `${formatInt(designBlockSummary.editablePercent)}% editable`,
        detail: `${formatInt(designBlockSummary.rawBlocks.length)} raw HTML/Jinja block(s) preserved for Source editing.`,
      }
      : {
        tone: 'good',
        title: 'Fully editable',
        detail: `${formatInt(designBlockSummary.editableBlocks)} design block(s) can be edited visually.`,
      };
  const htmlClassNames = Array.from(new Set([...extractHtmlClassNames(htmlBody), ...designClassNames])).sort();
  const cssClassCoverage = htmlClassNames.map((className) => {
    const rule = cssRuleForClass(className);
    return {
      name: className,
      hasRule: Boolean(rule),
      kind: inferCssClassKind(className, rule),
    };
  });
  const missingCssClasses = cssClassCoverage.filter((item) => !item.hasRule).map((item) => item.name);
  const designWorkflowStatus = designDocEdited
    ? 'Design changes are not synced to HTML/Jinja yet.'
    : hasUnsavedTemplateChanges
      ? 'Template has unsaved code, CSS, or metadata changes.'
      : 'Design and saved template state are aligned.';
  const designNextAction = (() => {
    if (!designDoc.blocks.length) {
      return {
        tone: 'warn',
        title: 'Next: add a block',
        detail: 'Start with a section, heading, paragraph, image, button, or custom HTML block.',
        action: '',
      };
    }
    if (designDocEdited) {
      return {
        tone: 'warn',
        title: 'Next: sync visual edits',
        detail: 'Sync writes the current Design block model into HTML/Jinja so it can be saved and rendered consistently.',
        action: 'sync',
      };
    }
    if (missingCssClasses.length) {
      return {
        tone: 'warn',
        title: 'Next: fix CSS coverage',
        detail: `${formatInt(missingCssClasses.length)} detected class rule(s) are missing. Create rules before final preview.`,
        action: 'css',
      };
    }
    if (previewFreshness !== 'current') {
      return {
        tone: 'warn',
        title: 'Next: preview render',
        detail: 'Render the template with sample variables to confirm Jinja, layout, and CSS output.',
        action: 'preview',
      };
    }
    if (hasUnsavedTemplateChanges) {
      return {
        tone: 'warn',
        title: 'Next: save changes',
        detail: 'Preview is current and no CSS gaps are detected. Save the template when the design looks right.',
        action: 'save',
      };
    }
    return {
      tone: 'good',
      title: 'Ready for refinement',
      detail: 'Design, CSS, preview, and saved state are aligned. Continue editing or move into campaign workflow.',
      action: '',
    };
  })();
  const classableHtmlTagCount = Array.from(htmlBody.matchAll(/<([a-z][a-z0-9-]*)(\s[^<>]*)?>/gi))
    .filter((match) => {
      const tag = match[1].toLowerCase();
      const attrs = match[2] || '';
      return !['html', 'head', 'body', 'meta', 'title', 'style', 'script', 'br'].includes(tag) && !/\sclass\s*=/.test(attrs);
    }).length;
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
      label: 'Styling',
      ready: !missingCssClasses.length,
      detail: missingCssClasses.length ? `${formatInt(missingCssClasses.length)} HTML class(es) need CSS rules.` : 'Detected classes have CSS coverage.',
    },
    {
      label: 'Preview',
      ready: previewFreshness === 'current',
      detail: previewFreshness === 'current' ? 'Rendered with sample variables.' : previewStatusText,
    },
  ];
  const templateSteps = [
    { label: 'Setup', detail: name.trim() || 'Name the template', ready: Boolean(name.trim()) },
    { label: 'Subject', detail: subject.trim() || 'Add a subject line', ready: Boolean(subject.trim()) },
    { label: 'Content', detail: htmlBody.trim() ? 'HTML/Jinja ready' : 'Add HTML/Jinja', ready: Boolean(htmlBody.trim()) },
    { label: 'Variables', detail: variables.length ? `${formatInt(variables.length)} detected` : 'Auto-detected at preview', ready: Boolean(variables.length) },
    { label: 'Preview', detail: previewFreshness === 'current' ? 'Preview rendered' : 'Render preview', ready: previewFreshness === 'current' },
  ];
  const pendingAiDraftNotes = pendingAiDraft ? (pendingAiDraft.change_summary || pendingAiDraft.notes || []) : [];
  const pendingAiDraftVariables = pendingAiDraft?.sample_variables ? Object.keys(pendingAiDraft.sample_variables) : [];
  const pendingAiDraftReview = pendingAiDraft ? {
    subjectChanged: (pendingAiDraft.subject || '') !== subject,
    htmlDelta: (pendingAiDraft.html_body || '').length - htmlBody.length,
    cssDelta: (pendingAiDraft.css_body || '').length - cssBody.length,
    cssChanged: (pendingAiDraft.css_body || '') !== cssBody,
  } : null;
  const aiAssistNextStep = pendingAiDraft
    ? {
      tone: 'warn',
      title: 'Review pending AI draft',
      detail: 'Preview the draft, then apply or discard it before requesting another edit.',
      actionLabel: 'Preview Draft',
      run: () => { void previewAiDraft(pendingAiDraft); },
    }
    : appliedAiDraftLabel
      ? {
        tone: 'warn',
        title: 'Save applied AI edit',
        detail: `Applied ${appliedAiDraftLabel}. Save to persist the template version.`,
        actionLabel: 'Save Changes',
        run: () => { void saveTemplate(); },
      }
      : aiRecommendations.length
        ? {
          tone: 'good',
          title: 'Suggestions loaded',
          detail: `${formatInt(aiRecommendations.length)} recommendation(s) are ready for review below.`,
          actionLabel: 'Review Suggestions',
          run: () => setTemplateFeedbackOpen(true),
        }
        : isPersistedTemplate
          ? {
            tone: 'neutral',
            title: 'Send an AI edit request',
            detail: aiInstruction.trim() ? 'Use the selected request preset or custom instruction.' : 'Choose a preset or write a custom instruction first.',
            actionLabel: 'Review AI Edit',
            run: () => { void applyAiEdit(); },
          }
          : {
            tone: 'neutral',
            title: 'Draft from template brief',
            detail: 'Create templates with AI first, then preview and apply the generated draft.',
            actionLabel: 'Draft with AI',
            run: () => { void draftWithAi(); },
          };
  function formatSignedCount(value: number) {
    if (!value) return '0';
    return `${value > 0 ? '+' : ''}${formatInt(value)}`;
  }

  function versionReview(version: TemplateVersionRead) {
    const versionDesignDocJson = version.document_json?.blocks
      ? semanticDesignDocJson(version.document_json as TemplateDesignDocument)
      : '{"blocks":[]}';
    return {
      subjectChanged: version.subject !== subject,
      htmlDelta: (version.html_body || '').length - htmlBody.length,
      cssDelta: (version.css_body || '').length - cssBody.length,
      cssChanged: (version.css_body || '') !== cssBody,
      textChanged: (version.text_body || '') !== '',
      documentChanged: versionDesignDocJson !== semanticDesignDocJson(designDoc),
    };
  }

  function designDocFromTemplate(template: TemplateRead): TemplateDesignDocument {
    const blocks = template.document_json?.blocks;
    if (Array.isArray(blocks) && blocks.length) {
      return { blocks: blocks.map((block, index) => normalizeDesignBlock(block, index)) };
    }
    return htmlToDesignDocument(template.html_body || '');
  }

  async function designDocForTemplate(template: TemplateRead): Promise<TemplateDesignDocument> {
    try {
      const documentData = await fetchJson<TemplateDocumentRead>(`/api/v1/templates/${template.id}/document`);
      const blocks = documentData.document_json?.blocks;
      if (Array.isArray(blocks) && blocks.length) {
        return { blocks: blocks.map((block, index) => normalizeDesignBlock(block, index)) };
      }
    } catch {
      // Fall back below so older templates and transient document endpoint failures still open.
    }
    return designDocFromTemplate(template);
  }

  async function loadTemplateVersions(templateId: string) {
    if (!templateId) {
      setTemplateVersions([]);
      return;
    }
    try {
      const versions = await fetchJson<TemplateVersionRead[]>(`/api/v1/templates/${templateId}/versions`);
      setTemplateVersions(versions);
    } catch {
      setTemplateVersions([]);
    }
  }

  function semanticDesignDocJson(document: TemplateDesignDocument) {
    const semanticBlock = (block: TemplateDesignBlock): Omit<TemplateDesignBlock, 'id'> => {
      const { id: _id, ...rest } = block;
      return {
        ...rest,
        children: block.children?.map(semanticBlock),
      };
    };
    return JSON.stringify({
      blocks: document.blocks.map(semanticBlock),
    });
  }

  function htmlToDesignDocument(source: string): TemplateDesignDocument {
    const trimmed = source.trim();
    if (!trimmed) return { blocks: [newDesignBlock('paragraph')] };
    const blocks = parseHtmlDesignBlocks(trimmed);
    if (!blocks.length) return { blocks: [{ id: designBlockId(), type: 'html', code: trimmed }] };
    return { blocks: designBlocksWithVisibleRoot(blocks) };
  }

  function designBlocksWithVisibleRoot(blocks: TemplateDesignBlock[]) {
    if (deepestDesignSectionDepth(blocks) >= 2) return blocks;
    if (blocks.length === 1 && blocks[0].type === 'section') {
      return [{
        id: designBlockId(),
        type: 'section',
        className: 'email-shell',
        bg: '#f5f7fb',
        padding_y: 24,
        children: blocks,
      }];
    }
    return [{
      id: designBlockId(),
      type: 'section',
      className: 'email-shell',
      bg: '#f5f7fb',
      padding_y: 24,
      children: [{
        id: designBlockId(),
        type: 'section',
        className: 'email-container',
        bg: '',
        padding_y: 24,
        children: blocks,
      }],
    }];
  }

  function deepestDesignSectionDepth(blocks: TemplateDesignBlock[], depth = 0): number {
    return blocks.reduce((maxDepth, block) => {
      const blockDepth = block.type === 'section' ? depth + 1 : depth;
      return Math.max(maxDepth, blockDepth, deepestDesignSectionDepth(block.children || [], blockDepth));
    }, depth);
  }

  function isDesignContainerBlock(block: TemplateDesignBlock) {
    return block.type === 'section' || block.type === 'columns';
  }

  function htmlAttribute(source: string, name: string) {
    const pattern = new RegExp(`${name}\\s*=\\s*["']([^"']*)["']`, 'i');
    return source.match(pattern)?.[1] || '';
  }

  function styleValue(style: string, property: string) {
    const pattern = new RegExp(`${property}\\s*:\\s*([^;]+)`, 'i');
    return style.match(pattern)?.[1]?.trim() || '';
  }

  function cssNumber(value: string, fallback: number) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function paddingPair(value: string, fallbackY: number, fallbackX: number) {
    const parts = value.trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return { y: fallbackY, x: fallbackX };
    return {
      y: cssNumber(parts[0], fallbackY),
      x: cssNumber(parts[1] || parts[0], fallbackX),
    };
  }

  function htmlInner(markup: string, tag: string) {
    const match = markup.match(new RegExp(`^<${tag}\\b[^>]*>([\\s\\S]*)<\\/${tag}>$`, 'i'));
    return match?.[1]?.trim() || '';
  }

  function htmlText(markup: string) {
    return decodeTemplateText(markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim());
  }

  function footerTextWithoutLinks(markup: string) {
    return htmlText(markup.replace(/<a\b[\s\S]*?<\/a>/gi, ''));
  }

  function findMatchingHtmlClose(source: string, tag: string, openEnd: number) {
    const pattern = new RegExp(`<\\/?${tag}\\b[^>]*>`, 'gi');
    pattern.lastIndex = openEnd;
    let depth = 1;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(source))) {
      if (match[0].startsWith('</')) depth -= 1;
      else if (!match[0].endsWith('/>')) depth += 1;
      if (depth === 0) return pattern.lastIndex;
    }
    return -1;
  }

  function nextDesignToken(source: string, cursor: number) {
    const nextMatch = source.slice(cursor).match(/({%\s*(if|for)\b[\s\S]*?{%\s*end\2\s*%}|<h[1-3]\b|<p\b|<a\b|<img\b|<ul\b|<ol\b|<table\b|<footer\b|<nav\b|<hr\b|<div\b)/i);
    if (!nextMatch || nextMatch.index === undefined) return null;
    const start = cursor + nextMatch.index;
    const tokenStart = nextMatch[0];
    if (tokenStart.startsWith('{%')) return { start, end: start + tokenStart.length, markup: tokenStart };
    const tag = tokenStart.match(/^<([a-z0-9]+)/i)?.[1]?.toLowerCase() || '';
    const openEnd = source.indexOf('>', start);
    if (openEnd < 0) return null;
    if (tag === 'img' || tag === 'hr') return { start, end: openEnd + 1, markup: source.slice(start, openEnd + 1) };
    const end = findMatchingHtmlClose(source, tag, openEnd + 1);
    if (end < 0) return null;
    return { start, end, markup: source.slice(start, end) };
  }

  function parseHtmlDesignBlocks(source: string) {
    const blocks: TemplateDesignBlock[] = [];
    let cursor = 0;
    let token: ReturnType<typeof nextDesignToken> | null;
    while ((token = nextDesignToken(source, cursor))) {
      const before = source.slice(cursor, token.start).trim();
      if (before) blocks.push({ id: designBlockId(), type: 'html', code: before });
      blocks.push(...parseHtmlDesignBlock(token.markup));
      cursor = token.end;
    }
    const after = source.slice(cursor).trim();
    if (after) blocks.push({ id: designBlockId(), type: 'html', code: after });
    return blocks.filter((block) => block.type !== 'html' || String(block.code || '').trim());
  }

  function parseHtmlDesignBlock(markup: string): TemplateDesignBlock[] {
    const id = designBlockId();
    const className = htmlAttribute(markup, 'class');
    const style = htmlAttribute(markup, 'style');
    const heading = markup.match(/^<h([1-3])\b/i);
    if (heading) {
      return [{ id, type: 'heading', level: Number(heading[1]), text: htmlText(htmlInner(markup, `h${heading[1]}`)), className, align: styleValue(style, 'text-align') || 'left' }];
    }
    if (/^<p\b/i.test(markup)) {
      const link = markup.match(/<a\b([\s\S]*?)>([\s\S]*?)<\/a>/i);
      if (link && /\bbutton\b/.test(htmlAttribute(link[0], 'class'))) {
        const linkStyle = htmlAttribute(link[0], 'style');
        return [{
          id,
          type: 'button',
          text: htmlText(link[2]),
          href: htmlAttribute(link[0], 'href') || '{{ tracking_click }}',
          className: htmlAttribute(link[0], 'class') || 'button',
          bg: styleValue(linkStyle, 'background') || '#2563eb',
          color: styleValue(linkStyle, 'color') || '#ffffff',
          radius: Number.parseInt(styleValue(linkStyle, 'border-radius'), 10) || 6,
        }];
      }
      return [{ id, type: 'paragraph', text: htmlText(htmlInner(markup, 'p')), className, align: styleValue(style, 'text-align') || 'left', color: styleValue(style, 'color') }];
    }
    if (/^<a\b/i.test(markup) && /<img\b/i.test(markup)) {
      const imageMarkup = markup.match(/<img\b[^>]*>/i)?.[0] || '';
      return [{ id, type: 'image', src: htmlAttribute(imageMarkup, 'src'), alt: htmlAttribute(imageMarkup, 'alt'), href: htmlAttribute(markup, 'href'), className: htmlAttribute(imageMarkup, 'class'), width: Number.parseInt(htmlAttribute(imageMarkup, 'width'), 10) || 600 }];
    }
    if (/^<img\b/i.test(markup)) {
      return [{ id, type: 'image', src: htmlAttribute(markup, 'src'), alt: htmlAttribute(markup, 'alt'), className, width: Number.parseInt(htmlAttribute(markup, 'width'), 10) || 600 }];
    }
    if (/^<(ul|ol)\b/i.test(markup)) {
      return [{
        id,
        type: 'list',
        ordered: /^<ol\b/i.test(markup),
        className,
        items: Array.from(markup.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/gi)).map((item) => htmlText(item[1])),
      }];
    }
    if (/^<table\b/i.test(markup)) {
      const rows = Array.from(markup.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)).map((row) => (
        Array.from(row[1].matchAll(/<t[hd]\b[^>]*>([\s\S]*?)<\/t[hd]>/gi)).map((cell) => htmlText(cell[1]))
      )).filter((row) => row.length);
      const firstRowIsHeader = /<tr\b[^>]*>[\s\S]*?<th\b/i.test(markup);
      const headerStyle = htmlAttribute(markup.match(/<th\b[^>]*>/i)?.[0] || '', 'style');
      const cellStyle = htmlAttribute(markup.match(/<t[hd]\b[^>]*>/i)?.[0] || '', 'style');
      const cellPadding = paddingPair(styleValue(cellStyle, 'padding'), 10, 12);
      return [{
        id,
        type: 'table',
        className: className || 'email-table',
        table_headers: firstRowIsHeader ? rows[0] || [] : [],
        table_rows: firstRowIsHeader ? rows.slice(1) : rows,
        bg: styleValue(style, 'background') || styleValue(headerStyle, 'background') || '#f8fafc',
        color: styleValue(style, 'color') || '#111827',
        padding_y: cellPadding.y,
        padding_x: cellPadding.x,
      }];
    }
    if (/^<footer\b/i.test(markup)) {
      const footerInner = htmlInner(markup, 'footer');
      return [{
        id,
        type: 'footer',
        text: footerTextWithoutLinks(footerInner) || 'You are receiving this email because you subscribed to updates.',
        href: htmlAttribute(markup.match(/<a\b[\s\S]*?<\/a>/i)?.[0] || '', 'href') || '{{ unsubscribe_url }}',
        className: className || 'email-footer',
        color: styleValue(style, 'color') || '#64748b',
        padding_y: Number.parseInt(styleValue(style, 'padding'), 10) || 18,
      }];
    }
    if (/^<nav\b/i.test(markup)) {
      const links = Array.from(markup.matchAll(/<a\b[\s\S]*?>([\s\S]*?)<\/a>/gi)).map((link) => ({
        label: htmlText(link[1]) || 'Link',
        url: htmlAttribute(link[0], 'href'),
      })).filter((link) => link.url);
      return [{
        id,
        type: 'social_links',
        className: className || 'email-social-links',
        social_links: links.length ? links : [
          { label: 'LinkedIn', url: '{{ linkedin_url }}' },
          { label: 'Instagram', url: '{{ instagram_url }}' },
        ],
        color: styleValue(style, 'color') || '#2563eb',
        align: styleValue(style, 'text-align') || 'center',
        padding_y: Number.parseInt(styleValue(style, 'padding'), 10) || 12,
      }];
    }
    if (/^<hr\b/i.test(markup)) return [{ id, type: 'divider', color: styleValue(style, 'border-top')?.split(' ').pop() || '#d8dee6', className }];
    if (/^<div\b/i.test(markup) && /height\s*:/.test(style)) return [{ id, type: 'spacer', height: Number.parseInt(styleValue(style, 'height'), 10) || 24, className }];
    if (/^<div\b/i.test(markup)) {
      const inner = htmlInner(markup, 'div');
      const nestedBlocks = inner ? parseHtmlDesignBlocks(inner) : [];
      if (nestedBlocks.length > 1 || nestedBlocks.some((block) => block.type !== 'html')) {
        return [{
          id,
          type: 'section',
          className,
          bg: styleValue(style, 'background') || '',
          padding_y: Number.parseInt(styleValue(style, 'padding'), 10) || undefined,
          children: nestedBlocks,
        }];
      }
    }
    return [{ id, type: 'html', code: markup }];
  }

  function designBlockId() {
    return `b_${Math.random().toString(36).slice(2, 10)}`;
  }

  function cloneDesignBlock(block: TemplateDesignBlock): TemplateDesignBlock {
    return {
      ...block,
      id: designBlockId(),
      items: block.items ? [...block.items] : block.items,
      table_headers: block.table_headers ? [...block.table_headers] : block.table_headers,
      table_rows: block.table_rows ? block.table_rows.map((row) => [...row]) : block.table_rows,
      social_links: block.social_links ? block.social_links.map((link) => ({ ...link })) : block.social_links,
      children: block.children?.map(cloneDesignBlock),
    };
  }

  function snapshotDesignBlock(block: TemplateDesignBlock): TemplateDesignBlock {
    return {
      ...block,
      items: block.items ? [...block.items] : block.items,
      table_headers: block.table_headers ? [...block.table_headers] : block.table_headers,
      table_rows: block.table_rows ? block.table_rows.map((row) => [...row]) : block.table_rows,
      social_links: block.social_links ? block.social_links.map((link) => ({ ...link })) : block.social_links,
      children: block.children?.map(snapshotDesignBlock),
    };
  }

  function normalizeDesignBlock(value: unknown, index: number): TemplateDesignBlock {
    const block = value && typeof value === 'object' ? value as TemplateDesignBlock : { type: 'paragraph' };
    return {
      ...block,
      id: block.id || `b_${index}`,
      type: block.type || 'paragraph',
      items: Array.isArray(block.items) ? block.items.map((item) => String(item)) : block.items,
      table_headers: Array.isArray(block.table_headers) ? block.table_headers.map((item) => String(item)) : block.table_headers,
      table_rows: Array.isArray(block.table_rows)
        ? block.table_rows.map((row) => Array.isArray(row) ? row.map((cell) => String(cell)) : [String(row)])
        : block.table_rows,
      social_links: Array.isArray(block.social_links)
        ? block.social_links.map((link) => ({
          label: String(link?.label || 'Link'),
          url: String(link?.url || '#'),
        }))
        : block.social_links,
      children: Array.isArray(block.children) ? block.children.map((child, childIndex) => normalizeDesignBlock(child, childIndex)) : block.children,
    };
  }

  function newDesignBlock(type: string): TemplateDesignBlock {
    const id = designBlockId();
    if (type === 'heading') return { id, type, text: 'Main headline', level: 1, align: 'left', className: 'email-title' };
    if (type === 'button') return { id, type, text: 'Call to Action', href: '{{ tracking_click }}', className: 'button', bg: '#2563eb', color: '#ffffff', radius: 6, padding_y: 11, padding_x: 16 };
    if (type === 'list') return { id, type, ordered: false, items: ['First point', 'Second point'], className: 'email-list' };
    if (type === 'image') return { id, type, src: '{{ hero_image_url }}', alt: 'Image', href: '', width: 600, className: 'email-image' };
    if (type === 'table') return {
      id,
      type,
      className: 'email-table',
      table_headers: ['Metric', 'Current', 'Goal'],
      table_rows: [
        ['Open rate', '{{ open_rate }}', '28%'],
        ['Click rate', '{{ click_rate }}', '4%'],
      ],
      bg: '#f8fafc',
      color: '#111827',
      padding_y: 10,
      padding_x: 12,
    };
    if (type === 'footer') return {
      id,
      type,
      text: 'You are receiving this email because you subscribed to updates.',
      href: '{{ unsubscribe_url }}',
      className: 'email-footer',
      color: '#64748b',
      padding_y: 18,
      padding_x: 0,
    };
    if (type === 'social_links') return {
      id,
      type,
      className: 'email-social-links',
      social_links: [
        { label: 'LinkedIn', url: '{{ linkedin_url }}' },
        { label: 'Instagram', url: '{{ instagram_url }}' },
        { label: 'Website', url: '{{ website_url }}' },
      ],
      color: '#2563eb',
      align: 'center',
      padding_y: 12,
      padding_x: 0,
    };
    if (type === 'divider') return { id, type, color: '#d8dee6', className: 'email-divider' };
    if (type === 'spacer') return { id, type, height: 24, className: 'email-spacer' };
    if (type === 'section') return { id, type, className: 'email-section', bg: '', padding_y: 18, children: [newDesignBlock('heading'), newDesignBlock('paragraph')] };
    if (type === 'columns') return {
      id,
      type,
      className: 'email-columns',
      bg: '',
      padding_y: 8,
      gap: 16,
      mobile_stack: 'stack',
      children: [
        { ...newDesignBlock('section'), className: 'email-column', padding_y: 14, children: [newDesignBlock('heading'), newDesignBlock('paragraph')] },
        { ...newDesignBlock('section'), className: 'email-column', padding_y: 14, children: [newDesignBlock('paragraph'), newDesignBlock('button')] },
      ],
    };
    if (type === 'trust_signal') return { id, type, text: 'Trusted by teams building better email workflows.', className: 'secondary-text' };
    if (type === 'html') return { id, type, code: '<p class="email-copy">Custom HTML or Jinja</p>' };
    return { id, type: 'paragraph', text: 'Add body copy with {{ first_name }}.', align: 'left', color: '', className: 'email-copy' };
  }

  function normalizedTableRows(block: TemplateDesignBlock) {
    const headers = (block.table_headers || []).map((item) => String(item));
    const columnCount = Math.max(headers.length, ...(block.table_rows || []).map((row) => row.length), 1);
    const rows = (block.table_rows?.length ? block.table_rows : [['Label', 'Value']]).map((row) => (
      Array.from({ length: columnCount }, (_, index) => String(row[index] ?? ''))
    ));
    return { headers, rows, columnCount };
  }

  function tableRowsText(block: TemplateDesignBlock) {
    return (block.table_rows || []).map((row) => row.join(' | ')).join('\n');
  }

  function parseTableRowsText(value: string) {
    return value.split('\n')
      .map((row) => row.split('|').map((cell) => cell.trim()))
      .filter((row) => row.some(Boolean));
  }

  function normalizedSocialLinks(block: TemplateDesignBlock) {
    const links = block.social_links?.length ? block.social_links : [
      { label: 'LinkedIn', url: '{{ linkedin_url }}' },
      { label: 'Instagram', url: '{{ instagram_url }}' },
    ];
    return links.map((link) => ({
      label: String(link.label || 'Link'),
      url: String(link.url || '#'),
    }));
  }

  function socialLinksText(block: TemplateDesignBlock) {
    return normalizedSocialLinks(block).map((link) => `${link.label} | ${link.url}`).join('\n');
  }

  function parseSocialLinksText(value: string) {
    return value.split('\n')
      .map((row) => {
        const [label, ...urlParts] = row.split('|');
        return { label: label.trim(), url: urlParts.join('|').trim() };
      })
      .filter((link) => link.label || link.url)
      .map((link) => ({ label: link.label || 'Link', url: link.url || '#' }));
  }

  function designBlockToHtml(block: TemplateDesignBlock) {
    const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
    const textBlockStyle = (base = '') => [
      base,
      block.color ? `color:${block.color};` : '',
      block.bg ? `background:${block.bg};` : '',
      block.padding_y || block.padding_x ? `padding:${Number(block.padding_y || 0)}px ${Number(block.padding_x || 0)}px;` : '',
    ].filter(Boolean).join('');
    if (block.type === 'heading') {
      const level = Math.min(3, Math.max(1, Number(block.level || 1)));
      const style = textBlockStyle(`text-align:${block.align || 'left'};`);
      return `<h${level}${classAttr} style="${style}">${escapeTemplateText(block.text)}</h${level}>`;
    }
    if (block.type === 'paragraph') {
      if (block.html) return `<p${classAttr}>${block.html}</p>`;
      const style = textBlockStyle(`text-align:${block.align || 'left'};`);
      return `<p${classAttr} style="${style}">${escapeTemplateText(block.text).replace(/\n/g, '<br>')}</p>`;
    }
    if (block.type === 'button') {
      const style = `display:inline-block;background:${block.bg || '#2563eb'};color:${block.color || '#ffffff'};padding:${Number(block.padding_y || 11)}px ${Number(block.padding_x || 16)}px;text-decoration:none;border-radius:${Number(block.radius || 6)}px;font-weight:700;`;
      return `<p class="email-action"><a${classAttr || ' class="button"'} href="${escapeTemplateText(block.href || '{{ tracking_click }}')}" style="${style}">${escapeTemplateText(block.text || 'Call to Action')}</a></p>`;
    }
    if (block.type === 'list') {
      const tag = block.ordered ? 'ol' : 'ul';
      const items = (block.items || []).map((item) => `<li>${escapeTemplateText(item)}</li>`).join('');
      const style = textBlockStyle();
      return `<${tag}${classAttr}${style ? ` style="${style}"` : ''}>${items}</${tag}>`;
    }
    if (block.type === 'image') {
      const image = `<img${classAttr} src="${escapeTemplateText(block.src)}" alt="${escapeTemplateText(block.alt)}" width="${Number(block.width || 600)}" style="display:block;border:0;width:100%;max-width:${Number(block.width || 600)}px;height:auto;" />`;
      return block.href ? `<a href="${escapeTemplateText(block.href)}">${image}</a>` : image;
    }
    if (block.type === 'table') {
      const { headers, rows } = normalizedTableRows(block);
      const cellPadding = `${Number(block.padding_y ?? 10)}px ${Number(block.padding_x ?? 12)}px`;
      const tableStyle = `width:100%;border-collapse:collapse;color:${block.color || '#111827'};`;
      const headerHtml = headers.length
        ? `<thead><tr>${headers.map((header) => `<th style="border:1px solid #d8dee6;background:${block.bg || '#f8fafc'};padding:${cellPadding};text-align:left;">${escapeTemplateText(header)}</th>`).join('')}</tr></thead>`
        : '';
      const bodyHtml = `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td style="border:1px solid #d8dee6;padding:${cellPadding};vertical-align:top;">${escapeTemplateText(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`;
      return `<table${classAttr || ' class="email-table"'} role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="${tableStyle}">${headerHtml}${bodyHtml}</table>`;
    }
    if (block.type === 'footer') {
      const style = textBlockStyle(`text-align:${block.align || 'center'};font-size:12px;line-height:1.5;`);
      const footerText = escapeTemplateText(block.text || 'You are receiving this email because you subscribed to updates.');
      const link = `<a href="${escapeTemplateText(block.href || '{{ unsubscribe_url }}')}">Unsubscribe</a>`;
      return `<footer${classAttr || ' class="email-footer"'} style="${style}">${footerText}<br>${link}</footer>`;
    }
    if (block.type === 'social_links') {
      const style = textBlockStyle(`text-align:${block.align || 'center'};font-size:13px;line-height:1.5;`);
      const links = normalizedSocialLinks(block).map((link) => `<a href="${escapeTemplateText(link.url)}" style="color:${block.color || '#2563eb'};text-decoration:none;font-weight:700;">${escapeTemplateText(link.label)}</a>`).join(' <span style="color:#cbd5e1;">|</span> ');
      return `<nav${classAttr || ' class="email-social-links"'} style="${style}">${links}</nav>`;
    }
    if (block.type === 'divider') return `<hr${classAttr} style="border:0;border-top:1px solid ${block.color || '#d8dee6'};" />`;
    if (block.type === 'spacer') return `<div${classAttr} style="height:${Number(block.height || 24)}px;line-height:${Number(block.height || 24)}px;font-size:0;">&nbsp;</div>`;
    if (block.type === 'section') {
      const style = `${block.bg ? `background:${block.bg};` : ''}${block.padding_y ? `padding:${Number(block.padding_y)}px;` : ''}`;
      const children = (block.children || []).map(designBlockToHtml).join('\n');
      return `<div${classAttr} style="${style}">\n${children.split('\n').map((line) => `  ${line}`).join('\n')}\n</div>`;
    }
    if (block.type === 'columns') {
      const columns = (block.children || []).length ? (block.children || []) : [newDesignBlock('section'), newDesignBlock('section')];
      const gap = Math.max(0, Number(block.gap ?? 16));
      const mobileStack = block.mobile_stack || 'stack';
      const mobileClass = mobileStack === 'reverse' ? 'stack-mobile-reverse' : mobileStack === 'keep' ? 'keep-mobile' : 'stack-mobile';
      const columnClass = `${block.className || 'email-columns'} ${mobileClass}`.trim();
      const columnClassAttr = ` class="${escapeTemplateText(columnClass)}"`;
      const tableStyle = `width:100%;border-collapse:collapse;${block.bg ? `background:${block.bg};` : ''}`;
      const outerPadding = Number(block.padding_y || 0);
      const explicitTotal = columns.reduce((total, child) => total + Math.max(0, Number(child.width || 0)), 0);
      const defaultWidth = Math.floor(100 / columns.length);
      const cells = columns.map((child) => {
        const width = explicitTotal > 0
          ? Math.max(1, Math.round((Math.max(0, Number(child.width || 0)) || defaultWidth) / Math.max(explicitTotal, 1) * 100))
          : defaultWidth;
        const childHtml = designBlockToHtml(child);
        return `<td width="${width}%" valign="top" style="width:${width}%;vertical-align:top;padding:${Math.floor(gap / 2)}px;">\n${childHtml.split('\n').map((line) => `      ${line}`).join('\n')}\n    </td>`;
      }).join('\n');
      const table = `<table${columnClassAttr} data-mobile-stack="${mobileStack}" role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="${tableStyle}">\n  <tr>\n    ${cells}\n  </tr>\n</table>`;
      if (!outerPadding) return table;
      return `<div style="padding:${outerPadding}px;">\n${table.split('\n').map((line) => `  ${line}`).join('\n')}\n</div>`;
    }
    if (block.type === 'trust_signal') return `<p${classAttr || ' class="secondary-text"'} style="${textBlockStyle('text-align:center;')}">${escapeTemplateText(block.text)}</p>`;
    return block.code || '';
  }

  function flattenDesignBlocks(blocks: TemplateDesignBlock[]): TemplateDesignBlock[] {
    return blocks.flatMap((block) => [block, ...flattenDesignBlocks(block.children || [])]);
  }

  function designDocumentTemplateSource(document = designDoc) {
    return document.blocks.map(designBlockToHtml).join('\n');
  }

  function cloneDesignDocument(document: TemplateDesignDocument): TemplateDesignDocument {
    return {
      blocks: document.blocks.map((block) => snapshotDesignBlock(block)),
    };
  }

  function designHistoryEntry(document = designDoc, selectedBlockId = selectedDesignBlockId): TemplateDesignHistoryEntry {
    return {
      document: cloneDesignDocument(document),
      selectedBlockId,
    };
  }

  function rememberDesignState() {
    const snapshot = designHistoryEntry();
    setDesignUndoStack((current) => {
      const last = current[current.length - 1];
      if (last && semanticDesignDocJson(last.document) === semanticDesignDocJson(snapshot.document)) return current;
      return [...current.slice(-39), snapshot];
    });
    setDesignRedoStack([]);
  }

  function restoreDesignHistorySnapshot(snapshot: TemplateDesignHistoryEntry) {
    const restoredDocument = cloneDesignDocument(snapshot.document);
    const restoredBlocks = flattenDesignBlocks(restoredDocument.blocks);
    setDesignDoc(restoredDocument);
    setSelectedDesignBlockId(restoredBlocks.some((block) => block.id === snapshot.selectedBlockId) ? snapshot.selectedBlockId : restoredBlocks[0]?.id || '');
    setDesignDocEdited(true);
    markPreviewStale();
  }

  function undoDesignChange() {
    const previous = designUndoStack[designUndoStack.length - 1];
    if (!previous) return;
    setDesignRedoStack((current) => [...current.slice(-39), designHistoryEntry()]);
    setDesignUndoStack((current) => current.slice(0, -1));
    restoreDesignHistorySnapshot(previous);
    setStatus('Undid last design change.');
  }

  function redoDesignChange() {
    const next = designRedoStack[designRedoStack.length - 1];
    if (!next) return;
    setDesignUndoStack((current) => [...current.slice(-39), designHistoryEntry()]);
    setDesignRedoStack((current) => current.slice(0, -1));
    restoreDesignHistorySnapshot(next);
    setStatus('Redid design change.');
  }

  const flatDesignBlocks = flattenDesignBlocks(designDoc.blocks);
  const maxDesignTreeDepth = designTreeMaxDepth(designDoc.blocks);
  const selectedDesignBlock = flatDesignBlocks.find((block) => block.id === selectedDesignBlockId) || flatDesignBlocks[0];
  const selectedDesignBlockIndex = selectedDesignBlock ? flatDesignBlocks.findIndex((block) => block.id === selectedDesignBlock.id) : -1;
  const designWorkspaceStyle = {
    '--design-hierarchy-width': `${designPaneWidths.hierarchy}px`,
    '--design-inspector-width': `${designPaneWidths.inspector}px`,
  } as CSSProperties;
  const designCanvasZoomValue = designCanvasZoom === 'fit' ? 0.86 : Number(designCanvasZoom);
  const designCanvasFrameStyle = {
    '--design-canvas-zoom': String(designCanvasZoomValue || 1),
  } as CSSProperties;
  function setDesignPaneWidth(pane: 'hierarchy' | 'inspector', width: number) {
    const minWidth = pane === 'hierarchy' ? 132 : 260;
    const maxWidth = pane === 'hierarchy' ? 360 : 480;
    setDesignPaneWidths((current) => ({
      ...current,
      [pane]: Math.max(minWidth, Math.min(maxWidth, Math.round(width))),
    }));
  }

  function handleDesignPaneResizeKey(
    pane: 'hierarchy' | 'inspector',
    event: KeyboardEvent<HTMLDivElement>,
  ) {
    const direction = pane === 'hierarchy' ? 1 : -1;
    const step = event.shiftKey ? 24 : 12;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      setDesignPaneWidth(pane, designPaneWidths[pane] - step * direction);
    }
    else if (event.key === 'ArrowRight') {
      event.preventDefault();
      setDesignPaneWidth(pane, designPaneWidths[pane] + step * direction);
    }
    else if (event.key === 'Home') {
      event.preventDefault();
      setDesignPaneWidth(pane, pane === 'hierarchy' ? 132 : 260);
    }
    else if (event.key === 'End') {
      event.preventDefault();
      setDesignPaneWidth(pane, pane === 'hierarchy' ? 360 : 480);
    }
    else if (event.key === 'Enter') {
      event.preventDefault();
      setDesignPaneWidth(pane, pane === 'hierarchy' ? 180 : 300);
    }
  }

  function startDesignPaneResize(
    pane: 'hierarchy' | 'inspector',
    event: PointerEvent<HTMLDivElement>,
  ) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = designPaneWidths[pane];
    const direction = pane === 'hierarchy' ? 1 : -1;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    function handlePointerMove(moveEvent: globalThis.PointerEvent) {
      const delta = (moveEvent.clientX - startX) * direction;
      setDesignPaneWidth(pane, startWidth + delta);
    }

    function handlePointerUp() {
      document.removeEventListener('pointermove', handlePointerMove);
      document.removeEventListener('pointerup', handlePointerUp);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    }

    document.addEventListener('pointermove', handlePointerMove);
    document.addEventListener('pointerup', handlePointerUp, { once: true });
  }
  function findDesignBlockParent(id: string, blocks = designDoc.blocks, parent: TemplateDesignBlock | null = null): TemplateDesignBlock | null {
    for (const block of blocks) {
      if (block.id === id) return parent;
      const childParent = findDesignBlockParent(id, block.children || [], block);
      if (childParent) return childParent;
    }
    return null;
  }
  function designBlockAncestorIds(id: string, blocks = designDoc.blocks, ancestors: string[] = []): string[] {
    for (const block of blocks) {
      if (block.id === id) return ancestors;
      const childAncestors = designBlockAncestorIds(id, block.children || [], [...ancestors, block.id]);
      if (childAncestors.length) return childAncestors;
    }
    return [];
  }
  function designBlockPath(id: string, blocks = designDoc.blocks, path: TemplateDesignBlock[] = []): TemplateDesignBlock[] {
    for (const block of blocks) {
      const nextPath = [...path, block];
      if (block.id === id) return nextPath;
      const childPath = designBlockPath(id, block.children || [], nextPath);
      if (childPath.length) return childPath;
    }
    return [];
  }
  function designTreeMaxDepth(blocks: TemplateDesignBlock[], depth = 0): number {
    if (!blocks.length) return depth;
    return blocks.reduce((maxDepth, block) => Math.max(maxDepth, designTreeMaxDepth(block.children || [], depth + 1)), depth);
  }
  function revealDesignBlockInHierarchy(id: string, ancestorIds = designBlockAncestorIds(id)) {
    if (!ancestorIds.length) return;
    setCollapsedDesignTreeIds((current) => current.filter((item) => !ancestorIds.includes(item)));
  }
  function selectDesignBlock(id: string, ancestorIds?: string[]) {
    revealDesignBlockInHierarchy(id, ancestorIds);
    setActiveDesignTreeAddId('');
    setSelectedDesignBlockId(id);
  }
  const selectedDesignBlockParent = selectedDesignBlock ? findDesignBlockParent(selectedDesignBlock.id) : null;
  const selectedDesignBlockPath = selectedDesignBlock ? designBlockPath(selectedDesignBlock.id) : [];
  const selectedDesignAncestorIds = selectedDesignBlock ? designBlockAncestorIds(selectedDesignBlock.id) : [];
  function designBlockSiblingContext(id: string, blocks = designDoc.blocks, parent: TemplateDesignBlock | null = null): { blocks: TemplateDesignBlock[]; index: number; parent: TemplateDesignBlock | null } | null {
    const index = blocks.findIndex((block) => block.id === id);
    if (index >= 0) return { blocks, index, parent };
    for (const block of blocks) {
      const childContext = designBlockSiblingContext(id, block.children || [], block);
      if (childContext) return childContext;
    }
    return null;
  }
  function designBlockSiblingInfo(id: string, blocks = designDoc.blocks): { index: number; count: number } | null {
    const index = blocks.findIndex((block) => block.id === id);
    if (index >= 0) return { index, count: blocks.length };
    for (const block of blocks) {
      const childInfo = designBlockSiblingInfo(id, block.children || []);
      if (childInfo) return childInfo;
    }
    return null;
  }
  function canMoveDesignBlock(id: string, direction: -1 | 1) {
    const siblingInfo = designBlockSiblingInfo(id);
    if (!siblingInfo) return false;
    const nextIndex = siblingInfo.index + direction;
    return nextIndex >= 0 && nextIndex < siblingInfo.count;
  }
  function canIndentDesignBlock(id: string) {
    const siblingContext = designBlockSiblingContext(id);
    return Boolean(siblingContext && siblingContext.index > 0 && isDesignContainerBlock(siblingContext.blocks[siblingContext.index - 1]));
  }
  const designPaletteBlockTypes = ['section', 'columns', 'heading', 'paragraph', 'button', 'image', 'table', 'list', 'divider', 'spacer', 'trust_signal', 'social_links', 'footer', 'html'];
  function designBlockTypeLabel(type: string) {
    const labels: Record<string, string> = {
      section: 'Section',
      columns: 'Columns',
      heading: 'Heading',
      paragraph: 'Paragraph',
      button: 'Button',
      image: 'Image',
      table: 'Table',
      list: 'List',
      divider: 'Divider',
      spacer: 'Spacer',
      trust_signal: 'Trust signal',
      social_links: 'Social links',
      footer: 'Footer',
      html: 'HTML / Jinja',
    };
    return labels[type] || type.replace('_', ' ');
  }

  function designTreeMeta(block: TemplateDesignBlock) {
    const raw = String(block.code || block.html || '');
    const className = String(block.className || '').split(/\s+/).filter(Boolean)[0] || '';
    const descendantCount = countDesignDescendants(block);
    const typeLabels: Record<string, string> = {
      heading: `Heading H${block.level || 1}`,
      section: className === 'email-shell' ? 'Email shell' : className === 'email-container' ? 'Email container' : 'Section',
      columns: 'Columns',
      paragraph: 'Paragraph',
      button: 'Button',
      image: 'Image',
      table: 'Table',
      list: block.ordered ? 'Numbered list' : 'List',
      divider: 'Divider',
      spacer: 'Spacer',
      trust_signal: 'Trust signal',
      social_links: 'Social links',
      footer: 'Footer',
      html: /{%\s*(if|elif|else|endif)\b/.test(raw) ? 'Conditional' : /{%\s*(for|endfor)\b/.test(raw) ? 'Loop' : 'HTML / Jinja',
    };
    const preview = block.type === 'table'
      ? `${(block.table_rows || []).length} row(s)`
      : block.type === 'social_links'
        ? `${normalizedSocialLinks(block).length} link(s)`
      : block.type === 'list'
      ? `${(block.items || []).length} item(s)`
      : decodeTemplateText(block.text || block.alt || block.code || block.html || block.src || '').slice(0, 64);
    return {
      label: typeLabels[block.type] || designBlockTypeLabel(block.type),
      preview,
      className,
      childCount: block.children?.length || 0,
      descendantCount,
    };
  }

  function countDesignDescendants(block: TemplateDesignBlock): number {
    return (block.children || []).reduce((count, child) => count + 1 + countDesignDescendants(child), 0);
  }

	  function toggleDesignTreeNode(id: string) {
	    setCollapsedDesignTreeIds((current) => (
	      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
	    ));
	  }

  function addDesignTreeChildBlock(parentId: string, type: string) {
    addDesignChildBlock(parentId, type);
    setActiveDesignTreeAddId('');
  }

  function designTreeDropPosition(event: DragEvent<HTMLElement>, block: TemplateDesignBlock): 'before' | 'after' | 'inside' {
    const rect = event.currentTarget.getBoundingClientRect();
    if (isDesignContainerBlock(block)) {
      const offset = event.clientY - rect.top;
      if (offset > rect.height * 0.3 && offset < rect.height * 0.7) return 'inside';
    }
    return event.clientY > rect.top + rect.height / 2 ? 'after' : 'before';
  }

  function designTreeDropLabel(position: string) {
    if (position === 'inside') return 'Nest inside';
    if (position === 'after') return 'Insert after';
    if (position === 'before') return 'Insert before';
    return '';
  }

  function visibleDesignTreeBlocks(blocks = designDoc.blocks): TemplateDesignBlock[] {
    return blocks.flatMap((block) => [
      block,
      ...(collapsedDesignTreeIds.includes(block.id) ? [] : visibleDesignTreeBlocks(block.children || [])),
    ]);
  }

  function handleDesignTreeKeyDown(event: KeyboardEvent<HTMLButtonElement>, block: TemplateDesignBlock) {
    const visibleBlocks = visibleDesignTreeBlocks();
    const currentIndex = visibleBlocks.findIndex((item) => item.id === block.id);
    const parent = findDesignBlockParent(block.id);
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      const nextBlock = visibleBlocks[Math.min(currentIndex + 1, visibleBlocks.length - 1)];
      if (nextBlock) selectDesignBlock(nextBlock.id);
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      const previousBlock = visibleBlocks[Math.max(currentIndex - 1, 0)];
      if (previousBlock) selectDesignBlock(previousBlock.id);
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      const children = block.children || [];
      if (children.length && collapsedDesignTreeIds.includes(block.id)) {
        setCollapsedDesignTreeIds((current) => current.filter((item) => item !== block.id));
      } else if (children[0]) {
        selectDesignBlock(children[0].id, [...designBlockAncestorIds(block.id), block.id]);
      }
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      const children = block.children || [];
      if (children.length && !collapsedDesignTreeIds.includes(block.id)) {
        setCollapsedDesignTreeIds((current) => [...current, block.id]);
      } else if (parent) {
        selectDesignBlock(parent.id);
      }
    }
  }

  function renderDesignHierarchy(blocks: TemplateDesignBlock[], depth = 0) {
    return blocks.flatMap((block, index) => {
      const meta = designTreeMeta(block);
      const children = block.children || [];
      const hasChildren = children.length > 0;
      const collapsed = collapsedDesignTreeIds.includes(block.id);
      const addMenuOpen = activeDesignTreeAddId === block.id;
      const inSelectedPath = selectedDesignAncestorIds.includes(block.id);
      const activeDropPosition = designTreeDropTarget?.id === block.id ? designTreeDropTarget.position : '';
      const isLastSibling = index === blocks.length - 1;
      return [
        <button
          className={`design-tree-row ${depth ? 'nested' : 'root'} ${isLastSibling ? 'last-sibling' : 'has-next-sibling'} ${inSelectedPath ? 'ancestor' : ''} ${selectedDesignBlockId === block.id ? 'selected' : ''} ${addMenuOpen ? 'adding' : ''} ${activeDropPosition ? `drop-${activeDropPosition}` : ''}`}
          data-design-tree-id={block.id}
          key={block.id}
          role="treeitem"
          aria-level={depth + 1}
          aria-expanded={hasChildren ? !collapsed : undefined}
          type="button"
          tabIndex={selectedDesignBlockId === block.id ? 0 : -1}
          draggable={!busy}
          onClick={() => selectDesignBlock(block.id)}
          onKeyDown={(event) => handleDesignTreeKeyDown(event, block)}
          onDragStart={(event) => {
            if (busy) return;
            const dragHandle = (event.target as HTMLElement).closest('.design-tree-drag-handle');
            if (!dragHandle) {
              event.preventDefault();
              setStatus('Use the hierarchy drag handle to reorder blocks.');
              return;
            }
            selectDesignBlock(block.id);
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', block.id);
          }}
          onDragEnd={() => setDesignTreeDropTarget(null)}
          onDragOver={(event) => {
            if (busy) return;
            const source = event.dataTransfer.getData('text/plain') || (draggedPaletteBlockType ? `new:${draggedPaletteBlockType}` : '');
            if (!source || source === block.id) return;
            event.preventDefault();
            event.dataTransfer.dropEffect = source.startsWith('new:') ? 'copy' : 'move';
            setDesignTreeDropTarget({ id: block.id, position: designTreeDropPosition(event, block) });
          }}
          onDragLeave={(event) => {
            if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
            setDesignTreeDropTarget((current) => current?.id === block.id ? null : current);
          }}
          onDrop={(event) => {
            if (busy) return;
            const source = event.dataTransfer.getData('text/plain') || (draggedPaletteBlockType ? `new:${draggedPaletteBlockType}` : '');
            if (!source || source === block.id) return;
            event.preventDefault();
            const position = designTreeDropPosition(event, block);
            setDesignTreeDropTarget(null);
            if (position === 'inside') {
              if (source.startsWith('new:')) {
                addDesignChildBlock(block.id, source.slice(4));
                return;
              }
              moveDesignBlockIntoSection(source, block.id);
              setStatus(`Nested design block inside ${designBlockTypeLabel(block.type).toLowerCase()}.`);
              return;
            }
            if (source.startsWith('new:')) {
              addDesignBlock(source.slice(4), block.id, position);
              return;
            }
            reorderDesignBlock(source, block.id, position);
            setStatus('Reordered design blocks from the hierarchy.');
          }}
          style={{ '--tree-depth': depth } as Record<string, number>}
        >
          <span className="design-tree-drag-handle" title="Drag to reorder">::</span>
          <span className="design-tree-level" title={`Hierarchy level ${depth + 1}`}>{depth + 1}</span>
          <span className="design-tree-icon">{meta.label.slice(0, 2)}</span>
          <span className="design-tree-copy">
            <strong>
              {meta.label}
              {collapsed && meta.descendantCount ? <em className="design-tree-hidden-count">{meta.descendantCount} hidden</em> : null}
            </strong>
            <small>{meta.className ? `.${meta.className}` : meta.preview || (children.length ? `${meta.childCount} nested block(s)` : 'No detail')}</small>
          </span>
	          <span
	            className={`design-tree-add ${isDesignContainerBlock(block) ? 'visible' : ''}`}
	            title={isDesignContainerBlock(block) ? `Add block inside ${designBlockTypeLabel(block.type).toLowerCase()}` : undefined}
	            onClick={isDesignContainerBlock(block) ? (event) => {
	              event.stopPropagation();
	              setActiveDesignTreeAddId((current) => current === block.id ? '' : block.id);
	            } : undefined}
	          >
	            {isDesignContainerBlock(block) ? 'Add' : ''}
	          </span>
          <span
            className={`design-tree-branch ${hasChildren ? 'has-children' : 'leaf'}`}
            title={hasChildren ? `${collapsed ? 'Expand' : 'Collapse'} ${meta.label}` : undefined}
            onClick={hasChildren ? (event) => {
              event.stopPropagation();
              toggleDesignTreeNode(block.id);
            } : undefined}
          >
            {hasChildren ? (collapsed ? '+' : '-') : ''}
          </span>
          {activeDropPosition ? <span className="design-tree-drop-label">{designTreeDropLabel(activeDropPosition)}</span> : null}
	        </button>,
        ...(addMenuOpen ? [
          <div className="design-tree-add-menu" key={`${block.id}-add-menu`} style={{ '--tree-depth': depth } as Record<string, number>}>
            <button className="close" type="button" onClick={() => setActiveDesignTreeAddId('')} title="Close chooser">x</button>
            {['section', 'columns', 'heading', 'paragraph', 'button', 'image', 'table', 'list', 'divider', 'spacer', 'social_links', 'footer', 'html'].map((type) => (
              <button key={type} type="button" onClick={() => addDesignTreeChildBlock(block.id, type)}>
                {designBlockTypeLabel(type)}
              </button>
            ))}
          </div>,
        ] : []),
        ...(collapsed ? [] : renderDesignHierarchy(children, depth + 1)),
      ];
    });
  }

  function designCanvasBlockContentHtml(block: TemplateDesignBlock) {
    const editableAttrs = (value: unknown) => `contenteditable="true" spellcheck="false" data-design-edit-field="text" data-design-original-value="${escapeTemplateText(value)}"`;
    const textBlockStyle = (base = '') => [
      base,
      block.color ? `color:${block.color};` : '',
      block.bg ? `background:${block.bg};` : '',
      block.padding_y || block.padding_x ? `padding:${Number(block.padding_y || 0)}px ${Number(block.padding_x || 0)}px;` : '',
    ].filter(Boolean).join('');
    if (block.type === 'heading') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
      const level = Math.min(3, Math.max(1, Number(block.level || 1)));
      return `<h${level}${classAttr} ${editableAttrs(block.text)} style="${textBlockStyle(`text-align:${block.align || 'left'};`)}">${escapeTemplateText(block.text)}</h${level}>`;
    }
    if (block.type === 'paragraph' && !block.html) {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
      const style = textBlockStyle(`text-align:${block.align || 'left'};`);
      return `<p${classAttr} ${editableAttrs(block.text)} style="${style}">${escapeTemplateText(block.text).replace(/\n/g, '<br>')}</p>`;
    }
    if (block.type === 'button') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : ' class="button"';
      const style = `display:inline-block;background:${block.bg || '#2563eb'};color:${block.color || '#ffffff'};padding:${Number(block.padding_y || 11)}px ${Number(block.padding_x || 16)}px;text-decoration:none;border-radius:${Number(block.radius || 6)}px;font-weight:700;`;
      const buttonHtml = `<p class="email-action"><a${classAttr} ${editableAttrs(block.text || 'Call to Action')} href="${escapeTemplateText(block.href || '{{ tracking_click }}')}" style="${style}">${escapeTemplateText(block.text || 'Call to Action')}</a></p>`;
      if (block.id !== selectedDesignBlockId) return buttonHtml;
      return `<div class="ee-button-edit-wrap">
        ${buttonHtml}
        <div class="ee-field-edit-panel">
          <label>Button URL<input data-design-block-field="href" value="${escapeTemplateText(block.href || '{{ tracking_click }}')}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'trust_signal') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : ' class="secondary-text"';
      return `<p${classAttr} ${editableAttrs(block.text)} style="${textBlockStyle('text-align:center;')}">${escapeTemplateText(block.text)}</p>`;
    }
    if (block.type === 'footer') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : ' class="email-footer"';
      const style = textBlockStyle(`text-align:${block.align || 'center'};font-size:12px;line-height:1.5;`);
      const footerHtml = `<footer${classAttr} style="${style}"><span ${editableAttrs(block.text || 'You are receiving this email because you subscribed to updates.')}>${escapeTemplateText(block.text || 'You are receiving this email because you subscribed to updates.')}</span><br><a href="${escapeTemplateText(block.href || '{{ unsubscribe_url }}')}">Unsubscribe</a></footer>`;
      if (block.id !== selectedDesignBlockId) return footerHtml;
      return `<div class="ee-footer-edit-wrap">
        ${footerHtml}
        <div class="ee-field-edit-panel">
          <label>Unsubscribe URL<input data-design-block-field="href" value="${escapeTemplateText(block.href || '{{ unsubscribe_url }}')}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'social_links') return designBlockToHtml(block);
    if (block.type === 'list') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
      const tag = block.ordered ? 'ol' : 'ul';
      const style = textBlockStyle();
      const items = (block.items || []).map((item, index) => (
        `<li contenteditable="true" spellcheck="false" data-design-edit-field="item" data-design-edit-index="${index}" data-design-original-value="${escapeTemplateText(item)}">${escapeTemplateText(item)}</li>`
      )).join('');
      return `<${tag}${classAttr}${style ? ` style="${style}"` : ''}>${items}</${tag}>`;
    }
    if (block.type === 'image') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
      const image = `<img${classAttr} src="${escapeTemplateText(block.src)}" alt="${escapeTemplateText(block.alt)}" width="${Number(block.width || 600)}" style="display:block;border:0;width:100%;max-width:${Number(block.width || 600)}px;height:auto;" />`;
      const imageHtml = block.href ? `<a href="${escapeTemplateText(block.href)}">${image}</a>` : image;
      if (block.id !== selectedDesignBlockId) return imageHtml;
      return `<div class="ee-image-edit-wrap">
        ${imageHtml}
        <div class="ee-image-edit-panel">
          <label>Image URL<input data-design-image-field="src" value="${escapeTemplateText(block.src)}" /></label>
          <label>Alt text<input data-design-image-field="alt" value="${escapeTemplateText(block.alt)}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'table') {
      const tableHtml = designBlockToHtml(block);
      if (block.id !== selectedDesignBlockId) return tableHtml;
      return `<div class="ee-table-edit-wrap">
        ${tableHtml}
        <div class="ee-table-edit-panel">
          <label>Header background<input type="color" data-design-block-field="bg" value="${escapeTemplateText(block.bg || '#f8fafc')}" /></label>
          <label>Text color<input type="color" data-design-block-field="color" value="${escapeTemplateText(block.color || '#111827')}" /></label>
          <label>Cell vertical padding<input type="number" min="0" max="48" data-design-block-field="padding_y" value="${Number(block.padding_y ?? 10)}" /></label>
          <label>Cell horizontal padding<input type="number" min="0" max="48" data-design-block-field="padding_x" value="${Number(block.padding_x ?? 12)}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'divider') {
      const dividerHtml = designBlockToHtml(block);
      if (block.id !== selectedDesignBlockId) return dividerHtml;
      return `<div class="ee-spacing-edit-wrap">
        ${dividerHtml}
        <div class="ee-field-edit-panel">
          <label>Line color<input type="color" data-design-block-field="color" value="${escapeTemplateText(block.color || '#d8dee6')}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'spacer') {
      const spacerHtml = designBlockToHtml(block);
      if (block.id !== selectedDesignBlockId) return spacerHtml;
      return `<div class="ee-spacing-edit-wrap">
        ${spacerHtml}
        <div class="ee-field-edit-panel">
          <label>Height<input type="number" min="0" max="120" data-design-block-field="height" value="${Number(block.height || 24)}" /></label>
        </div>
      </div>`;
    }
    if (block.type === 'columns') {
      const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : ' class="email-columns"';
      const columnTemplate = (block.children || []).length
        ? (block.children || []).map((child) => `${Math.max(1, Number(child.width || 1))}fr`).join(' ')
        : 'repeat(2,minmax(0,1fr))';
      const mobileStack = block.mobile_stack || 'stack';
      const mobileNote = mobileStack === 'reverse' ? 'Mobile: reverse stack' : mobileStack === 'keep' ? 'Mobile: keep columns' : 'Mobile: stack columns';
      const style = `${block.bg ? `background:${block.bg};` : ''}${block.padding_y ? `padding:${Number(block.padding_y)}px;` : ''}display:grid;grid-template-columns:${columnTemplate};gap:${Number(block.gap ?? 16)}px;`;
      const children = (block.children || []).map(designCanvasBlockHtml).join('\n');
      const emptyHint = children ? '' : '<div class="ee-section-empty">Drop blocks here</div>';
      const columnControls = block.id === selectedDesignBlockId
        ? `<div class="ee-section-edit-panel">
            <label>Background<input type="color" data-design-block-field="bg" value="${escapeTemplateText(block.bg || '#ffffff')}" /></label>
            <label>Padding<input type="number" min="0" max="80" data-design-block-field="padding_y" value="${Number(block.padding_y || 0)}" /></label>
            <label>Gap<input type="number" min="0" max="48" data-design-block-field="gap" value="${Number(block.gap ?? 16)}" /></label>
          </div>`
        : '';
      return `<div${classAttr} data-design-section-body="${escapeTemplateText(block.id)}" data-mobile-stack="${mobileStack}" style="${style}">\n<span class="ee-design-mobile-note">${mobileNote}</span>\n${columnControls}\n${children.split('\n').map((line) => `  ${line}`).join('\n')}\n${emptyHint}\n</div>`;
    }
    if (block.type !== 'section') return designBlockToHtml(block);
    const classAttr = block.className ? ` class="${escapeTemplateText(block.className)}"` : '';
    const style = `${block.bg ? `background:${block.bg};` : ''}${block.padding_y ? `padding:${Number(block.padding_y)}px;` : ''}`;
    const children = (block.children || []).map(designCanvasBlockHtml).join('\n');
    const emptyHint = children ? '' : '<div class="ee-section-empty">Drop blocks here</div>';
    const sectionControls = block.id === selectedDesignBlockId
      ? `<div class="ee-section-edit-panel">
          <label>Background<input type="color" data-design-block-field="bg" value="${escapeTemplateText(block.bg || '#ffffff')}" /></label>
          <label>Padding<input type="number" min="0" max="80" data-design-block-field="padding_y" value="${Number(block.padding_y || 0)}" /></label>
        </div>`
      : '';
    return `<div${classAttr} data-design-section-body="${escapeTemplateText(block.id)}" style="${style}">\n${sectionControls}\n${children.split('\n').map((line) => `  ${line}`).join('\n')}\n${emptyHint}\n</div>`;
  }

  function canEditDesignBlockTextOnCanvas(block: TemplateDesignBlock) {
    return block.type === 'heading'
      || block.type === 'button'
      || block.type === 'list'
      || block.type === 'trust_signal'
      || block.type === 'footer'
      || (block.type === 'paragraph' && !block.html);
  }

  function designCanvasEditHint(block: TemplateDesignBlock) {
    if (block.type === 'list') return 'Click list item to edit';
    if (block.type === 'button') return 'Edit text or URL';
    if (block.type === 'image') return 'Edit image details';
    if (block.type === 'table') return 'Edit table in inspector';
    if (block.type === 'footer') return 'Edit footer text or URL';
    if (block.type === 'social_links') return 'Edit social links in inspector';
    if (block.type === 'section') return 'Edit section style';
    if (block.type === 'columns') return 'Edit columns style';
    if (block.type === 'spacer') return 'Edit spacer height';
    if (block.type === 'divider') return 'Edit divider color';
    if (canEditDesignBlockTextOnCanvas(block)) return 'Click text to edit';
    return '';
  }

  function designCanvasBlockHtml(block: TemplateDesignBlock) {
    const meta = designTreeMeta(block);
    const selectedClass = block.id === selectedDesignBlockId ? ' selected' : selectedDesignAncestorIds.includes(block.id) ? ' ancestor' : '';
    const wrapAction = !isDesignContainerBlock(block)
      ? '<button type="button" data-design-action="wrap">Wrap</button>'
      : '';
    const parentAction = findDesignBlockParent(block.id)
      ? '<button type="button" data-design-action="parent">Parent</button><button type="button" data-design-action="outdent">Outdent</button><button type="button" data-design-action="root">Root</button>'
      : '';
    const selectedActions = block.id === selectedDesignBlockId
      ? `<div class="ee-design-actions">
          <button type="button" data-design-action="edit">Edit</button>
          <button type="button" data-design-action="style">Style</button>
          <button type="button" data-design-action="up">Up</button>
          <button type="button" data-design-action="down">Down</button>
          <button type="button" data-design-action="indent">Indent</button>
          ${parentAction}
          ${wrapAction}
          <button type="button" data-design-action="duplicate">Duplicate</button>
          <button type="button" data-design-action="delete">Delete</button>
        </div>`
			      : '';
    const editHintText = block.id === selectedDesignBlockId ? designCanvasEditHint(block) : '';
    const editableHint = editHintText
      ? `<span class="ee-design-edit-hint">${escapeTemplateText(editHintText)}</span>`
      : '';
    return `<div class="ee-design-block${selectedClass}" draggable="true" data-design-block-id="${escapeTemplateText(block.id)}" data-design-block-type="${escapeTemplateText(block.type)}" title="${escapeTemplateText(meta.label)}">
<span class="ee-design-block-label">${escapeTemplateText(meta.label)}</span>
${selectedActions}
${editableHint}
${designCanvasBlockContentHtml(block).split('\n').map((line) => `        ${line}`).join('\n')}
      </div>`;
  }

  function designCanvasSrcDoc() {
    const bodyHtml = designDoc.blocks.map(designCanvasBlockHtml).join('\n');
    return `<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <style>
      body { margin: 0; padding: 24px; background: #eef3f8; font-family: Arial, sans-serif; color: #111827; }
      .email-container { max-width: 640px; min-height: 420px; margin: 0 auto; background: #ffffff; padding: 28px; border-radius: 8px; }
      .email-container.ee-root-drop-target { outline: 2px dashed #10b981; outline-offset: 8px; }
      img { max-width: 100%; }
      .ee-design-block { position: relative; margin: 0 0 10px; padding: 4px; border: 1px solid transparent; border-radius: 6px; cursor: grab; transition: border-color 0.14s ease, background 0.14s ease, box-shadow 0.14s ease; }
      .ee-design-block:hover { border-color: #8bb7ff; background: rgba(37, 99, 235, 0.04); }
      .ee-design-block.ancestor { border-color: #bfdbfe; background: rgba(37, 99, 235, 0.035); }
      .ee-design-block.selected { border-color: #2563eb; background: rgba(37, 99, 235, 0.08); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12); }
      .ee-design-block-label { position: absolute; z-index: 9; top: -18px; left: 8px; display: none; border: 1px solid #bfdbfe; border-radius: 999px; background: #ffffff; color: #1d4ed8; font: 800 10px/1 Arial, sans-serif; padding: 5px 7px; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12); pointer-events: none; }
      .ee-design-block:hover > .ee-design-block-label, .ee-design-block.selected > .ee-design-block-label { display: block; }
      .ee-design-block.ee-drop-target-before { border-top-color: #10b981; border-top-width: 3px; background: rgba(16, 185, 129, 0.06); }
      .ee-design-block.ee-drop-target-after { border-bottom-color: #10b981; border-bottom-width: 3px; background: rgba(16, 185, 129, 0.06); }
      .ee-design-block .ee-design-block { margin: 8px 0; }
      .ee-design-actions { position: absolute; z-index: 10; top: -18px; right: 8px; display: flex; flex-wrap: wrap; justify-content: flex-end; max-width: min(96%, 520px); gap: 4px; padding: 3px; border: 1px solid #bfdbfe; border-radius: 12px; background: #ffffff; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14); }
      .ee-design-actions button { border: 0; border-radius: 999px; background: #eff6ff; color: #1d4ed8; font: 700 10px/1 Arial, sans-serif; padding: 6px 8px; cursor: pointer; }
      .ee-design-actions button:hover { background: #2563eb; color: #ffffff; }
	      .ee-design-edit-hint { position: absolute; z-index: 9; right: 10px; bottom: -16px; border: 1px solid #bbf7d0; border-radius: 999px; background: #f0fdf4; color: #047857; font: 800 10px/1 Arial, sans-serif; padding: 5px 7px; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.1); pointer-events: none; }
	      [data-design-edit-field] { min-height: 1em; outline: 1px dashed transparent; outline-offset: 3px; cursor: text; }
	      [data-design-edit-field]:hover { outline-color: #bfdbfe; background: rgba(37, 99, 235, 0.04); }
	      [data-design-edit-field]:focus { outline-color: #2563eb; background: rgba(37, 99, 235, 0.08); }
      .ee-image-edit-wrap, .ee-button-edit-wrap, .ee-spacing-edit-wrap, .ee-table-edit-wrap, .ee-footer-edit-wrap { display: grid; gap: 8px; }
      .ee-image-edit-panel, .ee-field-edit-panel, .ee-section-edit-panel, .ee-table-edit-panel { display: grid; gap: 6px; border: 1px solid #bfdbfe; border-radius: 8px; background: #eff6ff; padding: 8px; }
      .ee-section-edit-panel { grid-template-columns: minmax(0, 1fr) 96px; margin-bottom: 8px; }
      .ee-image-edit-panel label, .ee-field-edit-panel label, .ee-section-edit-panel label, .ee-table-edit-panel label { display: grid; gap: 4px; color: #1d4ed8; font: 800 10px/1.2 Arial, sans-serif; text-transform: uppercase; }
      .ee-image-edit-panel input, .ee-field-edit-panel input, .ee-section-edit-panel input, .ee-table-edit-panel input { min-width: 0; border: 1px solid #bfdbfe; border-radius: 6px; color: #0f172a; font: 12px/1.3 Arial, sans-serif; padding: 7px 8px; }
	      [data-design-section-body].ee-section-drop-target { outline: 2px dashed #10b981; outline-offset: 4px; background: rgba(16, 185, 129, 0.06); }
      .ee-section-empty { border: 1px dashed #93c5fd; border-radius: 6px; color: #64748b; font: 700 12px/1.4 Arial, sans-serif; padding: 14px; text-align: center; }
      .ee-design-mobile-note { display: inline-block; margin: 0 0 8px; border: 1px solid #cbd5e1; border-radius: 999px; background: #f8fafc; color: #475569; font: 800 10px/1 Arial, sans-serif; padding: 5px 7px; }
      @media (max-width: 520px) {
        [data-mobile-stack="stack"] { display: block !important; }
        [data-mobile-stack="reverse"] { display: flex !important; flex-direction: column-reverse; }
        [data-mobile-stack="stack"] > .ee-design-block,
        [data-mobile-stack="reverse"] > .ee-design-block { margin-bottom: 10px; }
      }
      ${cssBody || ''}
    </style>
  </head>
  <body>
    <div class="email-container" data-design-drop-root="true">
${bodyHtml.split('\n').map((line) => `      ${line}`).join('\n')}
	    </div>
	    <script>
		      var editOriginalValues = new WeakMap();
			      function editableValue(editable) {
			        return editable.innerText || editable.textContent || '';
			      }
		      function originalEditableValue(editable) {
		        if (editOriginalValues.has(editable)) return editOriginalValues.get(editable) || '';
		        return editable.getAttribute('data-design-original-value') || '';
		      }
		      function commitEditable(editable) {
		        var block = editable && editable.closest ? editable.closest('[data-design-block-id]') : null;
		        if (!block) return;
		        parent.postMessage({
		          type: 'ee-design-block-edit',
		          blockId: block.getAttribute('data-design-block-id'),
		          field: editable.getAttribute('data-design-edit-field') || 'text',
		          index: editable.getAttribute('data-design-edit-index') || '',
		          value: editableValue(editable)
		        }, '*');
		      }
		      document.addEventListener('click', function(event) {
		        var block = event.target && event.target.closest ? event.target.closest('[data-design-block-id]') : null;
		        if (!block) return;
	        if (event.target.closest('[data-design-edit-field]')) {
	          parent.postMessage({ type: 'ee-design-block-select', blockId: block.getAttribute('data-design-block-id'), action: 'select' }, '*');
	          return;
	        }
	        event.preventDefault();
	        event.stopPropagation();
	        var action = event.target && event.target.getAttribute ? event.target.getAttribute('data-design-action') : '';
	        parent.postMessage({ type: 'ee-design-block-select', blockId: block.getAttribute('data-design-block-id'), action: action || 'select' }, '*');
	      });
		      document.addEventListener('blur', function(event) {
		        var editable = event.target && event.target.closest ? event.target.closest('[data-design-edit-field]') : null;
		        if (!editable) return;
		        commitEditable(editable);
		      }, true);
      document.addEventListener('change', function(event) {
        var input = event.target && event.target.closest ? event.target.closest('[data-design-image-field]') : null;
        if (!input) input = event.target && event.target.closest ? event.target.closest('[data-design-block-field]') : null;
        if (!input) return;
        var block = input.closest('[data-design-block-id]');
        if (!block) return;
        parent.postMessage({
          type: input.hasAttribute('data-design-image-field') ? 'ee-design-block-image-edit' : 'ee-design-block-field-edit',
          blockId: block.getAttribute('data-design-block-id'),
          field: input.getAttribute('data-design-image-field') || input.getAttribute('data-design-block-field') || '',
          value: input.value || ''
        }, '*');
      });
		      document.addEventListener('focus', function(event) {
		        var editable = event.target && event.target.closest ? event.target.closest('[data-design-edit-field]') : null;
		        if (!editable) return;
		        var block = editable.closest('[data-design-block-id]');
		        if (!block) return;
		        editOriginalValues.set(editable, editableValue(editable));
		        parent.postMessage({
		          type: 'ee-design-block-edit-focus',
		          blockId: block.getAttribute('data-design-block-id')
		        }, '*');
		      }, true);
		      document.addEventListener('keydown', function(event) {
		        var editable = event.target && event.target.closest ? event.target.closest('[data-design-edit-field]') : null;
		        if (!editable) return;
			        if (event.key === 'Escape') {
			          event.preventDefault();
			          editable.textContent = originalEditableValue(editable);
			          editable.blur();
			          parent.postMessage({ type: 'ee-design-block-edit-cancel' }, '*');
		          return;
		        }
		        if (event.key === 'Enter' && !event.shiftKey) {
		          event.preventDefault();
		          commitEditable(editable);
		          editable.blur();
		        }
		      });
		      document.addEventListener('dragstart', function(event) {
	        var block = event.target && event.target.closest ? event.target.closest('[data-design-block-id]') : null;
	        if (!block || event.target.closest('.ee-design-actions') || event.target.closest('[data-design-edit-field]')) return;
	        event.dataTransfer.effectAllowed = 'move';
	        event.dataTransfer.setData('text/plain', block.getAttribute('data-design-block-id') || '');
	      });
	      document.addEventListener('dragover', function(event) {
	        var block = event.target && event.target.closest ? event.target.closest('[data-design-block-id]') : null;
	        var sectionBody = event.target && event.target.closest ? event.target.closest('[data-design-section-body]') : null;
	        var root = event.target && event.target.closest ? event.target.closest('[data-design-drop-root]') : null;
	        if (!block && !root) return;
	        event.preventDefault();
	        var nestedBlock = sectionBody && block && sectionBody.getAttribute('data-design-section-body') !== block.getAttribute('data-design-block-id');
	        if (sectionBody && !nestedBlock) {
	          block.classList.remove('ee-drop-target-before', 'ee-drop-target-after');
	          sectionBody.classList.add('ee-section-drop-target');
	        }
	        else if (block) {
	          var rect = block.getBoundingClientRect();
	          var position = event.clientY > rect.top + rect.height / 2 ? 'after' : 'before';
	          block.classList.remove('ee-drop-target-before', 'ee-drop-target-after');
          block.classList.add(position === 'after' ? 'ee-drop-target-after' : 'ee-drop-target-before');
        }
        else if (root) root.classList.add('ee-root-drop-target');
      });
	      document.addEventListener('dragleave', function(event) {
	        var block = event.target && event.target.closest ? event.target.closest('[data-design-block-id]') : null;
	        var sectionBody = event.target && event.target.closest ? event.target.closest('[data-design-section-body]') : null;
	        var root = event.target && event.target.closest ? event.target.closest('[data-design-drop-root]') : null;
	        if (block) block.classList.remove('ee-drop-target-before', 'ee-drop-target-after');
	        if (sectionBody && !sectionBody.contains(event.relatedTarget)) sectionBody.classList.remove('ee-section-drop-target');
	        if (root && !root.contains(event.relatedTarget)) root.classList.remove('ee-root-drop-target');
	      });
	      document.addEventListener('drop', function(event) {
	        var block = event.target && event.target.closest ? event.target.closest('[data-design-block-id]') : null;
	        var sectionBody = event.target && event.target.closest ? event.target.closest('[data-design-section-body]') : null;
	        var root = event.target && event.target.closest ? event.target.closest('[data-design-drop-root]') : null;
	        if (!block && !root) return;
	        event.preventDefault();
	        var position = 'after';
	        var nestedBlock = sectionBody && block && sectionBody.getAttribute('data-design-section-body') !== block.getAttribute('data-design-block-id');
	        var childTargetId = sectionBody && !nestedBlock ? sectionBody.getAttribute('data-design-section-body') : '';
	        if (block) {
	          var rect = block.getBoundingClientRect();
	          position = event.clientY > rect.top + rect.height / 2 ? 'after' : 'before';
	          block.classList.remove('ee-drop-target-before', 'ee-drop-target-after');
	        }
	        if (sectionBody) sectionBody.classList.remove('ee-section-drop-target');
	        if (root) root.classList.remove('ee-root-drop-target');
	        var source = event.dataTransfer.getData('text/plain') || '';
	        if (childTargetId) {
	          if (source.indexOf('new:') === 0) {
	            parent.postMessage({
	              type: 'ee-design-block-child-insert',
	              blockType: source.slice(4),
	              parentBlockId: childTargetId
	            }, '*');
	            return;
	          }
	          parent.postMessage({
	            type: 'ee-design-block-child-reorder',
	            sourceBlockId: source,
	            parentBlockId: childTargetId
	          }, '*');
	          return;
	        }
	        if (source.indexOf('new:') === 0) {
	          parent.postMessage({
            type: 'ee-design-block-insert',
            blockType: source.slice(4),
            targetBlockId: block ? block.getAttribute('data-design-block-id') : '',
            position: position
          }, '*');
          return;
        }
        parent.postMessage({
          type: 'ee-design-block-reorder',
          sourceBlockId: source,
          targetBlockId: block ? block.getAttribute('data-design-block-id') : '',
          position: position
        }, '*');
      });
    </script>
  </body>
</html>`;
  }

  function updateDesignBlock(id: string, updates: Partial<TemplateDesignBlock>) {
    rememberDesignState();
    const updateBlocks = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === id) return { ...block, ...updates };
      if (block.children?.length) return { ...block, children: updateBlocks(block.children) };
      return block;
    });
    setDesignDoc((current) => ({
      blocks: updateBlocks(current.blocks),
    }));
    setDesignDocEdited(true);
    markPreviewStale();
  }

  function addDesignBlock(type: string, targetId = '', position: 'before' | 'after' = 'before') {
    rememberDesignState();
    const block = newDesignBlock(type);
    let inserted = false;
    const insertBlock = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => {
      const targetIndex = blocks.findIndex((item) => item.id === targetId);
      if (targetIndex >= 0) {
        const nextBlocks = [...blocks];
        nextBlocks.splice(position === 'after' ? targetIndex + 1 : targetIndex, 0, block);
        inserted = true;
        return nextBlocks;
      }
      return blocks.map((item) => item.children?.length ? { ...item, children: insertBlock(item.children) } : item);
    };
    setDesignDoc((current) => {
      if (!targetId) return { blocks: [...current.blocks, block] };
      const blocks = insertBlock(current.blocks);
      return { blocks: inserted ? blocks : [...current.blocks, block] };
    });
    selectDesignBlock(block.id, targetId ? designBlockAncestorIds(targetId) : undefined);
    setEditorMode('design');
    setDesignDocEdited(true);
    markPreviewStale();
    setStatus(`Added ${type.replace('_', ' ')} block${targetId ? ' at drop point' : ''}.`);
  }

  function addDesignChildBlock(parentId: string, type: string) {
    rememberDesignState();
    const child = newDesignBlock(type);
    const appendChild = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === parentId) {
        return { ...block, children: [...(block.children || []), child] };
      }
      if (block.children?.length) return { ...block, children: appendChild(block.children) };
      return block;
    });
    setDesignDoc((current) => ({ blocks: appendChild(current.blocks) }));
    selectDesignBlock(child.id, [parentId]);
    setEditorMode('design');
    setDesignDocEdited(true);
    markPreviewStale();
    setStatus(`Added ${designBlockTypeLabel(type)} inside container.`);
  }

  function addDesignColumn(parentId: string) {
    rememberDesignState();
    const column = { ...newDesignBlock('section'), className: 'email-column', padding_y: 14, children: [newDesignBlock('paragraph')] };
    const appendColumn = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === parentId && block.type === 'columns') {
        return { ...block, children: [...(block.children || []), column] };
      }
      if (block.children?.length) return { ...block, children: appendColumn(block.children) };
      return block;
    });
    setDesignDoc((current) => ({ blocks: appendColumn(current.blocks) }));
    selectDesignBlock(column.id, [parentId]);
    setEditorMode('design');
    setDesignDocEdited(true);
    markPreviewStale();
    setStatus('Added column.');
  }

  function moveDesignColumn(parentId: string, columnId: string, direction: -1 | 1) {
    moveDesignBlock(columnId, direction);
    selectDesignBlock(parentId);
    setStatus(direction < 0 ? 'Moved column left.' : 'Moved column right.');
  }

  function duplicateDesignColumn(parentId: string, columnId: string) {
    rememberDesignState();
    let duplicated = false;
    const duplicateColumn = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === parentId && block.type === 'columns') {
        const children = block.children || [];
        const index = children.findIndex((child) => child.id === columnId);
        if (index < 0) return block;
        const duplicate = cloneDesignBlock(children[index]);
        duplicated = true;
        const nextChildren = [...children];
        nextChildren.splice(index + 1, 0, duplicate);
        return { ...block, children: nextChildren };
      }
      if (block.children?.length) return { ...block, children: duplicateColumn(block.children) };
      return block;
    });
    setDesignDoc((current) => {
      const blocks = duplicateColumn(current.blocks);
      return duplicated ? { blocks } : current;
    });
    if (duplicated) {
      selectDesignBlock(parentId);
      setDesignDocEdited(true);
      markPreviewStale();
      setStatus('Duplicated column.');
    }
  }

  function removeLastDesignColumn(parentId: string) {
    rememberDesignState();
    let removed = false;
    const removeColumn = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === parentId && block.type === 'columns') {
        const children = block.children || [];
        if (children.length <= 1) return block;
        removed = true;
        return { ...block, children: children.slice(0, -1) };
      }
      if (block.children?.length) return { ...block, children: removeColumn(block.children) };
      return block;
    });
    setDesignDoc((current) => {
      const blocks = removeColumn(current.blocks);
      return removed ? { blocks } : current;
    });
    selectDesignBlock(parentId);
    setEditorMode('design');
    if (removed) {
      setDesignDocEdited(true);
      markPreviewStale();
      setStatus('Removed last column.');
    } else {
      setStatus('Columns need at least one column.');
    }
  }

  function moveDesignBlockIntoSection(sourceId: string, parentId: string) {
    if (!sourceId || !parentId || sourceId === parentId) return;
    const sourceBlock = flatDesignBlocks.find((block) => block.id === sourceId);
    const blockContains = (block: TemplateDesignBlock, id: string): boolean => block.id === id || Boolean(block.children?.some((child) => blockContains(child, id)));
    if (sourceBlock && blockContains(sourceBlock, parentId)) return;
    rememberDesignState();
    setDesignDoc((current) => {
      let movedBlock: TemplateDesignBlock | null = null;
      const removeBlock = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks
        .filter((block) => {
          if (block.id !== sourceId) return true;
          movedBlock = block;
          return false;
        })
        .map((block) => block.children?.length ? { ...block, children: removeBlock(block.children) } : block);
      const appendToSection = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
        if (block.id === parentId && isDesignContainerBlock(block) && movedBlock) {
          return { ...block, children: [...(block.children || []), movedBlock] };
        }
        if (block.children?.length) return { ...block, children: appendToSection(block.children) };
        return block;
      });
      const withoutSource = removeBlock(current.blocks);
      if (!movedBlock) return current;
      return { blocks: appendToSection(withoutSource) };
    });
    selectDesignBlock(sourceId, [parentId]);
    setDesignDocEdited(true);
    markPreviewStale();
    setStatus('Moved block into container.');
  }

  function indentDesignBlock(id: string) {
    const siblingContext = designBlockSiblingContext(id);
    const targetSection = siblingContext && siblingContext.index > 0 ? siblingContext.blocks[siblingContext.index - 1] : null;
    if (!targetSection || !isDesignContainerBlock(targetSection)) return;
    moveDesignBlockIntoSection(id, targetSection.id);
    setStatus('Indented block into previous container.');
  }

  function outdentDesignBlock(id: string) {
    const parent = findDesignBlockParent(id);
    if (!parent) return;
    reorderDesignBlock(id, parent.id, 'after');
    setStatus('Outdented block one level.');
  }

  function wrapDesignBlockInSection(id: string) {
    rememberDesignState();
    let sectionId = '';
    const wrapBlock = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((block) => {
      if (block.id === id) {
        sectionId = designBlockId();
        return {
          id: sectionId,
          type: 'section',
          className: 'email-section',
          bg: '',
          padding_y: 18,
          children: [block],
        };
      }
      if (block.children?.length) return { ...block, children: wrapBlock(block.children) };
      return block;
    });
    setDesignDoc((current) => {
      const blocks = wrapBlock(current.blocks);
      return sectionId ? { blocks } : current;
    });
    if (sectionId) {
      selectDesignBlock(sectionId, designBlockAncestorIds(id));
      setDesignDocEdited(true);
      markPreviewStale();
      setStatus('Wrapped block in a section.');
    }
  }

  function moveDesignBlock(id: string, direction: -1 | 1) {
    rememberDesignState();
    let moved = false;
    const moveInBlocks = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => {
      const index = blocks.findIndex((block) => block.id === id);
      if (index >= 0) {
        const nextIndex = index + direction;
        if (nextIndex < 0 || nextIndex >= blocks.length) return blocks;
        const nextBlocks = [...blocks];
        [nextBlocks[index], nextBlocks[nextIndex]] = [nextBlocks[nextIndex], nextBlocks[index]];
        moved = true;
        return nextBlocks;
      }
      return blocks.map((block) => block.children?.length ? { ...block, children: moveInBlocks(block.children) } : block);
    };
    setDesignDoc((current) => {
      const blocks = moveInBlocks(current.blocks);
      return moved ? { blocks } : current;
    });
    if (moved) {
      setDesignDocEdited(true);
      markPreviewStale();
    }
  }

  function duplicateDesignBlock(id: string) {
    rememberDesignState();
    let duplicateId = '';
    const duplicateInBlocks = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => {
      const index = blocks.findIndex((block) => block.id === id);
      if (index >= 0) {
        const duplicatedBlock = cloneDesignBlock(blocks[index]);
        duplicateId = duplicatedBlock.id;
        const nextBlocks = [...blocks];
        nextBlocks.splice(index + 1, 0, duplicatedBlock);
        return nextBlocks;
      }
      return blocks.map((block) => block.children?.length ? { ...block, children: duplicateInBlocks(block.children) } : block);
    };
    setDesignDoc((current) => {
      const blocks = duplicateInBlocks(current.blocks);
      return duplicateId ? { blocks } : current;
    });
    if (duplicateId) {
      selectDesignBlock(duplicateId, designBlockAncestorIds(id));
      setDesignDocEdited(true);
      markPreviewStale();
      setStatus('Duplicated design block.');
    }
  }

  function reorderDesignBlock(sourceId: string, targetId: string, position: 'before' | 'after' = 'before') {
    if (!sourceId || sourceId === targetId) return;
    rememberDesignState();
    const blockContains = (block: TemplateDesignBlock, id: string): boolean => block.id === id || Boolean(block.children?.some((child) => blockContains(child, id)));
    setDesignDoc((current) => {
      let movedBlock: TemplateDesignBlock | null = null;
      let removed = false;
      let inserted = false;
      const removeBlock = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks
        .filter((block) => {
          if (block.id !== sourceId) return true;
          movedBlock = block;
          removed = true;
          return false;
        })
        .map((block) => block.children?.length ? { ...block, children: removeBlock(block.children) } : block);
      const insertBlock = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => {
        if (!movedBlock) return blocks;
        const targetIndex = blocks.findIndex((block) => block.id === targetId);
        if (targetIndex >= 0) {
          const nextBlocks = [...blocks];
          nextBlocks.splice(position === 'after' ? targetIndex + 1 : targetIndex, 0, movedBlock);
          inserted = true;
          return nextBlocks;
        }
        return blocks.map((block) => block.children?.length ? { ...block, children: insertBlock(block.children) } : block);
      };
      const sourceBlock = flatDesignBlocks.find((block) => block.id === sourceId);
      if (sourceBlock && targetId && blockContains(sourceBlock, targetId)) return current;
      const withoutSource = removeBlock(current.blocks);
      if (!removed || !movedBlock) return current;
      if (!targetId) return { blocks: [...withoutSource, movedBlock] };
      const blocks = insertBlock(withoutSource);
      return inserted ? { blocks } : current;
    });
    selectDesignBlock(sourceId, targetId ? designBlockAncestorIds(targetId) : designBlockAncestorIds(sourceId));
    setDesignDocEdited(true);
    markPreviewStale();
  }

  function removeDesignBlock(id: string) {
    rememberDesignState();
    const removeBlocks = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks
      .filter((block) => block.id !== id)
      .map((block) => block.children?.length ? { ...block, children: removeBlocks(block.children) } : block);
    setDesignDoc((current) => ({ blocks: removeBlocks(current.blocks) }));
    setSelectedDesignBlockId((current) => current === id ? '' : current);
    setDesignDocEdited(true);
    markPreviewStale();
  }

  function syncDesignToCode() {
    const nextHtml = designDocumentTemplateSource();
    setHtmlBody(nextHtml);
    setDesignDocEdited(false);
    markPreviewStale();
    setStatus(`Synced ${formatInt(designDoc.blocks.length)} design block(s) to HTML/Jinja.`);
  }

  function switchTemplateEditorMode(nextMode: 'edit' | 'design') {
    if (nextMode === 'design' && editorMode !== 'design' && (editorMode !== 'preview' || previewSourceMode !== 'design')) {
      if (!designDoc.blocks.length || htmlBody !== savedTemplateSnapshot.htmlBody) {
        setDesignDoc(htmlToDesignDocument(htmlBody));
      }
      setDesignDocEdited(false);
      setDesignUndoStack([]);
      setDesignRedoStack([]);
    }
    if (nextMode === 'edit' && editorMode === 'design') {
      if (designDocEdited) setHtmlBody(designDocumentTemplateSource());
      setDesignDocEdited(false);
    }
    setEditorMode(nextMode);
  }

  useEffect(() => {
    function handleDesignKeyboardShortcut(event: KeyboardEvent) {
      if (editorMode !== 'design' || busy) return;
      if (!(event.metaKey || event.ctrlKey)) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable="true"], .cm-editor')) return;
      const key = event.key.toLowerCase();
      if (key === 'z' && !event.shiftKey && designUndoStack.length) {
        event.preventDefault();
        undoDesignChange();
      }
      if ((key === 'z' && event.shiftKey || key === 'y') && designRedoStack.length) {
        event.preventDefault();
        redoDesignChange();
      }
    }
    window.addEventListener('keydown', handleDesignKeyboardShortcut);
    return () => window.removeEventListener('keydown', handleDesignKeyboardShortcut);
  }, [busy, designRedoStack, designUndoStack, editorMode, designDoc]);

  useEffect(() => {
    if (!designInspectorFocusNonce) return;
    const panel = designInspectorRef.current;
    const firstEditableField = panel?.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(
      'input:not([readonly]), textarea, select',
    );
    panel?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    window.setTimeout(() => firstEditableField?.focus(), 0);
    const highlightTimer = window.setTimeout(() => setDesignInspectorFocusNonce(0), 1400);
    return () => window.clearTimeout(highlightTimer);
  }, [designInspectorFocusNonce, selectedDesignBlockId]);

  useEffect(() => {
    if (editorMode !== 'design' || !designHierarchyOpen || !selectedDesignBlockId) return;
    const scrollTimer = window.setTimeout(() => {
      const selector = `[data-design-tree-id="${CSS.escape(selectedDesignBlockId)}"]`;
      const selectedRow = designHierarchyRef.current?.querySelector<HTMLElement>(selector);
      selectedRow?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }, 0);
    return () => window.clearTimeout(scrollTimer);
  }, [collapsedDesignTreeIds, designHierarchyOpen, editorMode, selectedDesignBlockId]);

  useEffect(() => {
    function handleDesignCanvasMessage(event: MessageEvent) {
      const data = event.data;
      if (data?.type === 'ee-design-block-reorder') {
        reorderDesignBlock(String(data.sourceBlockId || ''), String(data.targetBlockId || ''), data.position === 'after' ? 'after' : 'before');
        setStatus('Reordered design blocks from the canvas.');
        return;
      }
      if (data?.type === 'ee-design-block-insert') {
        addDesignBlock(String(data.blockType || 'paragraph'), String(data.targetBlockId || ''), data.position === 'after' ? 'after' : 'before');
        return;
      }
      if (data?.type === 'ee-design-block-child-insert') {
        addDesignChildBlock(String(data.parentBlockId || ''), String(data.blockType || 'paragraph'));
        return;
      }
      if (data?.type === 'ee-design-block-child-reorder') {
        moveDesignBlockIntoSection(String(data.sourceBlockId || ''), String(data.parentBlockId || ''));
        return;
      }
      if (data?.type === 'ee-design-block-edit' && typeof data.blockId === 'string') {
        const nextValue = String(data.value || '').trim();
        const block = flattenDesignBlocks(designDoc.blocks).find((item) => item.id === data.blockId);
        if (!block) return;
        if (data.field === 'item') {
          const itemIndex = Number(data.index);
          if (!Number.isInteger(itemIndex) || itemIndex < 0 || itemIndex >= (block.items || []).length) return;
          if ((block.items || [])[itemIndex] === nextValue) return;
          const nextItems = [...(block.items || [])];
          nextItems[itemIndex] = nextValue;
          updateDesignBlock(block.id, { items: nextItems });
          setStatus(`Updated list item ${itemIndex + 1} from the canvas.`);
          return;
        }
        if (block.text === nextValue) return;
        updateDesignBlock(block.id, { text: nextValue });
        setStatus(`Updated ${block.type.replace('_', ' ')} text from the canvas.`);
        return;
      }
      if (data?.type === 'ee-design-block-image-edit' && typeof data.blockId === 'string') {
        const field = data.field === 'alt' ? 'alt' : data.field === 'src' ? 'src' : '';
        if (!field) return;
        const nextValue = String(data.value || '').trim();
        updateDesignBlock(data.blockId, { [field]: nextValue });
        setStatus(`Updated image ${field === 'src' ? 'URL' : 'alt text'} from the canvas.`);
        return;
      }
      if (data?.type === 'ee-design-block-field-edit' && typeof data.blockId === 'string') {
        const field = data.field === 'href' ? 'href'
          : data.field === 'bg' ? 'bg'
            : data.field === 'padding_y' ? 'padding_y'
              : data.field === 'padding_x' ? 'padding_x'
                : data.field === 'height' ? 'height'
                  : data.field === 'gap' ? 'gap'
                    : data.field === 'color' ? 'color'
                      : '';
        if (!field) return;
        const nextValue = ['padding_y', 'padding_x', 'height', 'gap'].includes(field) ? Number(data.value || 0) : String(data.value || '').trim();
        updateDesignBlock(data.blockId, { [field]: nextValue });
        const fieldLabel = field === 'href' ? 'button URL'
          : field === 'bg' ? 'section background'
            : field === 'padding_y' ? 'vertical padding'
              : field === 'padding_x' ? 'horizontal padding'
                : field === 'height' ? 'spacer height'
                  : field === 'gap' ? 'column gap'
                    : 'color';
        setStatus(`Updated ${fieldLabel} from the canvas.`);
        return;
      }
      if (data?.type === 'ee-design-block-edit-focus' && typeof data.blockId === 'string') {
        const block = flattenDesignBlocks(designDoc.blocks).find((item) => item.id === data.blockId);
        if (!block) return;
        selectDesignBlock(block.id);
        setStatus(`Editing ${block.type === 'list' ? 'list item' : block.type.replace('_', ' ')} text on the canvas. Press Enter to commit, Escape to cancel, or click outside to capture changes.`);
        return;
      }
      if (data?.type === 'ee-design-block-edit-cancel') {
        setStatus('Canceled canvas text edit.');
        return;
      }
      if (!data || data.type !== 'ee-design-block-select' || typeof data.blockId !== 'string') return;
      const block = flattenDesignBlocks(designDoc.blocks).find((item) => item.id === data.blockId);
      if (!block) return;
      selectDesignBlock(block.id);
      if (data.action === 'style') {
        focusDesignBlockCss(block);
        return;
      }
      if (data.action === 'edit') {
        setDesignInspectorFocusNonce((current) => current + 1);
        setStatus(`Editing ${block.type.replace('_', ' ')} block in the inspector.`);
        return;
      }
      if (data.action === 'up') {
        moveDesignBlock(block.id, -1);
        setStatus(`Moved ${block.type.replace('_', ' ')} block up from canvas.`);
        return;
      }
      if (data.action === 'down') {
        moveDesignBlock(block.id, 1);
        setStatus(`Moved ${block.type.replace('_', ' ')} block down from canvas.`);
        return;
      }
      if (data.action === 'indent') {
        if (canIndentDesignBlock(block.id)) {
          indentDesignBlock(block.id);
        } else {
          setStatus('Select a block below a container to indent it.');
        }
        return;
      }
      if (data.action === 'parent') {
        const parent = findDesignBlockParent(block.id);
        if (parent) {
          selectDesignBlock(parent.id);
          setStatus(`Selected parent ${parent.type.replace('_', ' ')} block from canvas.`);
        }
        return;
      }
      if (data.action === 'outdent') {
        outdentDesignBlock(block.id);
        return;
      }
      if (data.action === 'root') {
        reorderDesignBlock(block.id, '');
        setStatus('Moved block to root from canvas.');
        return;
      }
      if (data.action === 'wrap') {
        wrapDesignBlockInSection(block.id);
        return;
      }
      if (data.action === 'duplicate') {
        duplicateDesignBlock(block.id);
        return;
      }
      if (data.action === 'delete') {
        removeDesignBlock(block.id);
        setStatus(`Deleted ${block.type.replace('_', ' ')} block from canvas.`);
        return;
      }
      setStatus(`Selected ${block.type.replace('_', ' ')} block from canvas.`);
    }
    window.addEventListener('message', handleDesignCanvasMessage);
    return () => window.removeEventListener('message', handleDesignCanvasMessage);
  }, [designDoc.blocks]);

  useEffect(() => {
    let cancelled = false;
    async function syncRouteTemplate() {
      if (routeTemplateId && selectedTemplateId !== routeTemplateId) {
        const template = templates.find((item) => item.id === routeTemplateId);
        if (template) {
          if (!await openTemplateInEditor(template)) {
            window.location.hash = selectedTemplateId ? `#templates/${selectedTemplateId}` : '#templates';
          }
          return;
        }
        if (!confirmDiscardTemplateChanges(`open template ${routeTemplateId}`)) {
          window.location.hash = selectedTemplateId ? `#templates/${selectedTemplateId}` : '#templates';
          return;
        }
        setBusy(true);
        setStatus('Loading template details...');
        try {
          const fetchedTemplate = await fetchJson<TemplateRead>(`/api/v1/templates/${routeTemplateId}`);
          const fetchedDesignDoc = await designDocForTemplate(fetchedTemplate);
          if (!cancelled) loadTemplateIntoEditor(fetchedTemplate, { force: true, designDoc: fetchedDesignDoc });
        } catch (error) {
          if (!cancelled) {
            setStatus(`Unable to load template: ${apiErrorMessage(error)}`);
            window.location.hash = selectedTemplateId ? `#templates/${selectedTemplateId}` : '#templates';
          }
        } finally {
          if (!cancelled) setBusy(false);
        }
      }
      if (isNewTemplate && selectedTemplateId) {
        if (!resetTemplateEditor()) {
          window.location.hash = `#templates/${selectedTemplateId}`;
        }
      }
    }
    syncRouteTemplate();
    return () => { cancelled = true; };
  }, [isNewTemplate, routeTemplateId, selectedTemplateId, templates]);

  function clearTemplatePreview() {
    setPreviewHtml('');
    setPreviewSubject('');
    setPreviewFreshness('empty');
  }

  function confirmDiscardTemplateChanges(nextAction: string) {
    if (!hasUnsavedTemplateChanges) return true;
    const confirmed = window.confirm(`Discard unsaved template changes and ${nextAction}?`);
    if (!confirmed) {
      setStatus('Kept unsaved template changes. Save or revert before switching context.');
    }
    return confirmed;
  }

  function clearTemplateLocalDraft(templateId = selectedTemplateId) {
    window.localStorage.removeItem(templateDraftStorageKey(templateId));
    setLocalTemplateDraft(null);
  }

  function readTemplateLocalDraft(templateId = selectedTemplateId): TemplateLocalDraft | null {
    try {
      const raw = window.localStorage.getItem(templateDraftStorageKey(templateId));
      if (!raw) return null;
      const draft = JSON.parse(raw) as TemplateLocalDraft;
      if (!draft || typeof draft.updatedAt !== 'number') return null;
      if (!draft.designDoc || !Array.isArray(draft.designDoc.blocks)) return null;
      return draft;
    } catch {
      return null;
    }
  }

  function restoreTemplateLocalDraft() {
    if (!localTemplateDraft) return;
    const nextDesignDoc = cloneDesignDocument(localTemplateDraft.designDoc);
    setName(localTemplateDraft.name);
    setSubject(localTemplateDraft.subject);
    setHtmlBody(localTemplateDraft.htmlBody);
    setCssBody(localTemplateDraft.cssBody);
    setDesignDoc(nextDesignDoc);
    setSelectedDesignBlockId(nextDesignDoc.blocks[0]?.id || '');
    setDesignDocEdited(true);
    setEditorMode(localTemplateDraft.editorMode);
    setPreviewSourceMode(localTemplateDraft.editorMode === 'design' ? 'design' : 'edit');
    markPreviewStale();
    setStatus('Restored local autosave draft. Save changes to persist it.');
  }

  function resetTemplateEditor(options: { force?: boolean } = {}) {
    if (!options.force && !confirmDiscardTemplateChanges('start a new template')) return false;
    clearTemplateLocalDraft(selectedTemplateId);
    setSelectedTemplateId('');
    setName(defaultTemplateSnapshot.name);
    setSubject(defaultTemplateSnapshot.subject);
    setHtmlBody(defaultTemplateSnapshot.htmlBody);
    setCssBody(defaultTemplateSnapshot.cssBody);
    setDesignDoc({ blocks: [] });
    setDesignDocEdited(false);
    setDesignUndoStack([]);
    setDesignRedoStack([]);
    setSelectedDesignBlockId('');
    setSavedTemplateSnapshot(defaultTemplateSnapshot);
    setVariablesJson('{\n  "first_name": "David",\n  "plan": "trial",\n  "recommendations": ["Welcome email", "Product update"]\n}');
    clearTemplatePreview();
    setVariables([]);
    setAiRecommendations([]);
    setAiNotes([]);
    setPendingAiDraft(null);
    setAppliedAiDraftLabel('');
    setEditorMode('edit');
    setPreviewSourceMode('edit');
    setTemplateVersions([]);
    setSelectedVersionReviewId('');
    setStatus('Ready to create a new template.');
    return true;
  }

  function loadTemplateIntoEditor(
    template: TemplateRead,
    options: { force?: boolean; designDoc?: TemplateDesignDocument } = {},
  ) {
    if (template.id !== selectedTemplateId && !options.force && !confirmDiscardTemplateChanges(`open "${template.name}"`)) return false;
    const nextDesignDoc = options.designDoc || designDocFromTemplate(template);
    const snapshot = {
      name: template.name,
      subject: template.subject,
      htmlBody: template.html_body || '',
      cssBody: template.css_body || '',
      designDocJson: semanticDesignDocJson(nextDesignDoc),
    };
    setSelectedTemplateId(template.id);
    setName(snapshot.name);
    setSubject(snapshot.subject);
    setHtmlBody(snapshot.htmlBody);
    setCssBody(snapshot.cssBody);
    setDesignDoc(nextDesignDoc);
    setDesignDocEdited(false);
    setDesignUndoStack([]);
    setDesignRedoStack([]);
    setSelectedDesignBlockId(nextDesignDoc.blocks[0]?.id || '');
    setSavedTemplateSnapshot(snapshot);
    setLocalTemplateDraft(readTemplateLocalDraft(template.id));
    clearTemplatePreview();
    setAiRecommendations([]);
    setAiNotes([]);
    setPendingAiDraft(null);
    setAppliedAiDraftLabel('');
    setSelectedVersionReviewId('');
    setEditorMode('edit');
    setPreviewSourceMode('edit');
    void loadTemplateVersions(template.id);
    setStatus(`Loaded template: ${template.name}`);
    return true;
  }

  async function openTemplateInEditor(template: TemplateRead, options: { force?: boolean } = {}) {
    if (template.id !== selectedTemplateId && !options.force && !confirmDiscardTemplateChanges(`open "${template.name}"`)) return false;
    setBusy(true);
    setStatus('Loading template design document...');
    try {
      const nextDesignDoc = await designDocForTemplate(template);
      return loadTemplateIntoEditor(template, { force: true, designDoc: nextDesignDoc });
    } catch (error) {
      setStatus(`Unable to load template design document: ${apiErrorMessage(error)}`);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function applyAiDraft(draft: AITemplateDraft) {
    await runTemplateOperation('Applying AI draft', async () => {
      const nextSubject = draft.subject || subject;
      const nextHtml = draft.html_body || htmlBody;
      const nextCss = draft.css_body ?? cssBody;
      const currentVariables = parsedVariables();
      const nextVariables = draft.sample_variables && Object.keys(draft.sample_variables).length
        ? { ...currentVariables, ...draft.sample_variables }
        : currentVariables;
      const variableData = await fetchJson<{ variables: TemplateVariable[]; sample_variables: Record<string, unknown>; errors: string[] }>('/api/v1/templates/variables', {
        method: 'POST',
        body: JSON.stringify({
          subject: nextSubject,
          html_body: nextHtml,
          css_body: nextCss || null,
          variables: nextVariables,
        }),
      });
      const renderVariables = variableData.sample_variables && Object.keys(variableData.sample_variables).length
        ? { ...variableData.sample_variables, ...nextVariables }
        : nextVariables;
      const preview = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject: nextSubject,
          html_body: nextHtml,
          css_body: nextCss || null,
          variables: renderVariables,
        }),
      });
      setSubject(nextSubject);
      setHtmlBody(nextHtml);
      setCssBody(nextCss);
      setDesignDoc(htmlToDesignDocument(nextHtml));
      setDesignDocEdited(false);
      setDesignUndoStack([]);
      setDesignRedoStack([]);
      setVariables(variableData.variables || []);
      setVariablesJson(JSON.stringify(renderVariables, null, 2));
      setPreviewHtml(preview.html_body || '');
      setPreviewSubject(preview.subject || nextSubject);
      setPreviewFreshness('current');
      setAiNotes(draft.change_summary || draft.notes || []);
      setPendingAiDraft(null);
      setAppliedAiDraftLabel(`${draft.provider}/${draft.model}`);
      setPreviewSourceMode('edit');
      setEditorMode('preview');
      const issueText = preview.errors?.length ? ` ${preview.errors.join('; ')}` : '';
      return `Applied AI draft and refreshed preview: ${preview.subject || nextSubject}.${issueText}`;
    });
  }

  function markPreviewStale() {
    setPreviewFreshness(previewHtml ? 'stale' : 'empty');
  }

  function cssRuleForClass(className: string) {
    if (!className) return '';
    const escaped = className.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = cssBody.match(new RegExp(`\\.${escaped}\\s*\\{([^}]*)\\}`, 'm'));
    return match?.[1] || '';
  }

  const selectedCssRule = cssRuleForClass(selectedCssClass);
  const selectedCssCoverage = cssClassCoverage.find((item) => item.name === selectedCssClass);
  const cssHelperNextAction = selectedCssClass && !selectedCssRule
    ? {
      tone: 'warn',
      title: `Create .${selectedCssClass}`,
      detail: `${selectedCssCoverage?.kind || cssClassKind} rule is missing for the selected class.`,
      actionLabel: 'Create Rule',
      run: applyCssPreset,
    }
    : missingCssClasses.length
      ? {
        tone: 'warn',
        title: 'Create missing CSS',
        detail: `${formatInt(missingCssClasses.length)} detected class rule(s) are missing before final preview.`,
        actionLabel: 'Create Missing Rules',
        run: scaffoldMissingCssClasses,
      }
      : previewFreshness !== 'current'
        ? {
          tone: 'warn',
          title: 'Preview updated styles',
          detail: 'CSS coverage is complete. Render the template to verify layout and variables.',
          actionLabel: 'Preview',
          run: previewTemplate,
        }
        : {
          tone: 'good',
          title: 'CSS ready',
          detail: `${formatInt(cssClassCoverage.length)} detected class rule(s) are covered.`,
          actionLabel: 'Open Preview',
          run: () => setEditorMode('preview'),
        };
  const cssClassKindHelp = {
    container: 'Creates a centered email-safe wrapper with width, margin, padding, and background.',
    section: 'Creates a reusable content band or card with padding, border, background, and radius.',
    button: 'Creates an email-safe CTA link with inline-block layout, accent color, and padding.',
    text: 'Creates text styling with font, color, spacing, and line height.',
    image: 'Creates responsive image styling with width, max-width, height, border, and radius.',
  }[cssClassKind];
  const visibleCssControls = {
    font: cssClassKind !== 'image',
    background: ['container', 'section', 'button'].includes(cssClassKind),
    text: ['container', 'section', 'text'].includes(cssClassKind),
    accent: ['section', 'button', 'image'].includes(cssClassKind),
    width: ['container', 'image'].includes(cssClassKind),
    padding: ['container', 'section', 'button'].includes(cssClassKind),
    radius: cssClassKind !== 'text',
  };
  const cssColorSwatches = ['#ffffff', '#f8fafc', '#f5f7fb', '#111827', '#334155', '#64748b', '#2563eb', '#0f766e', '#10b981', '#f59e0b', '#dc2626', '#7c3aed'];
  const designBackgroundPresets = [
    { name: 'Paper', value: '#ffffff' },
    { name: 'Mist', value: '#f8fafc' },
    { name: 'Blue', value: '#eff6ff' },
    { name: 'Mint', value: '#ecfdf5' },
    { name: 'Lavender', value: '#f5f3ff' },
    { name: 'Warm', value: '#fff7ed' },
    { name: 'Slate', value: '#111827' },
    { name: 'Brand', value: '#2563eb' },
  ];
  function updateCssPresetColor(key: 'background' | 'text' | 'accent', value: string) {
    setCssPreset((current) => ({ ...current, [key]: value }));
  }
  function cssColorControl(label: string, key: 'background' | 'text' | 'accent', visible: boolean) {
    const value = cssPreset[key];
    return (
      <label className={visible ? 'css-color-control' : 'css-control-hidden'}>
        {label}
        <div className="css-color-picker">
          <span className="css-color-preview" style={{ backgroundColor: value }} aria-hidden="true" />
          <input
            aria-label={`${label} hex color`}
            value={value}
            onChange={(event) => updateCssPresetColor(key, event.target.value)}
            onBlur={(event) => updateCssPresetColor(key, normalizeCssColor(event.target.value, value))}
          />
          <input
            aria-label={`${label} color picker`}
            className="native-color-input"
            type="color"
            value={normalizeCssColor(value, '#000000')}
            onChange={(event) => updateCssPresetColor(key, event.target.value)}
          />
        </div>
        <div className="css-color-swatches" aria-label={`${label} color swatches`}>
          {cssColorSwatches.map((swatch) => (
            <button
              aria-label={`Use ${swatch}`}
              className={swatch.toLowerCase() === value.toLowerCase() ? 'selected' : ''}
              key={swatch}
              onClick={() => updateCssPresetColor(key, swatch)}
              style={{ backgroundColor: swatch }}
              title={swatch}
              type="button"
            />
          ))}
        </div>
      </label>
    );
  }
  function cssProperty(rule: string, property: string) {
    const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = rule.match(new RegExp(`${escaped}\\s*:\\s*([^;]+)`, 'i'));
    return match?.[1]?.trim() || '';
  }

  function normalizeCssColor(value: string, fallback: string) {
    return /^#[0-9a-f]{6}$/i.test(value) ? value : fallback;
  }

  function hexToHsl(hex: string) {
    const normalized = normalizeCssColor(hex, '#ffffff').replace('#', '');
    const red = parseInt(normalized.slice(0, 2), 16) / 255;
    const green = parseInt(normalized.slice(2, 4), 16) / 255;
    const blue = parseInt(normalized.slice(4, 6), 16) / 255;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const lightness = (max + min) / 2;
    if (max === min) return { h: 0, s: 0, l: Math.round(lightness * 100) };
    const delta = max - min;
    const saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
    let hue = 0;
    if (max === red) hue = (green - blue) / delta + (green < blue ? 6 : 0);
    else if (max === green) hue = (blue - red) / delta + 2;
    else hue = (red - green) / delta + 4;
    return { h: Math.round(hue * 60), s: Math.round(saturation * 100), l: Math.round(lightness * 100) };
  }

  function hslToHex(hue: number, saturation: number, lightness: number) {
    const normalizedHue = (((hue % 360) + 360) % 360) / 360;
    const normalizedSaturation = Math.max(0, Math.min(100, saturation)) / 100;
    const normalizedLightness = Math.max(0, Math.min(100, lightness)) / 100;
    const hueToRgb = (p: number, q: number, tValue: number) => {
      let t = tValue;
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const channelToHex = (channel: number) => Math.round(channel * 255).toString(16).padStart(2, '0');
    if (normalizedSaturation === 0) {
      const gray = channelToHex(normalizedLightness);
      return `#${gray}${gray}${gray}`;
    }
    const q = normalizedLightness < 0.5
      ? normalizedLightness * (1 + normalizedSaturation)
      : normalizedLightness + normalizedSaturation - normalizedLightness * normalizedSaturation;
    const p = 2 * normalizedLightness - q;
    const red = hueToRgb(p, q, normalizedHue + 1 / 3);
    const green = hueToRgb(p, q, normalizedHue);
    const blue = hueToRgb(p, q, normalizedHue - 1 / 3);
    return `#${channelToHex(red)}${channelToHex(green)}${channelToHex(blue)}`;
  }

  function inferCssClassKind(className: string, rule = '') {
    const normalized = `${className} ${rule}`.toLowerCase();
    if (/button|btn|cta|link|display:\s*inline-block/.test(normalized)) return 'button';
    if (/image|img|photo|hero-image|<img|object-fit|height:\s*auto/.test(normalized)) return 'image';
    if (/table|thead|tbody|tr|td|th|border-collapse/.test(normalized)) return 'section';
    if (/title|heading|headline|copy|text|muted|eyebrow|font-size|line-height/.test(normalized)) return 'text';
    if (/section|card|panel|hero|banner|block|border:|box-shadow/.test(normalized)) return 'section';
    return 'container';
  }

  function cssDesignLinkStatus(className: string) {
    const block = designBlockForClass(className);
    if (!block) return ' Code-only class; no Design block is linked.';
    return ` Linked to ${designTreeMeta(block).label}; Back to Design will reselect it.`;
  }

  function selectCssClass(className: string) {
    setSelectedCssClass(className);
    const rule = cssRuleForClass(className);
    setCssClassKind(inferCssClassKind(className, rule));
    if (rule) {
      syncCssControlsFromRule(rule, className);
      return;
    }
    if (className) {
      setStatus(`Selected .${className}. No CSS rule exists yet; choose controls and create one.${cssDesignLinkStatus(className)}`);
    }
  }

  function designClassNameForBlock(block: TemplateDesignBlock) {
    if (block.type === 'heading') return Number(block.level) === 1 ? 'email-title' : 'email-heading';
    if (block.type === 'paragraph') return 'email-copy';
    if (block.type === 'button') return 'button';
    if (block.type === 'image') return 'email-image';
    if (block.type === 'table') return 'email-table';
    if (block.type === 'list') return 'email-list';
    if (block.type === 'divider') return 'email-divider';
    if (block.type === 'spacer') return 'email-spacer';
    if (block.type === 'section') return 'email-section';
    if (block.type === 'columns') return 'email-columns';
    if (block.type === 'trust_signal') return 'secondary-text';
    if (block.type === 'social_links') return 'email-social-links';
    if (block.type === 'footer') return 'email-footer';
    if (block.type === 'html') return 'email-custom-html';
    return `email-${block.type.replace(/_/g, '-')}`;
  }

  function revealCssEditorTools() {
    window.setTimeout(() => {
      cssEditorSectionRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
      cssEditorRef.current?.focus();
    }, 0);
  }

  function designBlockForClass(className: string, blocks = designDoc.blocks): TemplateDesignBlock | null {
    for (const block of blocks) {
      const classNames = String(block.className || '').split(/\s+/).filter(Boolean);
      if (classNames.includes(className)) return block;
      const childMatch = block.children?.length ? designBlockForClass(className, block.children) : null;
      if (childMatch) return childMatch;
    }
    return null;
  }

  function returnToDesignBlockForClass(className = selectedCssClass) {
    const block = designBlockForClass(className);
    if (!block) {
      setStatus(className ? `No Design block currently uses .${className}.` : 'Select a CSS class before returning to Design.');
      return;
    }
    selectDesignBlock(block.id, designBlockAncestorIds(block.id));
    setEditorMode('design');
    setStatus(`Returned to Design and selected .${className}.`);
  }
  const selectedCssDesignBlock = selectedCssClass ? designBlockForClass(selectedCssClass) : null;
  const designLinkedCssClassCount = cssClassCoverage.filter((item) => designBlockForClass(item.name)).length;
  const codeOnlyCssClassCount = Math.max(0, cssClassCoverage.length - designLinkedCssClassCount);

  function focusDesignBlockCss(block: TemplateDesignBlock) {
    selectDesignBlock(block.id);
    const className = String(block.className || '').split(/\s+/).filter(Boolean)[0] || designClassNameForBlock(block);
    let sourceDoc = designDoc;
    if (!block.className) {
      rememberDesignState();
      const updateBlocks = (blocks: TemplateDesignBlock[]): TemplateDesignBlock[] => blocks.map((item) => {
        if (item.id === block.id) return { ...item, className };
        if (item.children?.length) return { ...item, children: updateBlocks(item.children) };
        return item;
      });
      sourceDoc = { blocks: updateBlocks(designDoc.blocks) };
      setDesignDoc(sourceDoc);
      markPreviewStale();
    }
    selectCssClass(className);
    setCssToolsOpen(true);
    if (editorMode === 'design') {
      setHtmlBody(designDocumentTemplateSource(sourceDoc));
      setDesignDocEdited(false);
      setEditorMode('edit');
    }
    revealCssEditorTools();
    setStatus(`${block.className ? 'Styling' : 'Added class and opened CSS tools for'} .${className} from ${block.type.replace('_', ' ')} block.`);
  }

  function syncHtmlSelectionToCssClass(from?: number, to?: number) {
    const selection = typeof from === 'number' && typeof to === 'number'
      ? { from, to }
      : htmlEditorRef.current?.getSelectionRange();
    if (!selection) return;
    const cursor = selection.from;
    const selected = htmlBody.slice(selection.from, selection.to);
    const searchStart = Math.max(0, cursor - 500);
    const searchEnd = Math.min(htmlBody.length, cursor + 500);
    const context = `${htmlBody.slice(searchStart, cursor)}${selected}${htmlBody.slice(cursor, searchEnd)}`;
    const classMatch = context.match(/class=["']([^"']+)["']/);
    const className = classMatch?.[1]?.split(/\s+/).filter(Boolean)[0];
    if (className && htmlClassNames.includes(className) && className !== selectedCssClass) {
      selectCssClass(className);
      setStatus(`Selected .${className} from HTML. CSS controls are synced below.${cssDesignLinkStatus(className)}`);
    }
  }

  function syncCssSelectionToClass() {
    const editor = cssEditorRef.current;
    if (!editor) return;
    const cursor = editor.selectionStart ?? 0;
    const beforeCursor = cssBody.slice(0, cursor);
    const selectorStart = beforeCursor.lastIndexOf('.');
    const blockStart = beforeCursor.lastIndexOf('{');
    const blockEnd = beforeCursor.lastIndexOf('}');
    if (selectorStart < 0 || blockEnd > blockStart) return;
    const selector = cssBody.slice(selectorStart, Math.min(cssBody.indexOf('{', selectorStart), cssBody.length));
    const className = selector.match(/\.([a-zA-Z0-9_-]+)/)?.[1];
    if (className && htmlClassNames.includes(className) && className !== selectedCssClass) {
      selectCssClass(className);
      setStatus(`Selected .${className} from CSS. Class editor is synced below.${cssDesignLinkStatus(className)}`);
    }
  }

  function syncCssControlsFromRule(rule = cssRuleForClass(selectedCssClass), className = selectedCssClass) {
    if (!rule) {
      setStatus(className ? `No CSS rule exists yet for .${className}. Choose a style type and update CSS.${cssDesignLinkStatus(className)}` : 'Select an HTML class to load existing CSS values.');
      return;
    }
    const paddingMatch = cssProperty(rule, 'padding').match(/\d+/);
    const radiusMatch = cssProperty(rule, 'border-radius').match(/\d+/);
    const widthMatch = cssProperty(rule, 'max-width').match(/\d+/);
    setCssPreset((current) => ({
      ...current,
      font: cssProperty(rule, 'font-family') || current.font,
      background: normalizeCssColor(cssProperty(rule, 'background'), current.background),
      text: normalizeCssColor(cssProperty(rule, 'color'), current.text),
      accent: normalizeCssColor(cssProperty(rule, 'border-color'), current.accent),
      container: widthMatch?.[0] || current.container,
      padding: paddingMatch?.[0] || current.padding,
      radius: radiusMatch?.[0] || current.radius,
    }));
    setStatus(className ? `Loaded CSS values from .${className}.${cssDesignLinkStatus(className)}` : 'Loaded CSS values from the selected rule.');
  }

  useEffect(() => {
    if (!selectedCssClass && htmlClassNames.length) {
      setSelectedCssClass(htmlClassNames[0]);
    }
    if (selectedCssClass && !htmlClassNames.includes(selectedCssClass)) {
      setSelectedCssClass(htmlClassNames[0] || '');
    }
  }, [htmlClassNames, selectedCssClass]);

  useEffect(() => {
    if (classableHtmlTagCount) setHtmlToolsOpen(true);
  }, [classableHtmlTagCount]);

  useEffect(() => {
    if (missingCssClasses.length || (selectedCssClass && !selectedCssRule)) setCssToolsOpen(true);
  }, [missingCssClasses.length, selectedCssClass, selectedCssRule]);

  function generatedCssFromPreset() {
    const width = Number(cssPreset.container) || 640;
    const padding = Number(cssPreset.padding) || 24;
    const radius = Number(cssPreset.radius) || 8;
    const compactPadding = Math.max(8, Math.round(padding / 2));
    return [
      `body { margin: 0; background: ${cssPreset.background}; color: ${cssPreset.text}; font-family: ${cssPreset.font}; }`,
      `.email-container { max-width: ${width}px; margin: 0 auto; background: #ffffff; padding: ${padding}px; border-radius: ${radius}px; }`,
      `h1, h2, h3 { color: ${cssPreset.text}; margin-top: 0; }`,
      `p { line-height: 1.55; }`,
      `a { color: ${cssPreset.accent}; }`,
      `.button, .cta { display: inline-block; background: ${cssPreset.accent}; color: #ffffff; padding: 12px 18px; border-radius: ${radius}px; text-decoration: none; font-weight: 700; }`,
      `.email-table { width: 100%; border-collapse: collapse; color: ${cssPreset.text}; }`,
      `.email-table th, .email-table td { border: 1px solid #d8dee6; padding: ${compactPadding}px; text-align: left; vertical-align: top; }`,
      `.email-table th { background: ${cssPreset.background}; }`,
      `.email-social-links { color: ${cssPreset.accent}; font-size: 13px; line-height: 1.5; text-align: center; padding: ${compactPadding}px 0; }`,
      `.email-social-links a { color: ${cssPreset.accent}; text-decoration: none; font-weight: 700; }`,
      `.email-footer { color: #64748b; font-size: 12px; line-height: 1.5; text-align: center; padding: ${compactPadding}px 0 0; }`,
      `.muted { color: #6b7280; font-size: 13px; }`,
      `@media only screen and (max-width: 640px) { .email-container { width: auto !important; padding: 18px !important; border-radius: 0 !important; } }`,
    ].join('\n');
  }

  function classRuleFromPreset(className: string, kind = cssClassKind) {
    const radius = Number(cssPreset.radius) || 8;
    const padding = Number(cssPreset.padding) || 24;
    const width = Number(cssPreset.container) || 640;
    const compactPadding = Math.max(8, Math.round(padding / 2));
    if (kind === 'button') {
      return `.${className} {\n  display: inline-block;\n  background: ${cssPreset.accent};\n  color: #ffffff;\n  font-family: ${cssPreset.font};\n  padding: ${compactPadding}px ${padding}px;\n  border-radius: ${radius}px;\n  text-decoration: none;\n  font-weight: 700;\n  text-align: center;\n}`;
    }
    if (kind === 'text') {
      return `.${className} {\n  color: ${cssPreset.text};\n  font-family: ${cssPreset.font};\n  line-height: 1.55;\n  margin: 0 0 12px;\n}`;
    }
    if (kind === 'image') {
      return `.${className} {\n  display: block;\n  width: 100%;\n  max-width: ${width}px;\n  height: auto;\n  border-radius: ${radius}px;\n  border: 1px solid #e5e7eb;\n}`;
    }
    if (kind === 'section') {
      return `.${className} {\n  background: ${cssPreset.background};\n  color: ${cssPreset.text};\n  font-family: ${cssPreset.font};\n  padding: ${padding}px;\n  border-radius: ${radius}px;\n  border: 1px solid ${cssPreset.accent};\n}`;
    }
    return `.${className} {\n  max-width: ${width}px;\n  margin: 0 auto;\n  background: ${cssPreset.background};\n  color: ${cssPreset.text};\n  font-family: ${cssPreset.font};\n  padding: ${padding}px;\n  border-radius: ${radius}px;\n}`;
  }

  function formatCssSource(source: string) {
    return source
      .replace(/\/\*/g, '\n/*')
      .replace(/\*\//g, '*/\n')
      .replace(/\s*\{\s*/g, ' {\n  ')
      .replace(/;\s*/g, ';\n  ')
      .replace(/\s*\}\s*/g, '\n}\n\n')
      .split('\n')
      .map((line) => line.trimEnd())
      .join('\n')
      .replace(/\n\s+\}/g, '\n}')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  function formatCssEditor() {
    setCssBody(formatCssSource(cssBody));
    markPreviewStale();
    setStatus('Formatted CSS source. Use Preview to render the updated styles.');
  }

  function applyCssPreset() {
    if (selectedCssClass) {
      const classRule = classRuleFromPreset(selectedCssClass);
      const escaped = selectedCssClass.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const classRegex = new RegExp(`\\.${escaped}\\s*\\{[^}]*\\}`, 'm');
      setCssBody((current) => classRegex.test(current)
        ? current.replace(classRegex, classRule)
        : `${current.trim()}\n\n${classRule}`.trim());
    } else {
      setCssBody(generatedCssFromPreset());
    }
    markPreviewStale();
    setStatus(selectedCssClass ? `Updated CSS for .${selectedCssClass}. Click Preview to render it.` : 'Generated email-safe CSS from style controls. Click Preview to render it.');
  }

  function scaffoldMissingCssClasses() {
    if (!missingCssClasses.length) {
      setStatus('All detected HTML classes already have CSS rules.');
      return;
    }
    const missingRules = missingCssClasses.map((className) => classRuleFromPreset(className, inferCssClassKind(className))).join('\n\n');
    setCssBody((current) => `${current.trim()}\n\n${missingRules}`.trim());
    markPreviewStale();
    setStatus(`Created CSS rules for ${missingCssClasses.map((className) => `.${className}`).join(', ')}. Click Preview to render them.`);
  }

  function openCssGapTools() {
    setEditorMode('edit');
    setCssToolsOpen(true);
    if (missingCssClasses[0]) setSelectedCssClass(missingCssClasses[0]);
    setStatus(missingCssClasses.length ? `Opened CSS tools for ${formatInt(missingCssClasses.length)} missing class rule(s).` : 'Opened CSS tools. All detected classes currently have rules.');
  }

  function htmlBlockSnippet(kind: string) {
    const blocks: Record<string, string> = {
      container: '<div class="email-container">\n  <h1 class="email-title">Hello {{ first_name }}</h1>\n  <p class="email-copy">Add your message here.</p>\n</div>',
      hero: '<section class="email-hero">\n  <h1 class="email-title">Your headline goes here</h1>\n  <p class="email-copy">A short supporting line for {{ first_name }}.</p>\n  <p class="email-action"><a class="button" href="{{ tracking_click }}">Call to action</a></p>\n</section>',
      heading: '<h2 class="email-heading">Section heading</h2>',
      paragraph: '<p class="email-copy">Hello {{ first_name }},</p>\n<p class="email-copy">Add a concise paragraph with one clear idea.</p>',
      image: '<img class="email-image" src="{{ hero_image_url }}" alt="Describe this image" style="width: 100%; max-width: 600px; height: auto; display: block;" />',
      button: '<p class="email-action"><a class="button" href="{{ tracking_click }}">Call to action</a></p>',
      divider: '<hr class="email-divider" style="border: 0; border-top: 1px solid #e5e7eb; margin: 24px 0;" />',
      spacer: '<div class="email-spacer" style="height: 24px; line-height: 24px;">&nbsp;</div>',
      quote: '<blockquote class="email-quote" style="margin: 0; padding: 16px; border-left: 4px solid #2563eb; background: #f8fafc;">\n  <p class="email-copy">{{ testimonial }}</p>\n</blockquote>',
      twoColumn: '<table class="email-two-column" role="presentation" width="100%" cellspacing="0" cellpadding="0">\n  <tr class="email-row">\n    <td class="email-column" style="width: 50%; padding-right: 8px;">Left column content</td>\n    <td class="email-column" style="width: 50%; padding-left: 8px;">Right column content</td>\n  </tr>\n</table>',
      list: '<ul class="email-list">\n{% for item in recommendations %}\n  <li class="email-list-item">{{ loop.index }}. {{ item }}</li>\n{% endfor %}\n</ul>',
      conditional: '{% if plan == "trial" %}\n  <p class="email-copy">Your trial plan is active.</p>\n{% else %}\n  <p class="email-copy">Your plan is {{ plan }}.</p>\n{% endif %}',
      compliance: '<p class="muted">You are receiving this because you opted in. <a class="unsubscribe-link" href="{{ unsubscribe_url }}">Unsubscribe</a></p>',
    };
    return blocks[kind] || blocks.paragraph;
  }

  function classNameForHtmlTag(tag: string, attrs = '') {
    const normalized = tag.toLowerCase();
    if (normalized === 'h1') return 'email-title';
    if (normalized === 'h2' || normalized === 'h3') return 'email-heading';
    if (normalized === 'p') return /href=/.test(attrs) ? 'email-action' : 'email-copy';
    if (normalized === 'a') return /unsubscribe/i.test(attrs) ? 'unsubscribe-link' : 'email-link';
    if (normalized === 'img') return 'email-image';
    if (normalized === 'section') return 'email-section';
    if (normalized === 'div') return 'email-block';
    if (normalized === 'table') return 'email-table';
    if (normalized === 'tr') return 'email-row';
    if (normalized === 'td') return 'email-cell';
    if (normalized === 'ul' || normalized === 'ol') return 'email-list';
    if (normalized === 'li') return 'email-list-item';
    if (normalized === 'blockquote') return 'email-quote';
    if (normalized === 'hr') return 'email-divider';
    return `email-${normalized}`;
  }

  function htmlWithMissingClasses(source: string) {
    let added = 0;
    const html = source.replace(/<([a-z][a-z0-9-]*)(\s[^<>]*)?>/gi, (full, tag: string, attrs = '') => {
      const normalized = tag.toLowerCase();
      if (['html', 'head', 'body', 'meta', 'title', 'style', 'script', 'br'].includes(normalized) || /\sclass\s*=/.test(attrs)) {
        return full;
      }
      added += 1;
      return `<${tag} class="${classNameForHtmlTag(tag, attrs)}"${attrs || ''}>`;
    });
    return { html, added };
  }

  function addMissingHtmlClasses() {
    const { html: nextHtml, added } = htmlWithMissingClasses(htmlBody);
    if (!added) {
      setStatus('All common HTML elements already have classes.');
      return;
    }
    setHtmlBody(nextHtml);
    markPreviewStale();
    setStatus(`Added classes to ${formatInt(added)} HTML element(s). Review CSS coverage for new rules.`);
  }

  function addMissingHtmlClassesAndCss() {
    const { html: nextHtml, added } = htmlWithMissingClasses(htmlBody);
    const nextClassNames = extractHtmlClassNames(nextHtml);
    const missingRules = nextClassNames.filter((className) => !cssHasRuleForClass(cssBody, className));
    if (!added && !missingRules.length) {
      setStatus('HTML classes and CSS rules are already aligned.');
      return;
    }
    const nextRules = missingRules.map((className) => classRuleFromPreset(className, inferCssClassKind(className))).join('\n\n');
    setHtmlBody(nextHtml);
    if (nextRules) {
      setCssBody((current) => `${current.trim()}\n\n${nextRules}`.trim());
    }
    markPreviewStale();
    setStatus(`Added ${formatInt(added)} class(es) and created ${formatInt(missingRules.length)} CSS rule(s). Use Preview to render the updated template.`);
  }

  function formatHtmlJinjaSource(source: string) {
    const tokens = source.replace(/>\s+</g, '>\n<').replace(/\s*({%|{{)/g, '\n$1').replace(/(%}|}})\s*/g, '$1\n').split('\n');
    let depth = 0;
    return tokens
      .map((raw) => raw.trim())
      .filter(Boolean)
      .map((line) => {
        if (/^<\//.test(line) || /^{%\s*(else|elif|endif|endfor|endblock)/.test(line)) depth = Math.max(0, depth - 1);
        const formatted = `${'  '.repeat(depth)}${line}`;
        if (/^<[^/!][^>]*[^/]>\s*$/.test(line) && !/^<(br|hr|img|input|meta|link)\b/i.test(line)) depth += 1;
        if (/^{%\s*(if|for|block|macro)\b/.test(line)) depth += 1;
        if (/^{%\s*(else|elif)\b/.test(line)) depth += 1;
        return formatted;
      })
      .join('\n');
  }

  function ensureTemplateContainer(source: string) {
    const trimmed = source.trim();
    if (!trimmed) return '<div class="email-container">\n</div>';
    if (/^<div[^>]+class=["'][^"']*email-container/.test(trimmed)) return trimmed;
    return `<div class="email-container">\n${formatHtmlJinjaSource(trimmed).split('\n').map((line) => `  ${line}`).join('\n')}\n</div>`;
  }

  function formatTemplateSource() {
    const nextHtml = ensureTemplateContainer(formatHtmlJinjaSource(htmlBody));
    setHtmlBody(nextHtml);
    markPreviewStale();
    setStatus('Formatted HTML/Jinja and ensured an email-container wrapper.');
  }

  function insertHtmlBlock(kind: string) {
    const snippet = htmlBlockSnippet(kind);
    const selection = htmlEditorRef.current?.getSelectionRange();
    const start = selection?.from ?? htmlBody.length;
    const end = selection?.to ?? htmlBody.length;
    const before = htmlBody.slice(0, start);
    const after = htmlBody.slice(end);
    const prefix = before && !before.endsWith('\n') ? '\n\n' : '';
    const suffix = after && !after.startsWith('\n') ? '\n\n' : '';
    const nextHtml = `${before}${prefix}${snippet}${suffix}${after}`.trim();
    const nextCursor = Math.min(`${before}${prefix}${snippet}`.length, nextHtml.length);
    setHtmlBody(nextHtml);
    markPreviewStale();
    setEditorMode('edit');
    setStatus('Inserted HTML block. Click Preview to refresh variables and render it.');
    window.setTimeout(() => {
      htmlEditorRef.current?.focus();
      htmlEditorRef.current?.setSelectionRange(nextCursor, nextCursor);
    }, 0);
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

  function safeVariablesObject() {
    try {
      return parsedVariables();
    } catch {
      return {};
    }
  }

  function sampleJsonError() {
    try {
      parsedVariables();
      return '';
    } catch (error) {
      return error instanceof Error ? error.message : 'Invalid variables JSON.';
    }
  }

  function formatSampleInput(value: unknown) {
    if (value === undefined || value === null) return '';
    if (typeof value === 'string') return value;
    return JSON.stringify(value);
  }

  function parseSampleInput(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return '';
    try {
      return JSON.parse(trimmed);
    } catch {
      return value;
    }
  }

  function updateSampleVariable(name: string, value: string) {
    const current = safeVariablesObject();
    setVariablesJson(JSON.stringify({ ...current, [name]: parseSampleInput(value) }, null, 2));
    markPreviewStale();
  }

  function formatVariablesJson() {
    try {
      setVariablesJson(JSON.stringify(parsedVariables(), null, 2));
      markPreviewStale();
      setStatus('Formatted sample variables JSON.');
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Invalid variables JSON.'}`);
    }
  }

  const variablesJsonError = sampleJsonError();
  const sampleVariables = safeVariablesObject();
  const sampleVariableRows = variables.length
    ? variables.map((variable) => ({
      name: variable.name,
      value: sampleVariables[variable.name] ?? variable.sample_value ?? '',
      source: variable.native ? 'native' : (variable.sources?.[0] || 'template'),
    }))
    : Object.keys(sampleVariables).map((name) => ({ name, value: sampleVariables[name], source: 'sample' }));
  const nativeSampleVariableCount = sampleVariableRows.filter((item) => item.source === 'native').length;
  const jsonSampleVariableCount = Object.keys(sampleVariables).length;
  const templateEditorCompletions = Array.from(new Set([
    ...sampleVariableRows.map((item) => item.name),
    'first_name',
    'last_name',
    'email',
    'unsubscribe_url',
    'tracking_click',
    'tracking_open',
  ].filter(Boolean)));

  function renderDesignBlockControls(block: TemplateDesignBlock) {
    const colorValue = (value: unknown, fallback = '#111827') => /^#[0-9a-f]{6}$/i.test(String(value || '')) ? String(value) : fallback;
    const classOptions = Array.from(new Set([...htmlClassNames, ...String(block.className || '').split(/\s+/).filter(Boolean)])).sort();
    const textInput = (label: string, key: keyof TemplateDesignBlock, type = 'text') => (
      <label>
        {label}
        <input type={type} value={type === 'color' ? colorValue(block[key]) : String(block[key] ?? '')} onChange={(event) => updateDesignBlock(block.id, { [key]: type === 'number' ? Number(event.target.value) : event.target.value })} />
      </label>
    );
    const classInput = () => (
      <label>
        CSS class
        <select value={String(block.className || '')} onChange={(event) => updateDesignBlock(block.id, { className: event.target.value })}>
          <option value="">No class</option>
          {classOptions.map((className) => (
            <option key={className} value={className}>.{className}</option>
          ))}
        </select>
      </label>
    );
    const textArea = (label: string, key: keyof TemplateDesignBlock) => (
      <label className="wide-field">
        {label}
        <textarea rows={3} value={Array.isArray(block[key]) ? (block[key] as string[]).join('\n') : String(block[key] ?? '')} onChange={(event) => updateDesignBlock(block.id, { [key]: key === 'items' ? event.target.value.split('\n').map((item) => item.trim()).filter(Boolean) : event.target.value })} />
      </label>
    );
    const designColorPanel = (config: {
      allowTransparent?: boolean;
      ariaPrefix: string;
      emptyLabel: string;
      keyName: keyof TemplateDesignBlock;
      label: string;
      presets: { name: string; value: string }[];
    }) => {
      const rawValue = String(block[config.keyName] || '');
      const color = normalizeCssColor(rawValue, config.allowTransparent ? '#ffffff' : '#111827');
      const hsl = hexToHsl(color);
      const updateColor = (value: string) => updateDesignBlock(block.id, { [config.keyName]: value });
      const updateHsl = (updates: Partial<typeof hsl>) => updateColor(hslToHex(updates.h ?? hsl.h, updates.s ?? hsl.s, updates.l ?? hsl.l));
      return (
        <label className="design-color-control wide-field">
          {config.label}
          <div className="design-background-picker">
            <div className="design-color-main">
              <span className={`design-color-preview ${rawValue ? '' : 'empty'}`} style={{ backgroundColor: rawValue || 'transparent' }} aria-hidden="true" />
              <div>
                <strong>{rawValue || config.emptyLabel}</strong>
                <small>{rawValue ? `H ${hsl.h} / S ${hsl.s} / L ${hsl.l}` : config.emptyLabel}</small>
              </div>
              {config.allowTransparent ? <button className="ghost" onClick={() => updateColor('')} type="button">None</button> : null}
            </div>
            <div className="design-color-presets" aria-label={`${config.ariaPrefix} presets`}>
              {config.presets.map((preset) => (
                <button
                  className={preset.value.toLowerCase() === rawValue.toLowerCase() ? 'selected' : ''}
                  key={preset.name}
                  onClick={() => updateColor(preset.value)}
                  type="button"
                >
                  <span style={{ backgroundColor: preset.value }} />
                  {preset.name}
                </button>
              ))}
            </div>
            <div className="design-color-sliders">
              <label>
                Hue
                <input aria-label={`${config.ariaPrefix} hue`} max="360" min="0" type="range" value={hsl.h} onChange={(event) => updateHsl({ h: Number(event.target.value) })} />
              </label>
              <label>
                Saturation
                <input aria-label={`${config.ariaPrefix} saturation`} max="100" min="0" type="range" value={hsl.s} onChange={(event) => updateHsl({ s: Number(event.target.value) })} />
              </label>
              <label>
                Lightness
                <input aria-label={`${config.ariaPrefix} lightness`} max="100" min="0" type="range" value={hsl.l} onChange={(event) => updateHsl({ l: Number(event.target.value) })} />
              </label>
            </div>
            <div className="design-color-picker compact">
              <input
                aria-label={`${config.ariaPrefix} hex color`}
                placeholder={config.allowTransparent ? 'transparent' : '#111827'}
                value={rawValue}
                onChange={(event) => updateColor(event.target.value)}
                onBlur={(event) => updateColor(event.target.value.trim() ? normalizeCssColor(event.target.value, color) : '')}
              />
              <input
                aria-label={`${config.ariaPrefix} color picker`}
                className="native-color-input"
                type="color"
                value={color}
                onChange={(event) => updateColor(event.target.value)}
              />
            </div>
            <div className="design-color-swatches" aria-label={`${config.ariaPrefix} color swatches`}>
              {cssColorSwatches.map((swatch) => (
              <button
                aria-label={`Use ${swatch}`}
                className={swatch.toLowerCase() === rawValue.toLowerCase() ? 'selected' : ''}
                key={swatch}
                onClick={() => updateColor(swatch)}
                style={{ backgroundColor: swatch }}
                title={swatch}
                type="button"
              />
              ))}
            </div>
          </div>
        </label>
      );
    };
    const backgroundControl = () => designColorPanel({
      allowTransparent: true,
      ariaPrefix: 'Design background',
      emptyLabel: 'Transparent',
      keyName: 'bg',
      label: 'Background',
      presets: designBackgroundPresets,
    });
    const textColorControl = (label = 'Text color', ariaPrefix = 'Design text color') => designColorPanel({
      ariaPrefix,
      emptyLabel: 'Default text color',
      keyName: 'color',
      label,
      presets: [
        { name: 'Ink', value: '#111827' },
        { name: 'Slate', value: '#334155' },
        { name: 'Muted', value: '#64748b' },
        { name: 'White', value: '#ffffff' },
        { name: 'Blue', value: '#2563eb' },
        { name: 'Green', value: '#0f766e' },
        { name: 'Amber', value: '#f59e0b' },
        { name: 'Purple', value: '#7c3aed' },
      ],
    });
    const paddingControls = () => (
      <>
        {textInput('Vertical padding', 'padding_y', 'number')}
        {textInput('Horizontal padding', 'padding_x', 'number')}
      </>
    );
    const inspectorGroup = (title: string, detail: string, children: ReactNode) => (
      <fieldset className="design-inspector-group">
        <legend>{title}</legend>
        <small>{detail}</small>
        <div>{children}</div>
      </fieldset>
    );
    if (block.type === 'heading') {
      return (
        <>
          {inspectorGroup('Content', 'Text and heading level', <>{textInput('Text', 'text')}{textInput('Level', 'level', 'number')}</>)}
          {inspectorGroup('Style', 'Class, alignment, and colors', <>{classInput()}<label>Align<select value={block.align || 'left'} onChange={(event) => updateDesignBlock(block.id, { align: event.target.value })}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label>{textColorControl()}{backgroundControl()}</>)}
          {inspectorGroup('Layout', 'Spacing around this block', <>{paddingControls()}</>)}
        </>
      );
    }
    if (block.type === 'button') {
      return (
        <>
          {inspectorGroup('Content', 'CTA label and destination', <>{textInput('Text', 'text')}{textInput('URL', 'href')}</>)}
          {inspectorGroup('Style', 'Button class, fill, text color, and radius', <>{classInput()}{backgroundControl()}{textColorControl()}{textInput('Radius', 'radius', 'number')}</>)}
        </>
      );
    }
    if (block.type === 'list') {
      return (
        <>
          <label>List type<select value={block.ordered ? 'ordered' : 'bulleted'} onChange={(event) => updateDesignBlock(block.id, { ordered: event.target.value === 'ordered' })}><option value="bulleted">Bulleted</option><option value="ordered">Numbered</option></select></label>
          {classInput()}
          {textColorControl()}
          {backgroundControl()}
          {paddingControls()}
          {textArea('Items', 'items')}
        </>
      );
    }
    if (block.type === 'image') {
      return (
        <>
          {inspectorGroup('Content', 'Image source, alt text, and link', <>{textInput('Image URL', 'src')}{textInput('Alt text', 'alt')}{textInput('Link URL', 'href')}</>)}
          {inspectorGroup('Layout', 'Class and email-safe width', <>{classInput()}{textInput('Width', 'width', 'number')}</>)}
        </>
      );
    }
    if (block.type === 'table') {
      return (
        <>
          {inspectorGroup('Content', 'Header cells and row data', <><label className="wide-field">
            Headers
            <input
              value={(block.table_headers || []).join(' | ')}
              onChange={(event) => updateDesignBlock(block.id, {
                table_headers: event.target.value.split('|').map((cell) => cell.trim()).filter(Boolean),
              })}
            />
          </label>
          <label className="wide-field">
            Rows
            <textarea
              rows={5}
              value={tableRowsText(block)}
              onChange={(event) => updateDesignBlock(block.id, { table_rows: parseTableRowsText(event.target.value) })}
            />
          </label></>)}
          {inspectorGroup('Style', 'Class and table colors', <>{classInput()}{backgroundControl()}{textColorControl()}</>)}
          {inspectorGroup('Layout', 'Cell padding', <>{paddingControls()}</>)}
        </>
      );
    }
    if (block.type === 'footer') {
      return (
        <>
          {inspectorGroup('Content', 'Footer copy and unsubscribe destination', <>{textArea('Footer text', 'text')}{textInput('Unsubscribe URL', 'href')}</>)}
          {inspectorGroup('Style', 'Class, alignment, and colors', <>{classInput()}<label>Align<select value={block.align || 'center'} onChange={(event) => updateDesignBlock(block.id, { align: event.target.value })}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label>{textColorControl()}{backgroundControl()}</>)}
          {inspectorGroup('Layout', 'Footer spacing', <>{paddingControls()}</>)}
        </>
      );
    }
    if (block.type === 'social_links') {
      return (
        <>
          {inspectorGroup('Content', 'One social link per line as label | URL', <><label className="wide-field">
            Links
            <textarea
              rows={4}
              value={socialLinksText(block)}
              onChange={(event) => updateDesignBlock(block.id, { social_links: parseSocialLinksText(event.target.value) })}
            />
          </label></>)}
          {inspectorGroup('Style', 'Class, alignment, link color, and background', <>{classInput()}<label>Align<select value={block.align || 'center'} onChange={(event) => updateDesignBlock(block.id, { align: event.target.value })}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label>{textColorControl('Link color', 'Social link color')}{backgroundControl()}</>)}
          {inspectorGroup('Layout', 'Spacing around links', <>{paddingControls()}</>)}
        </>
      );
    }
    if (isDesignContainerBlock(block)) {
      const childBlockTypes = designPaletteBlockTypes.filter((type) => type !== 'section' && type !== 'columns');
      return (
        <>
          {inspectorGroup('Style', 'Container class and background', <>{classInput()}{backgroundControl()}</>)}
          {inspectorGroup('Layout', 'Container spacing and mobile behavior', <>{textInput('Padding', 'padding_y', 'number')}{block.type === 'columns' ? textInput('Column gap', 'gap', 'number') : null}{block.type === 'columns' ? (
            <label>Mobile behavior<select value={block.mobile_stack || 'stack'} onChange={(event) => updateDesignBlock(block.id, { mobile_stack: event.target.value as TemplateDesignBlock['mobile_stack'] })}><option value="stack">Stack columns</option><option value="reverse">Reverse stack</option><option value="keep">Keep columns</option></select></label>
          ) : null}</>)}
          {inspectorGroup('Structure', 'Nested block count and insertion controls', <>
          <label className="wide-field">
            Contents
            <input value={`${formatInt(block.children?.length || 0)} nested block(s)`} readOnly />
          </label>
          {block.type === 'columns' ? (
            <div className="section-child-tools wide-field">
              <span>Manage columns</span>
              <div>
                <button className="ghost" type="button" onClick={() => addDesignColumn(block.id)} disabled={busy}>Add Column</button>
                <button className="ghost" type="button" onClick={() => removeLastDesignColumn(block.id)} disabled={busy || (block.children?.length || 0) <= 1}>Remove Last Column</button>
              </div>
            </div>
          ) : null}
          {block.type === 'columns' && block.children?.length ? (
            <div className="column-width-tools wide-field">
              <span>Column widths</span>
              {block.children.map((child, index) => (
                <label key={child.id}>
                  <small>Column {index + 1}</small>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={Number(child.width || Math.round(100 / (block.children?.length || 1)))}
                    onChange={(event) => updateDesignBlock(child.id, { width: Number(event.target.value) })}
                  />
                  <span className="column-width-actions">
                    <button className="ghost" type="button" onClick={() => moveDesignColumn(block.id, child.id, -1)} disabled={busy || !canMoveDesignBlock(child.id, -1)}>Left</button>
                    <button className="ghost" type="button" onClick={() => moveDesignColumn(block.id, child.id, 1)} disabled={busy || !canMoveDesignBlock(child.id, 1)}>Right</button>
                    <button className="ghost" type="button" onClick={() => duplicateDesignColumn(block.id, child.id)} disabled={busy}>Duplicate</button>
                  </span>
                </label>
              ))}
            </div>
          ) : null}
          <div className="section-child-tools wide-field">
            <span>Add to {designBlockTypeLabel(block.type).toLowerCase()}</span>
            <div>
              {childBlockTypes.map((type) => (
                <button className="ghost" key={type} type="button" onClick={() => addDesignChildBlock(block.id, type)} disabled={busy}>
                  {designBlockTypeLabel(type)}
                </button>
              ))}
            </div>
          </div>
          </>)}
        </>
      );
    }
    if (block.type === 'divider') return <>{classInput()}{textColorControl('Line color', 'Design line color')}</>;
    if (block.type === 'spacer') return <>{classInput()}{textInput('Height', 'height', 'number')}</>;
    if (block.type === 'trust_signal') return <>{classInput()}{textArea('Text', 'text')}{textColorControl()}{backgroundControl()}{paddingControls()}</>;
    if (block.type === 'html') return <>{textArea('HTML / Jinja', 'code')}</>;
    return (
      <>
        {textArea(block.html ? 'Inline HTML' : 'Text', block.html ? 'html' : 'text')}
        {classInput()}
        <label>Align<select value={block.align || 'left'} onChange={(event) => updateDesignBlock(block.id, { align: event.target.value })}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label>
        {textColorControl()}
        {backgroundControl()}
        {paddingControls()}
      </>
    );
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

  function recordTemplateRenderResult(input: {
    label: string;
    subject: string;
    ok: boolean;
    errors?: string[];
    variableCount: number;
    sourceMode?: 'edit' | 'design';
  }) {
    setTemplateRenderResult({
      label: input.label,
      subject: input.subject,
      ok: input.ok,
      errors: input.errors || [],
      variableCount: input.variableCount,
      cssGapCount: missingCssClasses.length,
      sourceMode: input.sourceMode || (editorMode === 'design' ? 'design' : 'edit'),
    });
  }

  async function saveTemplate() {
    await runTemplateOperation(selectedTemplateId ? 'Saving template' : 'Creating template', async () => {
      const designHtml = editorMode === 'design' ? designDocumentTemplateSource() : htmlBody;
      const normalizedHtml = ensureTemplateContainer(formatHtmlJinjaSource(designHtml));
      const documentJson = editorMode === 'design' ? designDoc : designDoc.blocks.length ? designDoc : {};
      const payload = {
        name: name.trim() || 'Untitled ESP Template',
        subject,
        html_body: normalizedHtml,
        css_body: cssBody || null,
        text_body: null,
        document_json: documentJson,
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
      clearTemplateLocalDraft(selectedTemplateId);
      clearTemplateLocalDraft(saved.id);
      setSelectedTemplateId(saved.id);
      setHtmlBody(normalizedHtml);
      setDesignDocEdited(false);
      setSavedTemplateSnapshot({
        name: payload.name,
        subject: payload.subject,
        htmlBody: normalizedHtml,
        cssBody: payload.css_body || '',
        designDocJson: Array.isArray((documentJson as TemplateDesignDocument).blocks)
          ? semanticDesignDocJson(documentJson as TemplateDesignDocument)
          : '{"blocks":[]}',
      });
      setAppliedAiDraftLabel('');
      window.location.hash = `#templates/${saved.id}`;
      await loadTemplateVersions(saved.id);
      await onRefresh();
      return `Saved template: ${saved.name}`;
    });
  }

  async function cancelTemplateChanges() {
    await runTemplateOperation('Cancelling changes', async () => {
      if (!selectedTemplateId) {
        resetTemplateEditor({ force: true });
        return 'Discarded unsaved draft changes.';
      }
      const template = await fetchJson<TemplateRead>(`/api/v1/templates/${selectedTemplateId}`);
      const nextDesignDoc = await designDocForTemplate(template);
      clearTemplateLocalDraft(selectedTemplateId);
      loadTemplateIntoEditor(template, { force: true, designDoc: nextDesignDoc });
      await onRefresh();
      return `Reloaded template: ${template.name}`;
    });
  }

  async function restoreTemplateVersion(version: TemplateVersionRead) {
    if (!selectedTemplateId) return;
    if (!window.confirm(`Restore template version ${version.version_number}? This creates a new current version.`)) return;
    await runTemplateOperation(`Restoring version ${version.version_number}`, async () => {
      await fetchJson<TemplateVersionRead>(`/api/v1/templates/${selectedTemplateId}/versions`, {
        method: 'POST',
        body: JSON.stringify({
          subject: version.subject,
          html_body: version.html_body,
          css_body: version.css_body,
          text_body: version.text_body,
          document_json: version.document_json || {},
          set_current: true,
        }),
      });
      const template = await fetchJson<TemplateRead>(`/api/v1/templates/${selectedTemplateId}`);
      const nextDesignDoc = await designDocForTemplate(template);
      clearTemplateLocalDraft(selectedTemplateId);
      loadTemplateIntoEditor(template, { force: true, designDoc: nextDesignDoc });
      await loadTemplateVersions(selectedTemplateId);
      await onRefresh();
      return `Restored version ${version.version_number}.`;
    });
  }

  async function deleteTemplateRow(template: TemplateRead) {
    if (!window.confirm(`Delete template "${template.name}"?`)) return;
    await runTemplateOperation('Deleting template', async () => {
      await fetchJson<{ id: string }>(`/api/v1/templates/${template.id}`, { method: 'DELETE' });
      if (selectedTemplateId === template.id) resetTemplateEditor({ force: true });
      await onRefresh();
      return `Deleted template: ${template.name}.`;
    });
  }

  async function previewTemplate() {
    await runTemplateOperation('Rendering preview', async () => {
      const sourceHtml = editorMode === 'design' ? designDocumentTemplateSource() : htmlBody;
      const variableData = await refreshVariables(true);
      const data = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject,
          html_body: sourceHtml,
          css_body: cssBody || null,
          variables: variableData.renderVariables,
        }),
      });
      setPreviewHtml(data.html_body || sourceHtml);
      setPreviewSubject(data.subject || '');
      setPreviewFreshness('current');
      setPreviewSourceMode(editorMode === 'design' ? 'design' : 'edit');
      setEditorMode('preview');
      recordTemplateRenderResult({
        label: 'Preview render',
        subject: data.subject || subject,
        ok: data.ok,
        errors: data.errors || [],
        variableCount: (variableData.variables || []).length,
        sourceMode: editorMode === 'design' ? 'design' : 'edit',
      });
      const issueText = data.errors?.length ? ` ${data.errors.join('; ')}` : '';
      return `Rendered preview: ${data.subject}.${issueText}`;
    });
  }

  async function previewAiDraft(draft: AITemplateDraft) {
    await runTemplateOperation('Rendering AI draft preview', async () => {
      const variableData = await refreshVariables(true);
      const data = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject: draft.subject || subject,
          html_body: draft.html_body || htmlBody,
          css_body: draft.css_body || cssBody || null,
          variables: draft.sample_variables && Object.keys(draft.sample_variables).length
            ? { ...variableData.renderVariables, ...draft.sample_variables }
            : variableData.renderVariables,
        }),
      });
      if (draft.sample_variables && Object.keys(draft.sample_variables).length) {
        setVariablesJson(JSON.stringify({ ...variableData.renderVariables, ...draft.sample_variables }, null, 2));
      }
      setPreviewHtml(data.html_body || '');
      setPreviewSubject(data.subject || draft.subject || subject);
      setPreviewFreshness('current');
      setEditorMode('preview');
      recordTemplateRenderResult({
        label: 'AI draft preview',
        subject: data.subject || draft.subject || subject,
        ok: data.ok,
        errors: data.errors || [],
        variableCount: (variableData.variables || []).length,
      });
      const issueText = data.errors?.length ? ` ${data.errors.join('; ')}` : '';
      return `Rendered AI draft preview: ${data.subject || draft.subject}.${issueText}`;
    });
  }

  async function previewTemplateVersion(version: TemplateVersionRead) {
    await runTemplateOperation(`Rendering version ${version.version_number} preview`, async () => {
      const variableData = await refreshVariables(true);
      const data = await fetchJson<{ ok: boolean; subject: string; html_body: string; errors: string[]; undeclared_variables: string[] }>('/api/v1/templates/preview', {
        method: 'POST',
        body: JSON.stringify({
          subject: version.subject || subject,
          html_body: version.html_body || htmlBody,
          css_body: version.css_body || null,
          variables: variableData.renderVariables,
        }),
      });
      setPreviewHtml(data.html_body || version.html_body || '');
      setPreviewSubject(data.subject || version.subject || subject);
      setPreviewFreshness('current');
      setPreviewSourceMode('edit');
      setEditorMode('preview');
      setSelectedVersionReviewId(version.id);
      recordTemplateRenderResult({
        label: `Version ${version.version_number} preview`,
        subject: data.subject || version.subject || subject,
        ok: data.ok,
        errors: data.errors || [],
        variableCount: (variableData.variables || []).length,
        sourceMode: 'edit',
      });
      const issueText = data.errors?.length ? ` ${data.errors.join('; ')}` : '';
      return `Rendered version ${version.version_number} preview: ${data.subject || version.subject}.${issueText}`;
    });
  }

  async function refreshVariables(fillMissingSamples = true) {
    const currentVariables = parsedVariables();
    const data = await fetchJson<{ variables: TemplateVariable[]; sample_variables: Record<string, unknown>; errors: string[] }>('/api/v1/templates/variables', {
      method: 'POST',
      body: JSON.stringify({
        subject,
        html_body: editorMode === 'design' ? designDocumentTemplateSource() : htmlBody,
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

  async function importSourceToDesignBlocks() {
    await runTemplateOperation('Importing source to design', async () => {
      const source = htmlBody.trim();
      if (!source) return 'Add HTML/Jinja source before importing design blocks.';
      let nextDesignDoc: TemplateDesignDocument;
      let rawBlockCount = 0;
      try {
        const data = await fetchJson<TemplateDocumentImportRead>('/api/v1/templates/document/import-html', {
          method: 'POST',
          body: JSON.stringify({ html_body: source }),
        });
        const blocks = data.document_json?.blocks;
        if (!Array.isArray(blocks) || !blocks.length) throw new Error('Import returned no blocks');
        nextDesignDoc = {
          blocks: blocks.map((block, index) => normalizeDesignBlock(block, index)),
        };
        rawBlockCount = data.raw_block_count || 0;
      } catch {
        nextDesignDoc = htmlToDesignDocument(source);
        rawBlockCount = flattenDesignBlocks(nextDesignDoc.blocks)
          .filter((block) => block.type === 'html' || block.type === 'raw')
          .length;
      }
      setDesignDoc(nextDesignDoc);
      setSelectedDesignBlockId(nextDesignDoc.blocks[0]?.id || '');
      setDesignDocEdited(true);
      setDesignUndoStack([]);
      setDesignRedoStack([]);
      setEditorMode('design');
      markPreviewStale();
      return `Imported ${formatInt(flattenDesignBlocks(nextDesignDoc.blocks).length)} design block(s). ${formatInt(rawBlockCount)} raw block(s) preserved.`;
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
	                    onClick={() => { void openTemplateInEditor(template); }}
	                    onDoubleClick={() => { window.location.hash = `#templates/${template.id}`; }}
	                  >
                    <td>{template.name}</td>
                    <td>{template.subject}</td>
                    <td>{template.category || 'template'}</td>
                    <td><span className="pill">{template.css_body ? 'configured' : 'none'}</span></td>
                    <td>{formatInt((template.html_body || '').length)}</td>
                    <td><RowActionMenu openHref={`#templates/${template.id}`} onDelete={() => deleteTemplateRow(template)} /></td>
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

  const templateWorkspaceModules = [
    {
      key: 'code',
      label: 'Code',
      status: `${formatInt(htmlBody.length)} HTML chars`,
      detail: `${formatInt(cssBody.length)} CSS chars`,
      tone: editorMode === 'edit' ? 'active' : '',
      actionLabel: 'Edit',
      onClick: () => switchTemplateEditorMode('edit'),
      disabled: busy,
    },
    {
      key: 'design',
      label: 'Design',
      status: `${formatInt(designDoc.blocks.length)} block(s)`,
      detail: `${formatInt(designClassNames.length)} class(es)`,
      tone: editorMode === 'design' ? 'active' : '',
      actionLabel: 'Design',
      onClick: () => switchTemplateEditorMode('design'),
      disabled: busy,
    },
    {
      key: 'variables',
      label: 'Variables',
      status: variablesJsonError ? 'JSON error' : `${formatInt(sampleVariableRows.length)} value(s)`,
      detail: variables.length ? `${formatInt(variables.length)} detected` : 'Not inspected',
      tone: variablesJsonError ? 'warn' : sampleVariableRows.length ? 'good' : '',
      actionLabel: 'Refresh',
      onClick: () => { void refreshVariables(true); },
      disabled: busy || Boolean(variablesJsonError),
    },
    {
      key: 'preview',
      label: 'Preview',
      status: previewFreshness === 'current' ? 'Current' : previewFreshness === 'stale' ? 'Stale' : 'Not rendered',
      detail: previewSubject || 'No rendered subject',
      tone: editorMode === 'preview' ? 'active' : previewFreshness === 'current' ? 'good' : 'warn',
      actionLabel: 'Preview',
      onClick: () => { void previewTemplate(); },
      disabled: busy,
    },
    {
      key: 'css',
      label: 'CSS',
      status: missingCssClasses.length ? `${formatInt(missingCssClasses.length)} missing` : `${formatInt(cssClassCoverage.length)} covered`,
      detail: `${formatInt(designLinkedCssClassCount)} design linked`,
      tone: missingCssClasses.length ? 'warn' : cssClassCoverage.length ? 'good' : '',
      actionLabel: missingCssClasses.length ? 'Fix CSS' : 'Open',
      onClick: openCssGapTools,
      disabled: busy,
    },
    {
      key: 'ai',
      label: 'AI',
      status: pendingAiDraft ? 'Draft ready' : `${formatInt(aiRecommendations.length)} suggestion(s)`,
      detail: appliedAiDraftLabel ? `Applied ${appliedAiDraftLabel}` : aiInstructionMode,
      tone: pendingAiDraft || aiRecommendations.length || appliedAiDraftLabel ? 'good' : '',
      actionLabel: 'Feedback',
      onClick: () => setTemplateFeedbackOpen(true),
      disabled: busy,
    },
  ];
  const templateTriageAction = !name.trim()
    ? {
      tone: 'warn',
      title: 'Name template',
      detail: 'Add a clear template name before saving, versioning, or campaign handoff.',
      actionLabel: 'Review Setup',
      run: () => setStatus('Add a template name before saving.'),
      disabled: busy,
    }
    : !subject.trim()
      ? {
        tone: 'warn',
        title: 'Add subject line',
        detail: 'Campaign sends need a subject before preview, test send, or launch.',
        actionLabel: 'Review Setup',
        run: () => setStatus('Add a subject line before preview or save.'),
        disabled: busy,
      }
      : !htmlBody.trim()
        ? {
          tone: 'warn',
          title: 'Add template content',
          detail: 'HTML/Jinja content is required before preview, variable inspection, or campaign use.',
          actionLabel: 'Open Editor',
          run: () => switchTemplateEditorMode('edit'),
          disabled: busy,
        }
        : variablesJsonError
          ? {
            tone: 'warn',
            title: 'Fix sample JSON',
            detail: 'Sample variables must be valid JSON before preview and variable inspection can run.',
            actionLabel: 'Review Variables',
            run: () => setStatus('Fix sample variable JSON before previewing.'),
            disabled: busy,
          }
          : missingCssClasses.length
            ? {
              tone: 'warn',
              title: 'Create missing CSS',
              detail: `${formatInt(missingCssClasses.length)} detected class rule(s) need CSS coverage before final preview.`,
              actionLabel: 'Create Missing Rules',
              run: openCssGapTools,
              disabled: busy,
            }
            : previewFreshness !== 'current'
              ? {
                tone: 'warn',
                title: 'Render current preview',
                detail: 'Preview with sample variables before saving, version review, or campaign handoff.',
                actionLabel: 'Preview',
                run: previewTemplate,
                disabled: busy,
              }
              : pendingAiDraft
                ? {
                  tone: 'warn',
                  title: 'Review pending AI draft',
                  detail: 'Preview, apply, or discard the pending AI draft before requesting another change.',
                  actionLabel: 'Preview Draft',
                  run: () => { void previewAiDraft(pendingAiDraft); },
                  disabled: busy,
                }
                : hasUnsavedTemplateChanges
                  ? {
                    tone: 'warn',
                    title: 'Save template changes',
                    detail: 'Preview is current; save changes to create the latest persisted version.',
                    actionLabel: 'Save Changes',
                    run: saveTemplate,
                    disabled: busy,
                  }
                  : {
                    tone: 'good',
                    title: 'Template ready',
                    detail: 'Setup, content, CSS, preview, saved state, and version history are ready for campaign use.',
                    actionLabel: 'Open Campaigns',
                    run: () => { window.location.hash = '#campaigns'; },
                    disabled: busy,
                  };
  const templateTriageItems = [
    {
      label: 'Saved state',
      value: hasUnsavedTemplateChanges ? 'Unsaved' : isPersistedTemplate ? 'Saved' : 'Draft',
      detail: isPersistedTemplate ? `${formatInt(templateVersions.length)} version(s)` : 'Create template to start history',
      tone: hasUnsavedTemplateChanges || isCreatingTemplate ? 'warn' : 'good',
    },
    {
      label: 'Preview',
      value: previewFreshness === 'current' ? 'Current' : previewFreshness === 'stale' ? 'Stale' : 'Missing',
      detail: previewSubject || previewStatusText,
      tone: previewFreshness === 'current' ? 'good' : 'warn',
    },
    {
      label: 'Variables',
      value: variablesJsonError ? 'JSON error' : formatInt(variables.length),
      detail: variablesJsonError || `${formatInt(sampleVariableRows.length)} sample value(s)`,
      tone: variablesJsonError ? 'warn' : variables.length || sampleVariableRows.length ? 'good' : 'warn',
    },
    {
      label: 'CSS coverage',
      value: missingCssClasses.length ? `${formatInt(missingCssClasses.length)} gap(s)` : 'Ready',
      detail: `${formatInt(cssClassCoverage.length)} detected class(es)`,
      tone: missingCssClasses.length ? 'warn' : 'good',
    },
    {
      label: 'AI review',
      value: pendingAiDraft ? 'Draft' : aiRecommendations.length ? formatInt(aiRecommendations.length) : appliedAiDraftLabel ? 'Applied' : 'Idle',
      detail: pendingAiDraft ? 'Pending draft needs review' : appliedAiDraftLabel || 'AI suggestions optional',
      tone: pendingAiDraft || appliedAiDraftLabel ? 'warn' : aiRecommendations.length ? 'good' : 'warn',
    },
  ];
  const templateFoundationItems = [
    {
      label: 'Render engine',
      value: templateRenderResult?.ok ? 'Ready' : previewFreshness === 'current' ? 'Rendered' : 'Gap',
      detail: templateRenderResult?.ok
        ? 'Latest Jinja render completed with sample variables.'
        : 'Rendering complex Jinja and CSS-safe HTML remains the contract to validate before launch.',
      tone: templateRenderResult?.ok || previewFreshness === 'current' ? 'good' : 'warn',
    },
    {
      label: 'Variable schema',
      value: variablesJsonError ? 'Invalid' : variables.length ? `${formatInt(variables.length)} vars` : 'Gap',
      detail: variablesJsonError
        ? 'Sample JSON must be valid before variable contracts are trusted.'
        : variables.length
          ? 'Detected variables can be matched against samples and campaign data.'
          : 'Template variables need schema mapping to audience and client entity fields.',
      tone: variablesJsonError || !variables.length ? 'warn' : 'good',
    },
    {
      label: 'Compliance guardrails',
      value: htmlBody.includes('unsubscribe') ? 'Present' : 'Gap',
      detail: htmlBody.includes('unsubscribe')
        ? 'Unsubscribe content is present in the template body.'
        : 'Footer, unsubscribe, and brand compliance checks should be enforced before send.',
      tone: htmlBody.includes('unsubscribe') ? 'good' : 'warn',
    },
    {
      label: 'Version contract',
      value: templateVersions.length ? `${formatInt(templateVersions.length)} versions` : 'Gap',
      detail: templateVersions.length
        ? 'Version history is available for review and rollback.'
        : 'Save and version templates before campaign handoff or AI-assisted publishing.',
      tone: templateVersions.length ? 'good' : 'warn',
    },
  ];
  const templateReadyStepCount = templateSteps.filter((step) => step.ready).length;
  const templateTriageWarnCount = templateTriageItems.filter((item) => item.tone === 'warn').length;
  const templateFoundationWarnCount = templateFoundationItems.filter((item) => item.tone === 'warn').length;
  const templateWorkspaceWarnCount = templateWorkspaceModules.filter((module) => module.tone === 'warn').length;

  return (
    <section className="page-grid">
      <section className="panel full-span campaign-workbench">
        <details className="template-preflight-shell" open>
          <summary>
            <span>Template Controls</span>
            <strong>{selectedTemplate ? selectedTemplate.name : 'Create Template'}</strong>
            <small>{templateTriageAction.title} | {busy ? 'Working' : hasUnsavedTemplateChanges ? 'Unsaved changes' : 'Ready'}</small>
          </summary>
          <div className="template-preflight-content">
        <div className="panel-head">
          <div>
            <h2>{selectedTemplate ? selectedTemplate.name : 'Create Template'}</h2>
            <span className="muted">Edit HTML/Jinja, render previews, and review AI drafts before applying them.</span>
          </div>
          <div className="button-row">
            <a href="#templates">Back to templates</a>
          </div>
        </div>
        <div className="campaign-action-bar template-action-bar">
          <div>
            <strong>Template</strong>
            <button className="primary" onClick={saveTemplate} disabled={busy || (!isCreatingTemplate && !hasUnsavedTemplateChanges)}>{isCreatingTemplate ? 'Create Template' : 'Save Changes'}</button>
            <button className="ghost" onClick={cancelTemplateChanges} disabled={busy || (!isCreatingTemplate && !hasUnsavedTemplateChanges)}>{isCreatingTemplate ? 'Cancel Draft' : 'Revert Changes'}</button>
            <span className={hasUnsavedTemplateChanges ? 'edit-state-pill dirty' : 'edit-state-pill'}>{hasUnsavedTemplateChanges ? 'Unsaved changes' : 'Saved'}</span>
          </div>
          <div>
            <strong>AI Assist</strong>
            {isCreatingTemplate ? (
              <button className="ghost" onClick={draftWithAi} disabled={busy}>Draft with AI</button>
            ) : (
              <>
                <button className="ghost" onClick={() => applyAiEdit()} disabled={busy || !aiInstruction.trim()}>Review AI Edit</button>
                <button className="ghost" onClick={loadAiRecommendations} disabled={busy}>AI Suggestions</button>
              </>
            )}
          </div>
          <div>
            <strong>Render State</strong>
            <span className="muted">{previewStatusText}</span>
          </div>
        </div>
        <details className="template-collapsible-row template-workflow-collapse">
          <summary>
            <span>Workflow Guide</span>
            <strong>{formatInt(templateReadyStepCount)} / {formatInt(templateSteps.length)} ready</strong>
            <small>{templateSteps.find((step) => !step.ready)?.detail || 'Setup, subject, content, variables, and preview are ready.'}</small>
          </summary>
          <section className="campaign-flow">
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
        </details>
        <details className={`template-collapsible-row template-guidance-collapse ${templateTriageAction.tone}`}>
          <summary>
            <span>Readiness and Foundations</span>
            <strong>{templateTriageAction.title}</strong>
            <small>{formatInt(templateTriageWarnCount)} readiness issue(s), {formatInt(templateFoundationWarnCount)} foundation gap(s)</small>
          </summary>
          <section className={`template-triage-panel ${templateTriageAction.tone}`}>
            <div className="template-triage-head">
              <div>
                <span>Template triage</span>
                <strong>{templateTriageAction.title}</strong>
                <small>{templateTriageAction.detail}</small>
              </div>
              <button className={templateTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={templateTriageAction.run} disabled={templateTriageAction.disabled}>{templateTriageAction.actionLabel}</button>
            </div>
            <div className="template-triage-grid">
              {templateTriageItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
          <section className="template-foundation-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Template Foundations</h3>
                <span className="muted">Render engine, variable schema, compliance guardrails, and version readiness.</span>
              </div>
              <a href="#campaigns">Open Campaigns</a>
            </div>
            <div className="template-foundation-grid">
              {templateFoundationItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
        </details>
        <details className="template-collapsible-row template-module-collapse">
          <summary>
            <span>Workspace Modules</span>
            <strong>{editorMode === 'edit' ? 'Code' : editorMode === 'design' ? 'Design' : 'Preview'} mode</strong>
            <small>{formatInt(templateWorkspaceWarnCount)} module issue(s); mode controls remain in the editor.</small>
          </summary>
          <section className="template-workspace-map" aria-label="Template workspace modules">
            {templateWorkspaceModules.map((module) => (
              <article className={`${module.tone} ${module.key === editorMode ? 'active' : ''}`} key={module.key}>
                <div>
                  <span>{module.label}</span>
                  <strong>{module.status}</strong>
                  <small>{module.detail}</small>
                </div>
                <button className="ghost" type="button" onClick={module.onClick} disabled={module.disabled}>{module.actionLabel}</button>
              </article>
            ))}
          </section>
        </details>
        <details className={`template-collapsible-row template-status-collapse ${status.startsWith('Error:') ? 'warn' : ''}`} open>
          <summary>
            <span>Status Messages</span>
            <strong>{busy ? 'Working' : status.startsWith('Error:') ? 'Needs attention' : hasUnsavedTemplateChanges ? 'Unsaved changes' : 'Ready'}</strong>
            <small>{status}</small>
          </summary>
          <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
            <strong>{busy ? 'Working' : 'Status'}</strong>
            <span>{status}</span>
            {variables.length ? <small>{variables.map((item) => item.name).join(', ')}</small> : null}
          </div>
          {appliedAiDraftLabel ? (
            <div className="operation-banner ai-unsaved-banner">
              <strong>Unsaved AI edit</strong>
              <span>Applied draft from {appliedAiDraftLabel}. Save changes to persist this template version, or revert changes to reload from the database.</span>
            </div>
          ) : null}
          {hasUnsavedTemplateChanges && !appliedAiDraftLabel ? (
            <div className="operation-banner unsaved-template-banner">
              <strong>Unsaved changes</strong>
              <span>The editor differs from the last saved template. Changes are autosaved locally; save to persist them, or revert to reload from the database.</span>
            </div>
          ) : null}
          {localTemplateDraft && !hasUnsavedTemplateChanges ? (
            <div className="operation-banner local-draft-banner">
              <strong>Local draft available</strong>
              <span>Autosaved {new Date(localTemplateDraft.updatedAt).toLocaleString()}. Restore it or revert to keep the database version.</span>
              <button className="ghost" type="button" onClick={restoreTemplateLocalDraft} disabled={busy}>Restore Local Draft</button>
              <button className="ghost" type="button" onClick={() => clearTemplateLocalDraft()} disabled={busy}>Discard Local Draft</button>
            </div>
          ) : null}
        </details>
          </div>
        </details>
        {!templateFeedbackOpen ? (
          <div className="pane-restore-row template-feedback-restore-row">
            <span>Feedback hidden</span>
            <button className="pane-toggle-button" type="button" onClick={() => setTemplateFeedbackOpen(true)} title="Show Feedback">+ Feedback</button>
          </div>
        ) : null}
	        <div className={`template-editor-shell ${templateFeedbackOpen ? 'feedback-open' : 'feedback-closed'}`}>
          <section className="template-editor-main">
            <div className="tab-row mode-switch">
              <button className={editorMode === 'edit' ? 'active edit-mode' : 'edit-mode'} onClick={() => switchTemplateEditorMode('edit')}>Edit</button>
              <button className={editorMode === 'design' ? 'active design-mode' : 'design-mode'} onClick={() => switchTemplateEditorMode('design')}>Design</button>
              <button className={`${editorMode === 'preview' ? 'active preview-mode' : 'preview-mode'} ${previewFreshness === 'stale' ? 'needs-refresh' : ''}`} onClick={previewTemplate} disabled={busy}>Preview</button>
            </div>
            {editorMode === 'edit' ? (
              <div className="form-grid template-edit-grid">
                <label>
                  Template name
                  <input value={name} onChange={(event) => setName(event.target.value)} />
	                </label>
	                <label>
	                  Subject
	                  <input value={subject} onChange={(event) => {
	                    setSubject(event.target.value);
	                    markPreviewStale();
	                  }} />
	                </label>
                <div className="wide-field editor-field html-editor-field">
                  <span className="field-title">
                    HTML / Jinja
                    <small>Insert blocks into the editor below</small>
                  </span>
                  <TemplateCodeEditor
                    ref={htmlEditorRef}
                    value={htmlBody}
                    completions={templateEditorCompletions}
                    cssClasses={htmlClassNames}
                    onSave={saveTemplate}
                    onFormat={formatTemplateSource}
                    onSelectionChange={syncHtmlSelectionToCssClass}
	                    onChange={(nextValue) => {
	                      setHtmlBody(nextValue);
	                      markPreviewStale();
	                    }}
                  />
		                  <div className="editor-tool-panel">
		                    <div className="tool-panel-head">
                          <div className="pane-title-row">
                            <strong>HTML Tools</strong>
		                        <button className="pane-toggle-button" type="button" onClick={() => setHtmlToolsOpen((current) => !current)} title={htmlToolsOpen ? 'Hide HTML Tools' : 'Show HTML Tools'}>{htmlToolsOpen ? '-' : '+'}</button>
                          </div>
		                      <span>{classableHtmlTagCount ? `${formatInt(classableHtmlTagCount)} element(s) need classes` : 'These controls insert formatted HTML/Jinja at the cursor.'}</span>
		                    </div>
                    {htmlToolsOpen ? (
                      <div className="insert-tool-groups">
                        <div className="insert-tool-group">
                          <span>Workflow</span>
                          <div className="block-button-grid inline-block-actions">
                            <button className="block-structure" type="button" onClick={formatTemplateSource} disabled={busy}>Format Source</button>
                            <button className="block-structure" type="button" onClick={addMissingHtmlClasses} disabled={busy || !classableHtmlTagCount}>Add Classes</button>
                            <button className="block-structure" type="button" onClick={addMissingHtmlClassesAndCss} disabled={busy || (!classableHtmlTagCount && !missingCssClasses.length)}>Class + CSS</button>
                          </div>
                        </div>
                        <div className="insert-tool-group">
                          <span>Structure</span>
                          <div className="block-button-grid inline-block-actions">
                            <button className="block-structure" type="button" onClick={() => insertHtmlBlock('container')} disabled={busy}>Container</button>
                            <button className="block-structure" type="button" onClick={() => insertHtmlBlock('twoColumn')} disabled={busy}>2 Columns</button>
                            <button className="block-structure" type="button" onClick={() => insertHtmlBlock('divider')} disabled={busy}>Divider</button>
                            <button className="block-structure" type="button" onClick={() => insertHtmlBlock('spacer')} disabled={busy}>Spacer</button>
                          </div>
                        </div>
                        <div className="insert-tool-group">
                          <span>Content</span>
                          <div className="block-button-grid inline-block-actions">
                            <button className="block-content" type="button" onClick={() => insertHtmlBlock('hero')} disabled={busy}>Hero CTA</button>
                            <button className="block-content" type="button" onClick={() => insertHtmlBlock('heading')} disabled={busy}>Heading</button>
                            <button className="block-content" type="button" onClick={() => insertHtmlBlock('paragraph')} disabled={busy}>Paragraph</button>
                            <button className="block-content" type="button" onClick={() => insertHtmlBlock('quote')} disabled={busy}>Quote</button>
                          </div>
                        </div>
                        <div className="insert-tool-group">
                          <span>Media and logic</span>
                          <div className="block-button-grid inline-block-actions">
                            <button className="block-media" type="button" onClick={() => insertHtmlBlock('image')} disabled={busy}>Image</button>
                            <button className="block-action" type="button" onClick={() => insertHtmlBlock('button')} disabled={busy}>Button</button>
                            <button className="block-dynamic" type="button" onClick={() => insertHtmlBlock('list')} disabled={busy}>Dynamic List</button>
                            <button className="block-dynamic" type="button" onClick={() => insertHtmlBlock('conditional')} disabled={busy}>If / Else</button>
                            <button className="block-compliance" type="button" onClick={() => insertHtmlBlock('compliance')} disabled={busy}>Compliance</button>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
		                <div className="editor-field sample-editor-field">
	                  <span className="field-title">
	                    Sample variables JSON
	                    <small>{variablesJsonError ? 'Fix JSON before previewing' : 'Field editor updates this JSON'}</small>
	                  </span>
                    <div className="sample-variable-health" aria-label="Sample variable health">
                      <div className={variablesJsonError ? 'warn' : 'good'}>
                        <span>JSON</span>
                        <strong>{variablesJsonError ? 'Invalid' : 'Valid'}</strong>
                        <small>{variablesJsonError || `${formatInt(jsonSampleVariableCount)} value(s)`}</small>
                      </div>
                      <div className={variables.length ? 'good' : 'warn'}>
                        <span>Detected</span>
                        <strong>{formatInt(variables.length)}</strong>
                        <small>{variables.length ? 'Preview-aware variables' : 'Run preview or refresh'}</small>
                      </div>
                      <div className={nativeSampleVariableCount ? 'good' : ''}>
                        <span>Native</span>
                        <strong>{formatInt(nativeSampleVariableCount)}</strong>
                        <small>{sampleVariableRows.length ? `${formatInt(sampleVariableRows.length)} editable row(s)` : 'No rows yet'}</small>
                      </div>
                      <div className={previewFreshness === 'current' ? 'good' : 'warn'}>
                        <span>Preview</span>
                        <strong>{previewFreshness === 'current' ? 'Current' : previewFreshness === 'stale' ? 'Stale' : 'Empty'}</strong>
                        <small>{previewStatusText}</small>
                      </div>
                    </div>
	                  <textarea className={variablesJsonError ? 'field-error' : ''} value={variablesJson} onChange={(event) => {
	                    setVariablesJson(event.target.value);
	                    markPreviewStale();
	                  }} rows={16} />
	                  <div className="sample-json-actions">
	                    <button className="ghost" type="button" onClick={formatVariablesJson} disabled={busy || Boolean(variablesJsonError)}>Format JSON</button>
	                    <span className={variablesJsonError ? 'json-status warn' : 'json-status'}>
	                      {variablesJsonError || `${formatInt(Object.keys(sampleVariables).length)} sample value(s) ready`}
	                    </span>
	                  </div>
	                  {sampleVariableRows.length ? (
                    <div className="variable-editor-list inline-variable-editor">
                      {sampleVariableRows.map((item) => (
                        <label key={item.name}>
                          <span>
                            <strong>{item.name}</strong>
                            <em>{item.source}</em>
                          </span>
                          <input
                            value={formatSampleInput(item.value)}
                            onChange={(event) => updateSampleVariable(item.name, event.target.value)}
                          />
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">Click Preview to detect variables and create editable sample data.</p>
                  )}
                </div>
                <div className="wide-field editor-field css-editor-field" ref={cssEditorSectionRef}>
                  <span className="field-title">
                    CSS
                    <small>Select a class from the HTML, adjust controls, then update that CSS rule</small>
                  </span>
	                  <textarea ref={cssEditorRef} value={cssBody} onSelect={syncCssSelectionToClass} onClick={syncCssSelectionToClass} onKeyUp={syncCssSelectionToClass} onChange={(event) => {
	                    setCssBody(event.target.value);
	                    markPreviewStale();
	                  }} rows={7} />
		                  <div className="editor-tool-panel">
		                    <div className="tool-panel-head">
                          <div className="pane-title-row">
                            <strong>CSS Helper</strong>
		                        <button className="pane-toggle-button" type="button" onClick={() => setCssToolsOpen((current) => !current)} title={cssToolsOpen ? 'Hide CSS Helper' : 'Show CSS Helper'}>{cssToolsOpen ? '-' : '+'}</button>
                          </div>
		                      <span>{missingCssClasses.length ? `${formatInt(missingCssClasses.length)} missing CSS rule(s)` : 'Select an HTML class, tune controls, then update CSS.'}</span>
		                    </div>
	                    {cssToolsOpen ? (
	                      <>
			                    <div className="css-tool-actions">
			                      <button className="ghost" type="button" onClick={formatCssEditor} disabled={busy || !cssBody.trim()}>Format CSS</button>
	                              <button className="ghost" type="button" onClick={() => returnToDesignBlockForClass()} disabled={busy || !selectedCssClass || !selectedCssDesignBlock}>Back to Design</button>
			                      <span>{selectedCssClass ? `Working on .${selectedCssClass}` : 'Global CSS mode'}</span>
			                    </div>
                              {selectedCssClass ? (
                                <div className={`css-design-link ${selectedCssDesignBlock ? 'linked' : 'unlinked'}`}>
                                  <span>{selectedCssDesignBlock ? 'Linked Design Block' : 'No Design Block Link'}</span>
                                  <strong>{selectedCssDesignBlock ? designTreeMeta(selectedCssDesignBlock).label : `.${selectedCssClass}`}</strong>
                                  <small>{selectedCssDesignBlock ? 'Back to Design will reselect this block.' : 'This class exists in HTML/CSS but not the current Design block model.'}</small>
                                </div>
                              ) : null}
                              <div className={`css-next-action ${cssHelperNextAction.tone}`}>
                                <div>
                                  <span>Next CSS action</span>
                                  <strong>{cssHelperNextAction.title}</strong>
                                  <small>{cssHelperNextAction.detail}</small>
                                </div>
                                <button className={cssHelperNextAction.tone === 'good' ? 'ghost' : 'primary'} type="button" onClick={cssHelperNextAction.run} disabled={busy}>{cssHelperNextAction.actionLabel}</button>
                              </div>
		                    {selectedCssClass ? (
	                      <div className={selectedCssRule ? 'selected-css-rule has-rule' : 'selected-css-rule missing-rule'}>
	                        <div>
	                          <strong>.{selectedCssClass}</strong>
	                          <span>{selectedCssRule ? `Existing ${selectedCssCoverage?.kind || cssClassKind} rule loaded` : `Missing ${selectedCssCoverage?.kind || cssClassKind} rule`}</span>
	                        </div>
	                        <button className="ghost" type="button" onClick={applyCssPreset} disabled={busy}>{selectedCssRule ? 'Update Rule' : 'Create Rule'}</button>
	                      </div>
	                    ) : null}
	                    <div className="css-helper-grid inline-css-helper">
                    <label>
                      HTML class
                      <select value={selectedCssClass} onChange={(event) => selectCssClass(event.target.value)}>
	                        <option value="">Global starter CSS</option>
	                        {htmlClassNames.map((className) => (
	                          <option value={className} key={className}>.{className} - {designBlockForClass(className) ? 'design' : 'code only'}</option>
	                        ))}
	                      </select>
                    </label>
                    <label>
                      Style type
                      <select value={cssClassKind} onChange={(event) => setCssClassKind(event.target.value as typeof cssClassKind)}>
                        <option value="container">Container</option>
                        <option value="section">Section/card</option>
                        <option value="button">Button/link</option>
                        <option value="text">Text</option>
                        <option value="image">Image</option>
                      </select>
                    </label>
                    <label className={visibleCssControls.font ? '' : 'css-control-hidden'}>
                      Font
                      <select value={cssPreset.font} onChange={(event) => setCssPreset((current) => ({ ...current, font: event.target.value }))}>
                        <option value="Arial, Helvetica, sans-serif">Arial</option>
                        <option value="Georgia, 'Times New Roman', serif">Georgia</option>
                        <option value="'Trebuchet MS', Arial, sans-serif">Trebuchet</option>
                        <option value="Verdana, Geneva, sans-serif">Verdana</option>
                      </select>
                    </label>
                    {cssColorControl('Background', 'background', visibleCssControls.background)}
                    {cssColorControl('Text', 'text', visibleCssControls.text)}
                    {cssColorControl('Accent', 'accent', visibleCssControls.accent)}
                    <label className={visibleCssControls.width ? '' : 'css-control-hidden'}>
                      Width
                      <input type="number" min="480" max="760" step="20" value={cssPreset.container} onChange={(event) => setCssPreset((current) => ({ ...current, container: event.target.value }))} />
                    </label>
                    <label className={visibleCssControls.padding ? '' : 'css-control-hidden'}>
                      Padding
                      <input type="number" min="12" max="48" step="2" value={cssPreset.padding} onChange={(event) => setCssPreset((current) => ({ ...current, padding: event.target.value }))} />
                    </label>
                    <label className={visibleCssControls.radius ? '' : 'css-control-hidden'}>
                      Radius
                      <input type="number" min="0" max="24" step="2" value={cssPreset.radius} onChange={(event) => setCssPreset((current) => ({ ...current, radius: event.target.value }))} />
                    </label>
	                    <button className="ghost" type="button" onClick={applyCssPreset} disabled={busy}>{selectedCssClass ? (selectedCssRule ? 'Update Class CSS' : 'Create Class CSS') : 'Generate CSS'}</button>
	                    <button className="ghost" type="button" onClick={() => syncCssControlsFromRule()} disabled={busy || !selectedCssClass}>Load From CSS</button>
	                    </div>
	                      </>
	                    ) : null}
	                  </div>
	                  <p className="muted css-kind-hint">{cssClassKindHelp}</p>
	                  {selectedCssClass ? <p className="muted css-kind-hint">Selected .{selectedCssClass}. Use the controls above to {selectedCssRule ? 'update' : 'create'} its CSS rule.</p> : null}
                  {cssClassCoverage.length ? (
                    <div className="css-class-coverage">
	                      <div className="coverage-summary">
	                        <strong>HTML class coverage</strong>
	                        <span>
                            {missingCssClasses.length ? `${formatInt(missingCssClasses.length)} missing CSS rules` : 'All detected classes have rules'}
                            {` · ${formatInt(designLinkedCssClassCount)} design · ${formatInt(codeOnlyCssClassCount)} code only`}
                          </span>
	                      </div>
	                      <div className="coverage-chip-list">
	                        {cssClassCoverage.map((item) => {
                            const linkedBlock = designBlockForClass(item.name);
                            return (
	                            <button
	                              type="button"
		                              className={`${item.hasRule ? 'has-rule' : 'missing-rule'} ${linkedBlock ? 'design-linked' : 'code-only'} ${item.name === selectedCssClass ? 'selected' : ''}`}
	                              key={item.name}
	                              onClick={() => selectCssClass(item.name)}
	                            >
	                              .{item.name}
	                              <span>{item.hasRule ? `styled ${item.kind}` : `missing ${item.kind}`}</span>
                                <em>{linkedBlock ? 'design' : 'code only'}</em>
	                            </button>
                            );
                          })}
	                      </div>
                      <button className="ghost" type="button" onClick={scaffoldMissingCssClasses} disabled={busy || !missingCssClasses.length}>Create Missing Rules</button>
                    </div>
                  ) : (
                    <p className="muted css-coverage-empty">Add class attributes in HTML to manage class CSS here.</p>
                  )}
                </div>
              </div>
	            ) : editorMode === 'design' ? (
	              <div className="design-builder-shell">
	                <div className="design-builder-toolbar">
	                  <div>
	                    <strong>Design Canvas</strong>
	                    <span>{formatInt(designDoc.blocks.length)} block(s), {formatInt(designClassNames.length)} CSS class(es). Use the canvas for selection and the inspector for editing.</span>
		                  </div>
				                  <div className="button-row">
				                    <button className="ghost" type="button" onClick={undoDesignChange} disabled={busy || !designUndoStack.length}>Undo</button>
				                    <button className="ghost" type="button" onClick={redoDesignChange} disabled={busy || !designRedoStack.length}>Redo</button>
			                    {designPaletteBlockTypes.map((type) => (
	                      <button
                          className={`ghost design-palette-chip ${draggedPaletteBlockType === type ? 'dragging' : ''}`}
                          type="button"
                          key={type}
                          draggable={!busy}
                          onClick={() => addDesignBlock(type)}
	                          title={`Drag ${designBlockTypeLabel(type)} onto the canvas`}
                          onDragStart={(event) => {
                            setDraggedPaletteBlockType(type);
                            event.dataTransfer.effectAllowed = 'copy';
                            event.dataTransfer.setData('text/plain', `new:${type}`);
                          }}
                          onDragEnd={() => setDraggedPaletteBlockType('')}
                          disabled={busy}
                        >
                          {designBlockTypeLabel(type)}
                        </button>
	                    ))}
		                  </div>
			                </div>
                      <div className="design-sync-strip">
                        <div className={designDocEdited ? 'warn' : 'good'}>
                          <strong>{designDocEdited ? 'Sync needed' : 'Design synced'}</strong>
                          <span>{designWorkflowStatus}</span>
                        </div>
                        <div className={missingCssClasses.length ? 'warn' : 'good'}>
                          <strong>{missingCssClasses.length ? 'CSS gaps' : 'CSS covered'}</strong>
                          <span>{missingCssClasses.length ? `${formatInt(missingCssClasses.length)} class rule(s) missing.` : 'Detected design classes have rules.'}</span>
                        </div>
                        <div className={previewFreshness === 'current' ? 'good' : 'warn'}>
                          <strong>{previewFreshness === 'current' ? 'Preview current' : 'Preview needed'}</strong>
                          <span>{previewStatusText}</span>
                        </div>
                        <div className={designImportConfidence.tone}>
                          <strong>{designImportConfidence.title}</strong>
                          <span>{designImportConfidence.detail}</span>
                        </div>
                        <div className="button-row">
                          <button className="ghost" type="button" onClick={importSourceToDesignBlocks} disabled={busy || !htmlBody.trim()}>Import Source</button>
                          <button className={designDocEdited ? 'primary' : 'ghost'} type="button" onClick={syncDesignToCode} disabled={busy || !designDoc.blocks.length}>Sync to Code</button>
                          {missingCssClasses.length ? <button className="ghost" type="button" onClick={openCssGapTools} disabled={busy}>Fix CSS</button> : null}
                          <button className="primary" type="button" onClick={previewTemplate} disabled={busy || !designDoc.blocks.length}>Preview</button>
                        </div>
	                      </div>
                      {(!designHierarchyOpen || !designInspectorOpen) ? (
                        <div className="pane-restore-row" aria-label="Hidden panes">
                          <span>Hidden panes</span>
                          {!designHierarchyOpen ? <button className="pane-toggle-button" type="button" onClick={() => setDesignHierarchyOpen(true)} title="Show Hierarchy">+ Hierarchy</button> : null}
                          {!designInspectorOpen ? <button className="pane-toggle-button" type="button" onClick={() => setDesignInspectorOpen(true)} title="Show Selected Block">+ Selected Block</button> : null}
                        </div>
                      ) : null}
	                      <div className={`design-next-action ${designNextAction.tone}`}>
                        <div>
                          <strong>{designNextAction.title}</strong>
                          <span>{designNextAction.detail}</span>
                        </div>
                        {designNextAction.action === 'sync' ? (
                          <button className="primary" type="button" onClick={syncDesignToCode} disabled={busy || !designDoc.blocks.length}>Sync Now</button>
                        ) : designNextAction.action === 'css' ? (
                          <button className="ghost" type="button" onClick={openCssGapTools} disabled={busy}>Open CSS Tools</button>
                        ) : designNextAction.action === 'preview' ? (
                          <button className="primary" type="button" onClick={previewTemplate} disabled={busy || !designDoc.blocks.length}>Preview Now</button>
                        ) : designNextAction.action === 'save' ? (
                          <button className="primary" type="button" onClick={saveTemplate} disabled={busy || (!isCreatingTemplate && !hasUnsavedTemplateChanges)}>Save Template</button>
                        ) : null}
                      </div>
			                {designDoc.blocks.length ? (
	                    <div
                        className={`design-workspace-grid ${designHierarchyOpen ? 'hierarchy-open' : ''} ${designInspectorOpen ? 'inspector-open' : 'inspector-closed'}`}
                        style={designWorkspaceStyle}
                      >
	                      {designHierarchyOpen ? (
	                        <aside className="design-hierarchy-panel" ref={designHierarchyRef}>
                            <div
                              className="design-pane-resizer right"
                              role="separator"
                              aria-label="Resize hierarchy panel"
                              aria-orientation="vertical"
                              tabIndex={0}
                              onPointerDown={(event) => startDesignPaneResize('hierarchy', event)}
                              onKeyDown={(event) => handleDesignPaneResizeKey('hierarchy', event)}
                              onDoubleClick={() => setDesignPaneWidth('hierarchy', 180)}
                            />
	                          <div className="design-hierarchy-head">
	                            <div className="design-canvas-head">
	                              <strong>Hierarchy</strong>
	                              <span>{formatInt(flatDesignBlocks.length)} block(s) across {formatInt(maxDesignTreeDepth)} level(s). Select a row to edit it.</span>
	                            </div>
	                            <div className="design-tree-tools" aria-label="Hierarchy controls">
                                <button className="pane-toggle-button" type="button" onClick={() => setDesignHierarchyOpen(false)} title="Hide Hierarchy">-</button>
	                              <button className="ghost icon-button" type="button" onClick={() => setCollapsedDesignTreeIds([])} title="Expand all">+</button>
                              <button
                                className="ghost icon-button"
                                type="button"
                                onClick={() => setCollapsedDesignTreeIds(flatDesignBlocks.filter((block) => block.children?.length).map((block) => block.id))}
                                title="Collapse all"
                              >
                                -
                              </button>
                            </div>
                          </div>
                          <div className="design-tree" role="tree" aria-label="Template block hierarchy">
                            {renderDesignHierarchy(designDoc.blocks)}
                          </div>
                        </aside>
                      ) : null}
		                      <aside className="design-canvas-panel">
		                        <div className="design-canvas-head">
                              <div className="pane-title-row">
		                            <strong>Live Canvas</strong>
                                <div className="tab-row compact-tabs design-zoom-tabs" aria-label="Canvas zoom">
                                  {DESIGN_CANVAS_ZOOM_OPTIONS.map((option) => (
                                    <button
                                      key={option.value}
                                      className={designCanvasZoom === option.value ? 'active' : ''}
                                      type="button"
                                      onClick={() => setDesignCanvasZoom(option.value)}
                                    >
                                      {option.label}
                                    </button>
                                  ))}
                                </div>
                              </div>
		                          <span>Updates immediately from Design blocks and CSS. Use Preview for final Jinja rendering.</span>
		                        </div>
                            {selectedDesignBlock ? (
                              <>
                                <div className="design-canvas-selection">
                                  <div>
                                    <small>Selected</small>
                                    <strong>{designTreeMeta(selectedDesignBlock).label}</strong>
                                    <span>
                                      {selectedDesignBlockPath.length ? `Level ${selectedDesignBlockPath.length}` : 'Root'}
                                      {selectedDesignBlock.className ? ` · .${selectedDesignBlock.className.split(/\s+/)[0]}` : ''}
                                    </span>
                                  </div>
                                  <div className="button-row">
                                    <button className="ghost" type="button" onClick={() => setDesignInspectorFocusNonce((current) => current + 1)} disabled={busy}>Edit</button>
                                    <button className="ghost" type="button" onClick={() => focusDesignBlockCss(selectedDesignBlock)} disabled={busy}>{selectedDesignBlock.className ? 'Style' : 'Add Class'}</button>
                                  </div>
                                </div>
                              {selectedDesignBlockPath.length > 1 ? (
                                <div className="design-selected-path canvas-path" aria-label="Canvas selected block path">
                                  {selectedDesignBlockPath.map((block, index) => (
                                    <span key={block.id}>
                                      {index > 0 ? <em>/</em> : null}
                                      <button
                                        className={block.id === selectedDesignBlock.id ? 'current' : ''}
                                        type="button"
                                        onClick={() => selectDesignBlock(block.id)}
                                        disabled={block.id === selectedDesignBlock.id}
                                      >
                                        <small>L{index + 1}</small>
                                        {designTreeMeta(block).label}
                                      </button>
                                    </span>
                                  ))}
                                </div>
                              ) : null}
                              </>
                            ) : null}
                            <div className="design-canvas-viewport" style={designCanvasFrameStyle}>
		                          <iframe className="design-canvas-frame" title="Live template design canvas" srcDoc={designCanvasSrcDoc()} />
                            </div>
		                      </aside>
                      {designInspectorOpen ? (
			                      <aside className={`design-inspector-panel ${designInspectorFocusNonce ? 'inspector-prompted' : ''}`} ref={designInspectorRef}>
                            <div
                              className="design-pane-resizer left"
                              role="separator"
                              aria-label="Resize selected block panel"
                              aria-orientation="vertical"
                              tabIndex={0}
                              onPointerDown={(event) => startDesignPaneResize('inspector', event)}
                              onKeyDown={(event) => handleDesignPaneResizeKey('inspector', event)}
                              onDoubleClick={() => setDesignPaneWidth('inspector', 300)}
                            />
		                        {selectedDesignBlock ? (
		                          <>
			                            <div className="design-canvas-head">
                                  <div className="pane-title-row">
			                                <strong>Selected Block</strong>
                                    <button className="pane-toggle-button" type="button" onClick={() => setDesignInspectorOpen(false)} title="Hide Selected Block">-</button>
                                  </div>
			                              <span>
			                                {designBlockTypeLabel(selectedDesignBlock.type)}
	                                {selectedDesignBlockIndex >= 0 ? ` · ${selectedDesignBlockIndex + 1} of ${flatDesignBlocks.length}` : ''}
	                                {selectedDesignBlockParent ? ` · inside ${designBlockTypeLabel(selectedDesignBlockParent.type)}` : ' · root'}
		                                {selectedDesignBlock.className ? ` · .${selectedDesignBlock.className.split(/\s+/)[0]}` : ''}
		                              </span>
		                            </div>
		                            {selectedDesignBlockPath.length > 1 ? (
		                              <div className="design-selected-path" aria-label="Selected block path">
		                                {selectedDesignBlockPath.map((block, index) => (
		                                  <span key={block.id}>
		                                    {index > 0 ? <em>/</em> : null}
		                                    <button
		                                      className={block.id === selectedDesignBlock.id ? 'current' : ''}
		                                      type="button"
		                                      onClick={() => selectDesignBlock(block.id)}
		                                      disabled={block.id === selectedDesignBlock.id}
		                                    >
		                                      <small>L{index + 1}</small>
		                                      {designTreeMeta(block).label}
		                                    </button>
		                                  </span>
		                                ))}
		                              </div>
		                            ) : null}
		                            <div className="design-block-fields inspector-fields">
		                              {renderDesignBlockControls(selectedDesignBlock)}
		                            </div>
	                            <div className="button-row">
		                              <button className="ghost" type="button" onClick={() => focusDesignBlockCss(selectedDesignBlock)} disabled={busy}>{selectedDesignBlock.className ? 'Style' : 'Add Class'}</button>
		                              <button className="ghost" type="button" onClick={() => moveDesignBlock(selectedDesignBlock.id, -1)} disabled={busy || !canMoveDesignBlock(selectedDesignBlock.id, -1)}>Move Up</button>
		                              <button className="ghost" type="button" onClick={() => moveDesignBlock(selectedDesignBlock.id, 1)} disabled={busy || !canMoveDesignBlock(selectedDesignBlock.id, 1)}>Move Down</button>
		                              <button className="ghost" type="button" onClick={() => indentDesignBlock(selectedDesignBlock.id)} disabled={busy || !canIndentDesignBlock(selectedDesignBlock.id)}>Indent</button>
		                              {selectedDesignBlockParent ? <button className="ghost" type="button" onClick={() => outdentDesignBlock(selectedDesignBlock.id)} disabled={busy}>Outdent</button> : null}
		                              {!isDesignContainerBlock(selectedDesignBlock) ? <button className="ghost" type="button" onClick={() => wrapDesignBlockInSection(selectedDesignBlock.id)} disabled={busy}>Wrap in Section</button> : null}
		                              <button className="ghost" type="button" onClick={() => duplicateDesignBlock(selectedDesignBlock.id)} disabled={busy}>Duplicate</button>
	                              {selectedDesignBlockParent ? <button className="ghost" type="button" onClick={() => { reorderDesignBlock(selectedDesignBlock.id, ''); setStatus('Moved block to root.'); }} disabled={busy}>Move to Root</button> : null}
	                              <button className="ghost" type="button" onClick={() => removeDesignBlock(selectedDesignBlock.id)} disabled={busy}>Delete</button>
	                            </div>
	                          </>
	                        ) : (
	                          <div className="empty-state compact-empty">
	                            <strong>No block selected</strong>
		                            <p>Select a block on the canvas or hierarchy tree to edit it.</p>
	                          </div>
		                        )}
		                      </aside>
                      ) : null}
		                    </div>
	                ) : (
	                  <div
                      className={`empty-state design-empty-dropzone ${draggedPaletteBlockType ? 'active' : ''}`}
                      onDragOver={(event) => {
                        event.preventDefault();
                        event.dataTransfer.dropEffect = 'copy';
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        const source = event.dataTransfer.getData('text/plain');
                        if (source.startsWith('new:')) addDesignBlock(source.slice(4));
                        setDraggedPaletteBlockType('');
                      }}
                    >
	                    <strong>No design blocks yet</strong>
	                    <p>Add a block or load an existing block-based template to start designing visually.</p>
	                  </div>
	                )}
		              </div>
	            ) : previewHtml ? (
	              <div className="preview-shell">
	                {previewFreshness === 'stale' ? (
	                  <div className="preview-stale-banner">
	                    <strong>Preview needs refresh</strong>
	                    <span>The editor, CSS, or sample data changed after this preview was rendered.</span>
	                    <button className="ghost" onClick={previewTemplate} disabled={busy}>Refresh Preview</button>
	                  </div>
	                ) : null}
	                <div className="preview-toolbar">
	                  <div>
	                    <span>Subject</span>
	                    <strong>{previewSubject || subject}</strong>
	                    <div className="preview-meta-row">
	                      <span className={previewFreshness === 'current' ? 'preview-meta good' : 'preview-meta warn'}>{previewFreshness === 'current' ? 'Current' : 'Stale'}</span>
	                      <span className="preview-meta">{previewViewport}</span>
	                      <span className="preview-meta">{formatInt(variables.length)} variable(s)</span>
	                      <span className={missingCssClasses.length ? 'preview-meta warn' : 'preview-meta good'}>{missingCssClasses.length ? `${formatInt(missingCssClasses.length)} CSS gap(s)` : 'CSS covered'}</span>
	                    </div>
	                  </div>
                  <div className="tab-row compact-tabs">
                    <button className={previewViewport === 'desktop' ? 'active' : ''} onClick={() => setPreviewViewport('desktop')}>Desktop</button>
                    <button className={previewViewport === 'mobile' ? 'active' : ''} onClick={() => setPreviewViewport('mobile')}>Mobile</button>
                  </div>
                </div>
                <iframe className={`email-preview ${previewViewport === 'mobile' ? 'mobile-preview' : ''}`} title="Template preview" srcDoc={previewHtml} />
              </div>
            ) : (
              <div className="empty-state">
                <strong>Preview not rendered</strong>
                <p>Click Preview to refresh variables and render this template with the current sample data.</p>
              </div>
            )}
          </section>
	          {templateFeedbackOpen ? (
	          <aside className="template-side-pane">
	            <div className="tool-panel-head feedback-panel-head">
                <div className="pane-title-row">
                  <div className="pane-title-copy">
	                  <strong>Feedback</strong>
	                  <span>Readiness checks, AI drafts, and recommendations for this template.</span>
                  </div>
                  <button className="pane-toggle-button" type="button" onClick={() => setTemplateFeedbackOpen(false)} title="Hide Feedback">-</button>
                </div>
	            </div>
            <div className="ai-feedback-summary">
              <div className={pendingAiDraft ? 'active' : ''}>
                <strong>{pendingAiDraft ? 'Draft ready' : 'No draft'}</strong>
                <span>{pendingAiDraft ? 'Preview or apply before saving.' : 'Drafts appear after AI edits.'}</span>
              </div>
              <div className={aiRecommendations.length ? 'active' : ''}>
                <strong>{formatInt(aiRecommendations.length)} suggestion(s)</strong>
                <span>{aiRecommendations.length ? 'Review recommended changes.' : 'Load AI suggestions when needed.'}</span>
              </div>
            </div>
            <section className={`ai-next-step ${aiAssistNextStep.tone}`}>
              <div>
                <span>AI next step</span>
                <strong>{aiAssistNextStep.title}</strong>
                <small>{aiAssistNextStep.detail}</small>
              </div>
              <button className={aiAssistNextStep.tone === 'good' ? 'ghost' : 'primary'} type="button" onClick={aiAssistNextStep.run} disabled={busy || (aiAssistNextStep.actionLabel === 'Review AI Edit' && !aiInstruction.trim())}>{aiAssistNextStep.actionLabel}</button>
            </section>
            {templateRenderResult ? (
              <section className={`template-render-result ${templateRenderResult.ok ? 'good' : 'warn'}`}>
                <div>
                  <span>Latest render</span>
                  <strong>{templateRenderResult.label}</strong>
                  <small>{templateRenderResult.subject || 'No subject'}</small>
                </div>
                <div><span>Status</span><strong>{templateRenderResult.ok ? 'Rendered' : 'Review'}</strong></div>
                <div><span>Variables</span><strong>{formatInt(templateRenderResult.variableCount)}</strong></div>
                <div><span>CSS gaps</span><strong>{formatInt(templateRenderResult.cssGapCount)}</strong></div>
                <div><span>Source</span><strong>{templateRenderResult.sourceMode === 'design' ? 'Design' : 'Source'}</strong></div>
                {templateRenderResult.errors.length ? (
                  <p>{templateRenderResult.errors.slice(0, 2).join('; ')}</p>
                ) : (
                  <p>{previewFreshness === 'current' ? 'Preview is current with sample variables.' : previewStatusText}</p>
                )}
                <button className="ghost" type="button" onClick={previewTemplate} disabled={busy}>Refresh Preview</button>
              </section>
            ) : null}
            <section className="workflow-section template-readiness-section">
              <h3>Template Readiness</h3>
              <div className="compact-status-list">
                {liveTemplateGuidance.map((item) => (
                  <div className={item.ready ? 'ready' : 'warn'} key={item.label}>
                    <strong>{item.label}</strong>
                    <span>{item.detail}</span>
                  </div>
                ))}
              </div>
              {missingCssClasses.length ? (
                <div className="readiness-action-card">
                  <strong>CSS coverage needs attention</strong>
                  <span>{missingCssClasses.slice(0, 4).map((className) => `.${className}`).join(', ')}{missingCssClasses.length > 4 ? ` and ${formatInt(missingCssClasses.length - 4)} more` : ''}</span>
                  <div className="button-row">
                    <button className="ghost" type="button" onClick={openCssGapTools} disabled={busy}>Open CSS Tools</button>
                    <button className="primary" type="button" onClick={scaffoldMissingCssClasses} disabled={busy}>Create Missing Rules</button>
                  </div>
                </div>
              ) : null}
            </section>
            {isPersistedTemplate ? (
              <section className="workflow-section template-history-section">
                <h3>Template History</h3>
                {templateVersions.length ? (
                  <div className="template-version-list">
                    {templateVersions.slice(0, 6).map((version) => {
                      const review = versionReview(version);
                      const isReviewing = selectedVersionReviewId === version.id;
                      return (
                        <div className={`${version.is_current ? 'current' : ''} ${isReviewing ? 'reviewing' : ''}`} key={version.id}>
                          <div>
                            <strong>Version {version.version_number}</strong>
                            <span>{version.is_current ? 'Current version' : `${formatInt((version.html_body || '').length)} HTML chars`}</span>
                          </div>
                          <div className="button-row">
                            <button className="ghost" type="button" onClick={() => setSelectedVersionReviewId(isReviewing ? '' : version.id)} disabled={busy}>Review</button>
                            <button className="ghost" type="button" onClick={() => previewTemplateVersion(version)} disabled={busy || !isReviewing}>Preview</button>
                            <button className="ghost" type="button" onClick={() => restoreTemplateVersion(version)} disabled={busy || version.is_current || !isReviewing}>Restore</button>
                          </div>
                          {isReviewing ? (
                            <div className="template-version-compare">
                              <div className={review.subjectChanged ? 'changed' : ''}>
                                <span>Subject</span>
                                <strong>{review.subjectChanged ? 'Changed' : 'Same'}</strong>
                              </div>
                              <div className={review.htmlDelta ? 'changed' : ''}>
                                <span>HTML size</span>
                                <strong>{formatSignedCount(review.htmlDelta)} chars</strong>
                              </div>
                              <div className={review.cssChanged ? 'changed' : ''}>
                                <span>CSS size</span>
                                <strong>{formatSignedCount(review.cssDelta)} chars</strong>
                              </div>
                              <div className={review.documentChanged ? 'changed' : ''}>
                                <span>Design doc</span>
                                <strong>{review.documentChanged ? 'Changed' : 'Same'}</strong>
                              </div>
                              <div className={review.textChanged ? 'changed' : ''}>
                                <span>Text body</span>
                                <strong>{review.textChanged ? 'Present' : 'Empty'}</strong>
                              </div>
                              <div>
                                <span>Restore</span>
                                <strong>{version.is_current ? 'Already current' : 'Creates new version'}</strong>
                              </div>
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-state compact-empty">
                    <strong>No versions loaded</strong>
                    <p>Save this template to create version history.</p>
                  </div>
                )}
              </section>
            ) : null}
            {isPersistedTemplate ? (
              <section className="workflow-section ai-command-section">
                <h3>AI Command Center</h3>
                <div className="ai-request-box">
	                  <div className="ai-preset-row">
	                    {aiInstructionPresets.map((preset) => (
	                      <button className={aiInstructionMode === preset.label ? 'ghost active' : 'ghost'} type="button" key={preset.label} onClick={() => chooseAiInstructionPreset(preset.label, preset.instruction)} disabled={busy}>{preset.label}</button>
	                    ))}
	                  </div>
	                  <textarea value={aiInstruction} onChange={(event) => {
	                    setAiInstruction(event.target.value);
	                    setAiInstructionMode('Custom');
	                  }} rows={4} />
	                  <span className="ai-request-mode">{aiInstructionMode === 'Custom' ? 'Custom AI request' : `${aiInstructionMode} preset selected`}</span>
                  <div className="button-row">
                    <button className="primary" onClick={() => applyAiEdit()} disabled={busy || !aiInstruction.trim()}>Review AI Edit</button>
                    <button className="ghost" onClick={loadAiRecommendations} disabled={busy}>Suggestions</button>
                  </div>
                </div>
              </section>
            ) : null}
            <section className="workflow-section ai-review-section">
              <h3>Pending Draft Review</h3>
              {pendingAiDraft ? (
                <div className="ai-draft-preview">
                  <span className="muted">{pendingAiDraft.provider}/{pendingAiDraft.model}</span>
                  <strong>{pendingAiDraft.subject}</strong>
                  {pendingAiDraftReview ? (
                    <div className="ai-draft-compare-grid">
                      <div>
                        <span>Current subject</span>
                        <strong>{subject || 'No subject'}</strong>
                      </div>
                      <div className={pendingAiDraftReview.subjectChanged ? 'changed' : ''}>
                        <span>Draft subject</span>
                        <strong>{pendingAiDraft.subject || subject || 'No subject'}</strong>
                      </div>
                      <div className={pendingAiDraftReview.htmlDelta ? 'changed' : ''}>
                        <span>HTML size</span>
                        <strong>{formatSignedCount(pendingAiDraftReview.htmlDelta)} chars</strong>
                      </div>
                      <div className={pendingAiDraftReview.cssChanged ? 'changed' : ''}>
                        <span>CSS size</span>
                        <strong>{formatSignedCount(pendingAiDraftReview.cssDelta)} chars</strong>
                      </div>
                      <div>
                        <span>Sample data</span>
                        <strong>{pendingAiDraftVariables.length ? `${formatInt(pendingAiDraftVariables.length)} value(s)` : 'No draft values'}</strong>
                      </div>
                      <div>
                        <span>Status</span>
                        <strong>{pendingAiDraftReview.subjectChanged || pendingAiDraftReview.htmlDelta || pendingAiDraftReview.cssChanged ? 'Changes pending' : 'No structural change'}</strong>
                      </div>
                    </div>
                  ) : null}
                  {pendingAiDraftNotes.length ? (
                    <ul className="ai-draft-notes">
                      {pendingAiDraftNotes.slice(0, 4).map((note) => <li key={note}>{note}</li>)}
                    </ul>
                  ) : null}
                  <span className="ai-draft-source-label">Draft HTML excerpt</span>
                  <pre>{(pendingAiDraft.html_body || '').slice(0, 900)}</pre>
                  <div className="button-row">
                    <button className="ghost" onClick={() => previewAiDraft(pendingAiDraft)} disabled={busy}>Preview Draft</button>
                    <button className="primary" onClick={() => applyAiDraft(pendingAiDraft)} disabled={busy}>Apply Draft</button>
                    <button className="ghost" onClick={() => setPendingAiDraft(null)} disabled={busy}>Discard</button>
                  </div>
                </div>
              ) : (
                <p className="muted">AI drafts and edits appear here for review before they change the editor.</p>
              )}
            </section>
            <section className="workflow-section ai-suggestion-section">
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
              ) : (
                <div className="ai-empty-state">
                  <strong>No suggestions loaded</strong>
                  <span>Use AI Suggestions after previewing to get deliverability, layout, and copy recommendations.</span>
                </div>
	              )}
	            </section>
	          </aside>
            ) : null}
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
  const [deliveryAttempts, setDeliveryAttempts] = useState<DeliveryAttemptRead[]>([]);
  const [providerFeedbackEvents, setProviderFeedbackEvents] = useState<ProviderFeedbackEventRead[]>([]);
  const [providerFeedbackTotal, setProviderFeedbackTotal] = useState(0);
  const [readinessChecks, setReadinessChecks] = useState<ManagedSmtpReadinessCheckRead[]>([]);
  const [readinessCheckTotal, setReadinessCheckTotal] = useState(0);
  const [readinessSummary, setReadinessSummary] = useState<ManagedSmtpReadinessSummaryRead | null>(null);
  const [readinessTrend, setReadinessTrend] = useState<ManagedSmtpReadinessTrendRead | null>(null);
  const [readinessAlerts, setReadinessAlerts] = useState<ManagedSmtpReadinessAlertsRead | null>(null);
  const [readinessNotification, setReadinessNotification] = useState<ManagedSmtpReadinessNotificationRead | null>(null);
  const [managedSmtpDeploymentSummary, setManagedSmtpDeploymentSummary] = useState<ManagedSmtpDeploymentSummaryRead | null>(null);
  const [firstSendReadiness, setFirstSendReadiness] = useState<ManagedSmtpFirstSendRead | null>(null);
  const [readinessFilters, setReadinessFilters] = useState({
    status: '',
    domain: '',
    host: '',
    check_type: '',
  });
  const [feedbackFilters, setFeedbackFilters] = useState({
    provider: '',
    source: '',
    event_name: '',
    email: '',
    provider_message_id: '',
  });
  const [domainPolicies, setDomainPolicies] = useState<DomainDeliveryPolicyRead[]>([]);
  const [selectedDomainPolicyId, setSelectedDomainPolicyId] = useState('');
  const [domainDashboard, setDomainDashboard] = useState<DomainReputationDashboardRead | null>(null);
  const [managedSmtpRouteResolution, setManagedSmtpRouteResolution] = useState<ManagedSmtpRouteResolutionRead | null>(null);
  const [aiDeliverySummary, setAiDeliverySummary] = useState<string[]>([]);
  const [aiDeliveryRecommendations, setAiDeliveryRecommendations] = useState<AIWorkflowAnalysis['recommendations']>([]);
  const [status, setStatus] = useState('Ready to inspect send jobs and delivery records.');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedJobId && sendJobs.length) setSelectedJobId(sendJobs[0].id);
    if (!selectedRecordId && sendRecords.length) setSelectedRecordId(sendRecords[0].id);
  }, [sendJobs, selectedJobId, selectedRecordId, sendRecords]);

  useEffect(() => {
    let active = true;
    fetchJson<ListResponse<DomainDeliveryPolicyRead>>('/api/v1/domain-delivery-policies/list?limit=100&offset=0')
      .then((data) => {
        if (!active) return;
        const items = data.items || [];
        setDomainPolicies(items);
        if (!selectedDomainPolicyId && items.length) setSelectedDomainPolicyId(items[0].id);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [selectedDomainPolicyId]);

  const queuedRecords = countRecordsByStatus(sendRecords, queuedDeliveryStatuses);
  const failedRecords = countRecordsByStatus(sendRecords, failedDeliveryStatuses);
  const deadLetteredRecords = sendRecords.filter((record) => record.status === 'dead_lettered').length;
  const sentRecords = countRecordsByStatus(sendRecords, acceptedDeliveryStatuses);
  const activeJobs = sendJobs.filter((job) => !['completed', 'failed', 'cancelled'].includes(job.status)).length;
  const selectedJob = sendJobs.find((job) => job.id === selectedJobId);
  const selectedRecord = sendRecords.find((record) => record.id === selectedRecordId);
  const selectedDomainPolicy = domainPolicies.find((policy) => policy.id === selectedDomainPolicyId);
  const selectedCampaign = campaigns.find((campaign) => campaign.id === selectedJob?.campaign_id || campaign.id === selectedRecord?.campaign_id);
  const retryPressure = sendRecords.filter((record) => queuedDeliveryStatuses.includes(record.status) && Number(record.attempt_count || 0) > 0).length;
  const blockedRecords = countRecordsByStatus(sendRecords, blockedDeliveryStatuses);
  const queueControlAttempts = deliveryAttempts.filter((attempt) => attempt.route_type === 'queue_control' || ['claim_blocked', 'dead_lettered'].includes(attempt.status));
  const claimBlockedAttempts = deliveryAttempts.filter((attempt) => attempt.status === 'claim_blocked').length;
  const deadLetterAttempts = deliveryAttempts.filter((attempt) => attempt.status === 'dead_lettered').length;
  const providerFootprint = Array.from(new Set(sendRecords.map((record) => providerLabel(record.provider)).filter(Boolean)));
  const providerFeedbackWarningCount = providerFeedbackEvents.filter((event) => ['dsn_bounce', 'bounce', 'complaint', 'tempfail', 'deferred'].includes(event.event_name)).length;
  const readinessWarningCount = readinessSummary
    ? readinessSummary.warning_count + readinessSummary.failed_count
    : readinessChecks.filter((check) => check.status !== 'ok').length;
  const latestReadinessCheck = readinessSummary?.latest_check || readinessChecks[0];
  const latestSuccessfulReadiness = readinessSummary?.latest_success || readinessChecks.find((check) => check.status === 'ok');
  const managedSmtpDeploymentItems = [
    {
      label: 'Provider accounts',
      value: formatInt(managedSmtpDeploymentSummary?.provider_accounts.total || 0),
      detail: managedSmtpDeploymentSummary
        ? `${formatInt(managedSmtpDeploymentSummary.provider_accounts.active)} active, ${formatInt(managedSmtpDeploymentSummary.provider_accounts.pending)} pending`
        : 'Load deployment summary for provider status.',
      tone: managedSmtpDeploymentSummary?.provider_accounts.active ? 'good' : 'warn',
    },
    {
      label: 'MTA nodes',
      value: formatInt(managedSmtpDeploymentSummary?.nodes.total || 0),
      detail: managedSmtpDeploymentSummary
        ? `${formatInt(managedSmtpDeploymentSummary.nodes.active)} active, ${formatInt(managedSmtpDeploymentSummary.nodes.paused)} paused`
        : 'Load deployment summary for node status.',
      tone: managedSmtpDeploymentSummary?.nodes.active ? 'good' : 'warn',
    },
    {
      label: 'IP pools',
      value: formatInt(managedSmtpDeploymentSummary?.ip_pools.total || 0),
      detail: managedSmtpDeploymentSummary
        ? `${formatInt(managedSmtpDeploymentSummary.ip_pools.active)} active, ${formatInt(managedSmtpDeploymentSummary.pool_nodes.active)} active pool node(s)`
        : 'Load deployment summary for pool status.',
      tone: managedSmtpDeploymentSummary?.ip_pools.active ? 'good' : 'warn',
    },
    {
      label: 'Route policies',
      value: formatInt(managedSmtpDeploymentSummary?.managed_smtp_domain_policy_count || 0),
      detail: managedSmtpDeploymentSummary
        ? `${formatInt(managedSmtpDeploymentSummary.managed_smtp_route_count)} managed SMTP route(s)`
        : 'Load deployment summary for route coverage.',
      tone: managedSmtpDeploymentSummary?.managed_smtp_route_count ? 'good' : 'warn',
    },
    {
      label: 'Submission auth',
      value: managedSmtpDeploymentSummary?.submission_credentials_configured ? 'Configured' : 'Missing',
      detail: managedSmtpDeploymentSummary
        ? `TLS ${managedSmtpDeploymentSummary.submission_tls_enabled ? 'enabled' : 'disabled'} for worker-to-MTA submission.`
        : 'Load deployment summary for worker submission credentials.',
      tone: managedSmtpDeploymentSummary?.submission_credentials_configured ? 'good' : 'warn',
    },
  ];
  const firstManagedSmtpNode = managedSmtpDeploymentSummary?.recent_nodes?.[0] || null;
  const firstManagedSmtpProvider = firstManagedSmtpNode?.provider_account || null;
  const port25Approved = firstManagedSmtpProvider?.port25_status === 'approved';
  const rdnsConfigured = firstManagedSmtpProvider?.rdns_status === 'configured';
  const latestReadinessOk = latestReadinessCheck?.status === 'ok';
  const authenticationReady = domainDashboard?.authentication_status === 'verified'
    || domainDashboard?.authentication_status === 'ok';
  const firstSendComplianceHold = selectedDomainPolicy?.metadata_json?.compliance_hold;
  const firstSendComplianceStatus = typeof firstSendComplianceHold === 'object'
    && firstSendComplianceHold !== null
    && 'status' in firstSendComplianceHold
    ? String((firstSendComplianceHold as Record<string, unknown>).status)
    : 'clear';
  const fallbackFirstSendReadinessItems = [
    {
      label: 'AWS port 25',
      value: firstManagedSmtpProvider?.port25_status || 'Pending',
      detail: port25Approved
        ? 'Outbound direct-MX delivery is approved for the selected provider account.'
        : 'Seed send remains blocked until the provider removes outbound TCP 25 limits.',
      tone: port25Approved ? 'good' : 'warn',
    },
    {
      label: 'PTR/rDNS',
      value: firstManagedSmtpProvider?.rdns_status || 'Not loaded',
      detail: rdnsConfigured
        ? 'Reverse DNS is configured for the MTA public IP.'
        : 'Load deployment summary and confirm reverse DNS before first send.',
      tone: rdnsConfigured ? 'good' : 'warn',
    },
    {
      label: 'Submission auth',
      value: managedSmtpDeploymentSummary?.submission_credentials_configured ? 'Ready' : 'Missing',
      detail: managedSmtpDeploymentSummary?.submission_tls_enabled
        ? 'Worker-to-MTA credentials and TLS are configured.'
        : 'Configure SMTP username, password, and TLS for worker submission.',
      tone: managedSmtpDeploymentSummary?.submission_credentials_configured
        && managedSmtpDeploymentSummary?.submission_tls_enabled ? 'good' : 'warn',
    },
    {
      label: 'Domain auth',
      value: domainDashboard?.authentication_status || 'Not loaded',
      detail: authenticationReady
        ? 'Domain authentication is verified in the reputation dashboard.'
        : 'Load the reputation dashboard and resolve SPF, DKIM, DMARC, or bounce-MX gaps.',
      tone: authenticationReady ? 'good' : 'warn',
    },
    {
      label: 'MTA smoke',
      value: latestReadinessCheck?.status || 'Not loaded',
      detail: latestReadinessOk
        ? `Latest readiness check passed at ${latestReadinessCheck?.created_at || 'unknown time'}.`
        : 'Publish or load MTA smoke evidence before first send.',
      tone: latestReadinessOk ? 'good' : 'warn',
    },
    {
      label: 'Compliance',
      value: domainDashboard?.compliance_status || firstSendComplianceStatus,
      detail: domainDashboard?.compliance_reason || 'No active hold loaded for selected domain.',
      tone: domainDashboard?.compliance_status === 'hold' || firstSendComplianceStatus === 'active'
        ? 'warn'
        : 'good',
    },
  ];
  const firstSendReadinessItems = firstSendReadiness
    ? firstSendReadiness.items.map((item) => ({
      label: item.label,
      value: item.value,
      detail: item.detail,
      tone: item.status === 'ready' ? 'good' : 'warn',
    }))
    : fallbackFirstSendReadinessItems;
  const firstSendReadyCount = firstSendReadiness?.items.filter((item) => item.status === 'ready').length || 0;
  const firstSendSummaryTone = firstSendReadiness
    ? firstSendReadiness.ok ? 'good' : 'warn'
    : 'warn';
  const firstSendSummaryTitle = firstSendReadiness
    ? firstSendReadiness.ok ? 'Ready for first seed send' : 'First seed send blocked'
    : 'First-send evidence not loaded';
  const firstSendControlCount = firstSendReadiness?.items.length || 0;
  const firstSendControlProgress = firstSendReadiness
    ? `${formatInt(firstSendReadyCount)} of ${formatInt(firstSendControlCount)} control(s) ready`
    : '';
  const firstSendSummaryDetail = firstSendReadiness
    ? firstSendReadiness.blockers.length
      ? `${firstSendControlProgress}; ${formatInt(firstSendReadiness.blockers.length)} blocker(s): ${firstSendReadiness.blockers.join(', ')}.`
      : `${firstSendControlProgress}.`
    : 'Load First Send Evidence to check provider, MTA, auth, DNS, smoke, and compliance gates.';
  const deliveryTriageAction = failedRecords
    ? {
      tone: 'warn',
      title: 'Review failed records',
      detail: `${formatInt(failedRecords)} failed record(s) need requeue, skip, or suppression review.`,
      actionLabel: 'Requeue Record',
      run: requeueRecord,
      disabled: busy || !selectedRecordId,
    }
    : queuedRecords
      ? {
        tone: 'warn',
        title: 'Process queued delivery',
        detail: `${formatInt(queuedRecords)} queued record(s) are ready for the send engine.`,
        actionLabel: 'Process Queued',
        run: processQueued,
        disabled: busy,
      }
      : activeJobs
        ? {
          tone: 'warn',
          title: 'Load job progress',
          detail: `${formatInt(activeJobs)} active job(s) should be checked for remaining work.`,
          actionLabel: 'Load Progress',
          run: loadProgress,
          disabled: busy || !selectedJobId,
        }
        : {
          tone: 'good',
          title: 'Delivery clear',
          detail: 'No visible queue or failed-record pressure in the loaded delivery lists.',
          actionLabel: 'Refresh Lists',
          run: onRefresh,
          disabled: busy,
        };
  const deliveryTriageItems = [
    {
      label: 'Queue pressure',
      value: formatInt(queuedRecords),
      detail: retryPressure ? `${formatInt(retryPressure)} queued retry candidate(s)` : 'No retry pressure detected',
      tone: queuedRecords ? 'warn' : 'good',
    },
    {
      label: 'Failure review',
      value: formatInt(failedRecords),
      detail: blockedRecords ? `${formatInt(blockedRecords)} blocked or skipped record(s)` : 'No blocked records visible',
      tone: failedRecords ? 'warn' : 'good',
    },
    {
      label: 'Selected job',
      value: selectedJob?.status || 'None',
      detail: progress ? `${formatPct(progress.percent_complete)} complete, ${formatInt(progress.remaining_count)} remaining` : 'Load progress for job detail',
      tone: selectedJob && !['completed', 'failed', 'cancelled'].includes(selectedJob.status) ? 'warn' : 'good',
    },
    {
      label: 'Selected record',
      value: selectedRecord?.status || 'None',
      detail: selectedRecord?.error_message || selectedRecord?.to_email || 'Select a record for retry context',
      tone: blockedDeliveryStatuses.includes(selectedRecord?.status || '') ? 'warn' : 'good',
    },
    {
      label: 'Queue audit',
      value: formatInt(queueControlAttempts.length),
      detail: claimBlockedAttempts
        ? `${formatInt(claimBlockedAttempts)} claim-blocked audit row(s)`
        : deadLetterAttempts
          ? `${formatInt(deadLetterAttempts)} dead-letter audit row(s)`
          : 'Load attempts for queue-control audit rows',
      tone: queueControlAttempts.length ? 'warn' : 'good',
    },
  ];
  const deliveryFoundationItems = [
    {
      label: 'Owned SMTP server',
      value: managedSmtpDeploymentSummary?.nodes.total ? 'Modeled' : 'Gap',
      detail: managedSmtpDeploymentSummary?.nodes.total
        ? `${formatInt(managedSmtpDeploymentSummary.nodes.total)} MTA node(s) registered in deployment inventory.`
        : 'Platform-owned SMTP service still needs MTA, auth, throttling, and domain controls.',
      tone: managedSmtpDeploymentSummary?.nodes.total ? 'good' : 'warn',
    },
    {
      label: 'Send queues',
      value: sendJobs.length || sendRecords.length ? 'Visible' : 'Gap',
      detail: `${formatInt(sendJobs.length)} job(s), ${formatInt(queuedRecords)} queued record(s), ${formatInt(activeJobs)} active job(s).`,
      tone: sendJobs.length || sendRecords.length ? 'good' : 'warn',
    },
    {
      label: 'Bounce queues',
      value: failedRecords ? 'Signals' : 'Gap',
      detail: failedRecords ? `${formatInt(failedRecords)} failed record(s) need bounce classification.` : 'Dedicated bounce and complaint queues are still needed.',
      tone: 'warn',
    },
    {
      label: 'Deliverability feedback',
      value: providerFootprint.length ? providerFootprint.join(', ') : 'Gap',
      detail: 'Reputation, complaint, bounce, and inbox-placement feedback need a unified loop.',
      tone: 'warn',
    },
  ];
  const deliveryOperationsContractItems = [
    {
      label: 'SMTP service contract',
      value: managedSmtpDeploymentSummary?.managed_smtp_route_count ? 'Visible' : 'Gap',
      detail: managedSmtpDeploymentSummary?.managed_smtp_route_count
        ? `${formatInt(managedSmtpDeploymentSummary.managed_smtp_route_count)} route(s), ${formatInt(managedSmtpDeploymentSummary.managed_smtp_domain_policy_count)} domain policy mapping(s).`
        : 'Owned SMTP needs MTA configuration, authenticated submission, domain policy, TLS, and tenant-level rate controls.',
      tone: managedSmtpDeploymentSummary?.managed_smtp_route_count ? 'good' : 'warn',
    },
    {
      label: 'Queue lifecycle',
      value: sendRecords.length ? 'Visible' : 'Gap',
      detail: 'Send queues need claim locks, visibility timeouts, dead-letter handling, and operator-safe replay controls.',
      tone: sendRecords.length ? 'good' : 'warn',
    },
    {
      label: 'Retry policy',
      value: retryPressure ? `${formatInt(retryPressure)} retries` : 'Pending',
      detail: 'Retries need provider-aware backoff, max-attempt policy, suppression checks, and permanent-failure promotion.',
      tone: retryPressure ? 'warn' : 'warn',
    },
    {
      label: 'Bounce classification',
      value: failedRecords ? `${formatInt(failedRecords)} signals` : 'Gap',
      detail: 'Failures must classify hard bounce, soft bounce, complaint, deferral, and policy block outcomes.',
      tone: 'warn',
    },
    {
      label: 'Feedback ingestion',
      value: providerFootprint.length ? providerFootprint.join(', ') : 'Gap',
      detail: 'Provider events and owned SMTP logs need one durable feedback stream into suppression and analytics records.',
      tone: 'warn',
    },
    {
      label: 'Deliverability controls',
      value: 'Gap',
      detail: 'Domain warmup, reputation monitoring, inbox-placement signals, and throttle overrides need admin controls.',
      tone: 'warn',
    },
  ];
  const complianceAuditLog = Array.isArray(selectedDomainPolicy?.metadata_json?.compliance_audit_log)
    ? selectedDomainPolicy.metadata_json.compliance_audit_log
    : [];
  const activeComplianceHold = selectedDomainPolicy?.metadata_json?.compliance_hold;
  const complianceHoldStatus = typeof activeComplianceHold === 'object' && activeComplianceHold !== null && 'status' in activeComplianceHold
    ? String((activeComplianceHold as Record<string, unknown>).status)
    : 'clear';
  const domainComplianceItems = [
    {
      label: 'Compliance hold',
      value: domainDashboard?.compliance_status || complianceHoldStatus,
      detail: domainDashboard?.compliance_reason || selectedDomainPolicy?.paused_until || 'No active domain hold loaded',
      tone: domainDashboard?.compliance_status === 'hold' || complianceHoldStatus === 'active' ? 'warn' : 'good',
    },
    {
      label: 'Reputation status',
      value: domainDashboard?.reputation_status || 'Not loaded',
      detail: domainDashboard ? `${formatPct(domainDashboard.bounce_rate)} bounce, ${formatPct(domainDashboard.complaint_rate)} complaint` : 'Load dashboard for reputation rates',
      tone: domainDashboard?.reputation_status === 'risk' ? 'warn' : 'good',
    },
    {
      label: 'Throttle status',
      value: domainDashboard?.throttle_status || 'Not loaded',
      detail: selectedDomainPolicy ? `${selectedDomainPolicy.max_per_minute || 'no'} per-minute / ${selectedDomainPolicy.max_concurrent || 'no'} concurrent` : 'Select a domain policy',
      tone: domainDashboard?.throttle_status === 'paused' ? 'warn' : 'good',
    },
    {
      label: 'Compliance audit',
      value: formatInt(complianceAuditLog.length),
      detail: complianceAuditLog.length ? 'hold/release audit entries stored on policy metadata' : 'No hold/release audit entries loaded',
      tone: complianceAuditLog.length ? 'warn' : 'good',
    },
  ];
  const managedSmtpRouteItems = managedSmtpRouteResolution?.ok && managedSmtpRouteResolution.route
    ? [
      {
        label: 'Route',
        value: managedSmtpRouteResolution.route.delivery_route_name,
        detail: `${managedSmtpRouteResolution.route.provider} via ${managedSmtpRouteResolution.route.hostname}`,
        tone: 'good',
      },
      {
        label: 'IP pool',
        value: managedSmtpRouteResolution.route.ip_pool_name,
        detail: managedSmtpRouteResolution.route.ip_pool_type,
        tone: 'good',
      },
      {
        label: 'MTA node',
        value: managedSmtpRouteResolution.route.mta_node_name,
        detail: managedSmtpRouteResolution.route.public_ipv4 || managedSmtpRouteResolution.route.hostname,
        tone: 'good',
      },
      {
        label: 'Submission',
        value: `${managedSmtpRouteResolution.route.submission_host}:${managedSmtpRouteResolution.route.submission_port}`,
        detail: managedSmtpRouteResolution.route.auth_secret_ref ? 'auth secret referenced' : 'auth secret missing',
        tone: managedSmtpRouteResolution.route.auth_secret_ref ? 'good' : 'warn',
      },
    ]
    : [
      {
        label: 'Route readiness',
        value: managedSmtpRouteResolution?.reason?.code || 'Not checked',
        detail: managedSmtpRouteResolution?.reason?.message || 'Resolve the selected domain policy route.',
        tone: managedSmtpRouteResolution ? 'warn' : 'warn',
      },
    ];

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
      await refreshDeliveryAttempts();
      if (selectedJobId) {
        const refreshedProgress = await fetchJson<CampaignSendJobProgress>(`/api/v1/campaign-send-jobs/${selectedJobId}/progress`);
        setProgress(refreshedProgress);
      }
      return `Processed ${formatInt(data.claimed_count)} record(s): ${formatInt(data.sent_count)} sent, ${formatInt(data.failed_count)} failed, ${formatInt(data.skipped_count || 0)} policy-blocked.`;
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

  async function deadLetterRecord() {
    await runDeliveryOperation('Dead-lettering send record', async () => {
      if (!selectedRecordId) throw new Error('Select a send record.');
      const reason = window.prompt('Reason for dead-lettering this record?', selectedRecord?.error_message || 'Operator reviewed terminal queue issue') || '';
      const suffix = reason ? `?reason=${encodeURIComponent(reason)}` : '';
      const record = await fetchJson<EmailSendRecordRead>(`/api/v1/email-send-records/${selectedRecordId}/dead-letter${suffix}`, { method: 'POST' });
      await onRefresh();
      await refreshDeliveryAttempts();
      return `Dead-lettered ${record.to_email}; status is ${record.status}.`;
    });
  }

  async function deleteRecord() {
    if (!selectedRecordId) {
      setStatus('Select a send record before deleting.');
      return;
    }
    const label = selectedRecord?.to_email || selectedRecordId;
    if (!window.confirm(`Delete send record for "${label}"? This also removes its tracking events.`)) return;
    await runDeliveryOperation('Deleting send record', async () => {
      await fetchJson<{ id: string }>(`/api/v1/email-send-records/${selectedRecordId}`, { method: 'DELETE' });
      setSelectedRecordId('');
      setTrackingLinks(null);
      setAiDeliverySummary([]);
      setAiDeliveryRecommendations([]);
      await onRefresh();
      return `Deleted send record for ${label}.`;
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

  async function refreshDeliveryAttempts() {
    const params = new URLSearchParams({ limit: '50', offset: '0' });
    if (selectedRecordId) params.set('send_record_id', selectedRecordId);
    else if (selectedJobId) params.set('send_job_id', selectedJobId);
    const data = await fetchJson<ListResponse<DeliveryAttemptRead>>(`/api/v1/delivery-attempts/list?${params.toString()}`);
    setDeliveryAttempts(data.items || []);
    return data.items || [];
  }

  function updateFeedbackFilter(name: keyof typeof feedbackFilters, value: string) {
    setFeedbackFilters((current) => ({ ...current, [name]: value }));
  }

  function updateReadinessFilter(name: keyof typeof readinessFilters, value: string) {
    setReadinessFilters((current) => ({ ...current, [name]: value }));
  }

  function useSelectedRecordForFeedbackFilters() {
    if (!selectedRecord) {
      setStatus('Select a send record before applying feedback filters.');
      return;
    }
    setFeedbackFilters((current) => ({
      ...current,
      provider: selectedRecord.provider || current.provider,
      email: selectedRecord.to_email,
      provider_message_id: selectedRecord.provider_message_id || current.provider_message_id,
    }));
  }

  async function loadProviderFeedbackEvents() {
    await runDeliveryOperation('Loading provider feedback evidence', async () => {
      const params = new URLSearchParams({ limit: '50', offset: '0' });
      Object.entries(feedbackFilters).forEach(([key, value]) => {
        if (value.trim()) params.set(key, value.trim());
      });
      const data = await fetchJson<ListResponse<ProviderFeedbackEventRead>>(`/api/v1/provider-feedback-events/list?${params.toString()}`);
      setProviderFeedbackEvents(data.items || []);
      setProviderFeedbackTotal(data.total || 0);
      const warningCount = (data.items || []).filter((event) => ['dsn_bounce', 'bounce', 'complaint', 'tempfail', 'deferred'].includes(event.event_name)).length;
      return `Loaded ${formatInt(data.items?.length || 0)} provider feedback event(s), ${formatInt(warningCount)} requiring delivery review.`;
    });
  }

  async function loadReadinessChecks() {
    await runDeliveryOperation('Loading managed SMTP readiness checks', async () => {
      const params = new URLSearchParams({ limit: '25', offset: '0' });
      const summaryParams = new URLSearchParams();
      Object.entries(readinessFilters).forEach(([key, value]) => {
        if (value.trim()) {
          params.set(key, value.trim());
          summaryParams.set(key, value.trim());
        }
      });
      const [data, summary, trend, alerts, notification] = await Promise.all([
        fetchJson<ListResponse<ManagedSmtpReadinessCheckRead>>(`/api/v1/managed-smtp/readiness-checks/list?${params.toString()}`),
        fetchJson<ManagedSmtpReadinessSummaryRead>(`/api/v1/managed-smtp/readiness-checks/summary?${summaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessTrendRead>(`/api/v1/managed-smtp/readiness-checks/trend?${summaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessAlertsRead>(`/api/v1/managed-smtp/readiness-checks/alerts?${summaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessNotificationRead>(`/api/v1/managed-smtp/readiness-checks/notification?${summaryParams.toString()}`),
      ]);
      setReadinessChecks(data.items || []);
      setReadinessCheckTotal(data.total || 0);
      setReadinessSummary(summary);
      setReadinessTrend(trend);
      setReadinessAlerts(alerts);
      setReadinessNotification(notification);
      const warningCount = summary.warning_count + summary.failed_count;
      return `Loaded ${formatInt(data.items?.length || 0)} managed SMTP readiness check(s), ${formatInt(alerts.alert_count || warningCount)} alert evidence row(s).`;
    });
  }

  async function loadManagedSmtpDeploymentSummary() {
    await runDeliveryOperation('Loading managed SMTP deployment summary', async () => {
      const summary = await fetchJson<ManagedSmtpDeploymentSummaryRead>('/api/v1/managed-smtp/deployment-summary?limit=8');
      setManagedSmtpDeploymentSummary(summary);
      return `Loaded managed SMTP deployment summary: ${formatInt(summary.nodes.total)} node(s), ${formatInt(summary.managed_smtp_route_count)} route(s), ${formatInt(summary.managed_smtp_domain_policy_count)} domain policy mapping(s).`;
    });
  }

  async function loadFirstSendEvidence() {
    await runDeliveryOperation('Loading managed SMTP first-send evidence', async () => {
      const readinessParams = new URLSearchParams({ limit: '25', offset: '0' });
      const readinessSummaryParams = new URLSearchParams();
      Object.entries(readinessFilters).forEach(([key, value]) => {
        if (value.trim()) {
          readinessParams.set(key, value.trim());
          readinessSummaryParams.set(key, value.trim());
        }
      });
      const [firstSend, readiness, summary, trend, alerts, notification, policies] = await Promise.all([
        fetchJson<ManagedSmtpFirstSendRead>('/api/v1/managed-smtp/first-send-readiness?limit=8'),
        fetchJson<ListResponse<ManagedSmtpReadinessCheckRead>>(`/api/v1/managed-smtp/readiness-checks/list?${readinessParams.toString()}`),
        fetchJson<ManagedSmtpReadinessSummaryRead>(`/api/v1/managed-smtp/readiness-checks/summary?${readinessSummaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessTrendRead>(`/api/v1/managed-smtp/readiness-checks/trend?${readinessSummaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessAlertsRead>(`/api/v1/managed-smtp/readiness-checks/alerts?${readinessSummaryParams.toString()}`),
        fetchJson<ManagedSmtpReadinessNotificationRead>(`/api/v1/managed-smtp/readiness-checks/notification?${readinessSummaryParams.toString()}`),
        fetchJson<ListResponse<DomainDeliveryPolicyRead>>('/api/v1/domain-delivery-policies/list?limit=100&offset=0'),
      ]);
      setFirstSendReadiness(firstSend);
      setManagedSmtpDeploymentSummary(firstSend.deployment_summary);
      setReadinessChecks(readiness.items || []);
      setReadinessCheckTotal(readiness.total || 0);
      setReadinessSummary(summary);
      setReadinessTrend(trend);
      setReadinessAlerts(alerts);
      setReadinessNotification(notification);
      const policyItems = policies.items || [];
      setDomainPolicies(policyItems);
      const policyId = selectedDomainPolicyId || policyItems[0]?.id || '';
      if (policyId && policyId !== selectedDomainPolicyId) setSelectedDomainPolicyId(policyId);
      if (policyId) {
        const dashboard = await fetchJson<DomainReputationDashboardRead>(`/api/v1/domain-delivery-policies/${policyId}/reputation-dashboard`);
        setDomainDashboard(dashboard);
      }
      const port25 = firstSend.items.find((item) => item.key === 'port25')?.value || 'unknown';
      const blockerText = firstSend.blockers.length
        ? `${formatInt(firstSend.blockers.length)} blocker(s)`
        : 'no blockers';
      return `Loaded first-send evidence: port 25 ${port25}, ${blockerText}, ${formatInt(summary.ok_count)} passing readiness check(s), ${formatInt(policyItems.length)} domain policy row(s).`;
    });
  }

  async function loadDeliveryAttempts() {
    await runDeliveryOperation('Loading delivery attempt audit', async () => {
      const items = await refreshDeliveryAttempts();
      const blocked = items.filter((attempt) => attempt.status === 'claim_blocked').length;
      const dead = items.filter((attempt) => attempt.status === 'dead_lettered').length;
      return `Loaded ${formatInt(items.length)} attempt row(s): ${formatInt(blocked)} claim-blocked, ${formatInt(dead)} dead-lettered.`;
    });
  }

  async function loadDomainPolicies() {
    await runDeliveryOperation('Loading domain delivery policies', async () => {
      const data = await fetchJson<ListResponse<DomainDeliveryPolicyRead>>('/api/v1/domain-delivery-policies/list?limit=100&offset=0');
      const items = data.items || [];
      setDomainPolicies(items);
      if (!selectedDomainPolicyId && items.length) setSelectedDomainPolicyId(items[0].id);
      return `Loaded ${formatInt(items.length)} domain delivery policy row(s).`;
    });
  }

  async function loadDomainReputationDashboard() {
    await runDeliveryOperation('Loading domain reputation dashboard', async () => {
      if (!selectedDomainPolicyId) throw new Error('Select a domain policy.');
      const data = await fetchJson<DomainReputationDashboardRead>(`/api/v1/domain-delivery-policies/${selectedDomainPolicyId}/reputation-dashboard`);
      setDomainDashboard(data);
      return `Loaded ${data.domain} reputation dashboard: ${data.reputation_status}, compliance ${data.compliance_status}.`;
    });
  }

  async function applyDomainComplianceHold() {
    await runDeliveryOperation('Applying domain compliance hold', async () => {
      if (!selectedDomainPolicyId) throw new Error('Select a domain policy.');
      const reason = window.prompt('Reason for the compliance hold?', domainDashboard?.compliance_reason || 'Operator compliance review') || '';
      if (!reason.trim()) throw new Error('Compliance hold reason is required.');
      const policy = await fetchJson<DomainDeliveryPolicyRead>(`/api/v1/domain-delivery-policies/${selectedDomainPolicyId}/compliance-hold`, {
        method: 'POST',
        body: JSON.stringify({
          reason,
          abuse_type: 'operator_review',
          operator: 'esp_admin',
          paused_hours: 24,
        }),
      });
      setDomainPolicies((items) => items.map((item) => item.id === policy.id ? policy : item));
      const dashboard = await fetchJson<DomainReputationDashboardRead>(`/api/v1/domain-delivery-policies/${selectedDomainPolicyId}/reputation-dashboard`);
      setDomainDashboard(dashboard);
      return `Applied compliance hold for ${policy.domain}; delivery is paused until ${policy.paused_until || 'review release'}.`;
    });
  }

  async function releaseDomainComplianceHold() {
    await runDeliveryOperation('Releasing domain compliance hold', async () => {
      if (!selectedDomainPolicyId) throw new Error('Select a domain policy.');
      const reason = window.prompt('Release reason?', 'review_cleared') || 'review_cleared';
      const policy = await fetchJson<DomainDeliveryPolicyRead>(`/api/v1/domain-delivery-policies/${selectedDomainPolicyId}/release-compliance-hold`, {
        method: 'POST',
        body: JSON.stringify({
          reason,
          operator: 'esp_admin',
        }),
      });
      setDomainPolicies((items) => items.map((item) => item.id === policy.id ? policy : item));
      const dashboard = await fetchJson<DomainReputationDashboardRead>(`/api/v1/domain-delivery-policies/${selectedDomainPolicyId}/reputation-dashboard`);
      setDomainDashboard(dashboard);
      return `Released compliance hold for ${policy.domain}; delivery policy claiming can resume.`;
    });
  }

  async function resolveManagedSmtpRoute() {
    await runDeliveryOperation('Resolving managed SMTP route', async () => {
      if (!selectedDomainPolicy) throw new Error('Select a domain policy.');
      const result = await fetchJson<ManagedSmtpRouteResolutionRead>('/api/v1/managed-smtp/resolve-route', {
        method: 'POST',
        body: JSON.stringify({
          from_domain: selectedDomainPolicy.domain,
          route_id: selectedDomainPolicy.route_id,
          send_type: 'internal_test',
        }),
      });
      setManagedSmtpRouteResolution(result);
      if (result.ok && result.route) {
        return `Managed SMTP route ready: ${result.route.delivery_route_name} -> ${result.route.ip_pool_name} -> ${result.route.mta_node_name}.`;
      }
      return `Managed SMTP route blocked: ${result.reason?.code || 'UNKNOWN'} - ${result.reason?.message || 'No reason returned.'}`;
    });
  }

  async function reviewDeliveryWithAi() {
    await runDeliveryOperation('Running AI Delivery Review', async () => {
      const data = await fetchJson<AIWorkflowAnalysis>('/api/v1/ai/delivery/analyze', {
        method: 'POST',
        body: JSON.stringify({
          delivery_context: {
            jobs: { items: sendJobs },
            records: { items: sendRecords },
            progress,
            selected_job: selectedJob || null,
            selected_record: selectedRecord || null,
              triage: {
              title: deliveryTriageAction.title,
              detail: deliveryTriageAction.detail,
              queued_records: queuedRecords,
              failed_records: failedRecords,
              active_jobs: activeJobs,
              retry_pressure: retryPressure,
              queue_control_attempts: queueControlAttempts,
            },
          },
          goals: [
            'Prioritize failed and queued delivery records',
            'Avoid blind retries when suppression or compliance review is safer',
            'Recommend the next operator action for the delivery manager',
          ],
        }),
      });
      setAiDeliverySummary(data.summary || []);
      setAiDeliveryRecommendations(data.recommendations || []);
      return `AI Delivery Review loaded ${formatInt(data.recommendations?.length || 0)} recommendation(s).`;
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
      <section className={`delivery-triage-panel full-span ${deliveryTriageAction.tone}`}>
        <div className="delivery-triage-head">
          <div>
            <span>Delivery triage</span>
            <strong>{deliveryTriageAction.title}</strong>
            <small>{deliveryTriageAction.detail}</small>
          </div>
          <button className={deliveryTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={deliveryTriageAction.run} disabled={deliveryTriageAction.disabled}>{deliveryTriageAction.actionLabel}</button>
        </div>
        <div className="delivery-triage-list" aria-label="Delivery triage support list">
          {deliveryTriageItems.map((item) => (
            <article className={`delivery-triage-row ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="delivery-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Send Engine Foundation</h3>
            <span className="muted">Owned SMTP, queues, bounces, and deliverability feedback.</span>
          </div>
          <a href="#settings">Provider settings</a>
        </div>
        <div className="delivery-foundation-strip" aria-label="Send engine foundation strip">
          {deliveryFoundationItems.map((item) => (
            <div className={`delivery-foundation-item ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </div>
          ))}
        </div>
      </section>
      <section className="delivery-operations-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Send Engine Operations Contract</h3>
            <span className="muted">Operational contracts for owned SMTP, queue lifecycle, retries, bounces, feedback, and deliverability controls.</span>
          </div>
          <a href="#compliance">Open Compliance</a>
        </div>
        <div className="delivery-operations-checklist">
          {deliveryOperationsContractItems.map((item) => (
            <article className={`delivery-operations-check ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel full-span provider-feedback-panel">
        <div className="panel-head">
          <div>
            <h2>Managed SMTP Deployment</h2>
            <span className="muted">Control-plane inventory for provider accounts, MTA nodes, IP pools, routes, and node readiness.</span>
          </div>
          <button className="link-button" onClick={loadManagedSmtpDeploymentSummary} disabled={busy}>Load SMTP Deployment</button>
        </div>
        <div className="delivery-score-strip" aria-label="Managed SMTP deployment score strip">
          {managedSmtpDeploymentItems.map((item) => (
            <div className={`delivery-score-item ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </div>
          ))}
        </div>
        {managedSmtpDeploymentSummary?.recent_nodes.length ? (
          <div className="provider-feedback-list">
            {managedSmtpDeploymentSummary.recent_nodes.map((item) => (
              <article className={item.readiness_summary.latest_check?.status === 'ok' ? 'good' : 'warn'} key={item.node.id}>
                <div>
                  <span>{item.provider_account?.provider || 'provider'} / {item.node.status}</span>
                  <strong>{item.node.name} - {item.node.hostname}</strong>
                </div>
                <small>{item.node.public_ipv4 || item.node.submission_host || 'No public IP loaded'}</small>
                <dl>
                  <div><dt>provider</dt><dd>{item.provider_account?.name || '-'}</dd></div>
                  <div><dt>support case</dt><dd>{item.provider_account?.support_case_ref || '-'}</dd></div>
                  <div><dt>port 25</dt><dd>{item.provider_account?.port25_status || 'unknown'}</dd></div>
                  <div><dt>rDNS</dt><dd>{item.provider_account?.rdns_status || 'unknown'}</dd></div>
                  <div><dt>submission</dt><dd>{item.node.submission_host || item.node.hostname}:{item.node.submission_port}</dd></div>
                  <div><dt>pools</dt><dd>{formatInt(item.pool_memberships.length)}</dd></div>
                  <div><dt>readiness</dt><dd>{formatInt(item.readiness_summary.ok_count)} ok / {formatInt(item.readiness_summary.failed_count)} failed</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <div className="ai-empty-state">
            <strong>No managed SMTP deployment summary loaded</strong>
            <span>Load SMTP Deployment after bootstrapping the first provider account, MTA node, IP pool, route, and domain policy.</span>
          </div>
        )}
      </section>
      <section className="panel full-span first-send-checklist-panel">
        <div className="panel-head">
          <div>
            <h2>Managed SMTP First Send</h2>
            <span className="muted">Go/no-go checklist for the first controlled seed email through the owned MTA path.</span>
          </div>
          <div className="button-row">
            <button className="ghost" onClick={loadFirstSendEvidence} disabled={busy}>Load First Send Evidence</button>
            <button className="ghost" onClick={loadReadinessChecks} disabled={busy}>Load Readiness</button>
          </div>
        </div>
        <div className="first-send-checklist">
          <article className={`first-send-summary-card ${firstSendSummaryTone}`}>
            <span>First-send status</span>
            <strong>{firstSendSummaryTitle}</strong>
            <small>{firstSendSummaryDetail}</small>
          </article>
          {firstSendReadinessItems.map((item) => (
            <article className={`first-send-check ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel full-span domain-compliance-panel">
        <div className="panel-head">
          <div>
            <h2>Managed SMTP Domain Compliance</h2>
            <span className="muted">Compliance hold, release, reputation dashboard, and policy audit controls for owned SMTP domains.</span>
          </div>
          <button className="link-button" onClick={loadDomainPolicies} disabled={busy}>Load Domain Policies</button>
        </div>
        <div className="form-grid">
          <label className="wide-field">
            Domain policy
            <select value={selectedDomainPolicyId} onChange={(event) => {
              setSelectedDomainPolicyId(event.target.value);
              setDomainDashboard(null);
              setManagedSmtpRouteResolution(null);
            }}>
              <option value="">Select domain policy</option>
              {domainPolicies.map((policy) => (
                <option value={policy.id} key={policy.id}>
                  {policy.domain} | {policy.warmup_stage || 'no warmup'} | {policy.paused_until ? 'paused' : 'active'}
                </option>
              ))}
            </select>
          </label>
          <label>
            Warmup
            <input value={selectedDomainPolicy?.warmup_stage || 'No warmup stage'} readOnly />
          </label>
          <label>
            Route
            <input value={selectedDomainPolicy?.route_id?.slice(0, 8) || 'No route'} readOnly />
          </label>
          <label className="wide-field">
            Latest recommendation
            <input value={domainDashboard?.recommendations?.[0] || 'Load the reputation dashboard for domain-specific guidance.'} readOnly />
          </label>
        </div>
        <div className="domain-compliance-strip" aria-label="Managed SMTP domain compliance strip">
          {domainComplianceItems.map((item) => (
            <div className={`domain-compliance-item ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </div>
          ))}
        </div>
        <div className="panel-head compact-head">
          <div>
            <h3>Managed SMTP Route Resolution</h3>
            <span className="muted">Resolve the selected domain to its IP pool, MTA node, and submission endpoint before cloud send testing.</span>
          </div>
          <button className="link-button" onClick={resolveManagedSmtpRoute} disabled={busy || !selectedDomainPolicyId}>Resolve Route</button>
        </div>
        <div className="managed-smtp-route-inspector">
          {managedSmtpRouteItems.map((item) => (
            <article className={`managed-smtp-route-field ${item.tone}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
        {managedSmtpRouteResolution?.reason ? (
          <details className="json-details">
            <summary>Route block details</summary>
            <pre className="json-preview">{JSON.stringify(managedSmtpRouteResolution.reason.details, null, 2)}</pre>
          </details>
        ) : null}
        <div className="button-row">
          <button className="ghost" onClick={loadDomainReputationDashboard} disabled={busy || !selectedDomainPolicyId}>Load Reputation Dashboard</button>
          <button className="ghost" onClick={resolveManagedSmtpRoute} disabled={busy || !selectedDomainPolicyId}>Resolve SMTP Route</button>
          <button className="ghost" onClick={applyDomainComplianceHold} disabled={busy || !selectedDomainPolicyId}>Apply Compliance Hold</button>
          <button className="ghost" onClick={releaseDomainComplianceHold} disabled={busy || !selectedDomainPolicyId}>Release Compliance Hold</button>
        </div>
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
                    setDeliveryAttempts([]);
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
                    setDeliveryAttempts([]);
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
              setDeliveryAttempts([]);
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
              setDeliveryAttempts([]);
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
          <button className="ghost" onClick={deadLetterRecord} disabled={busy || !selectedRecordId}>Dead-letter Record</button>
          <button className="ghost" onClick={deleteRecord} disabled={busy || !selectedRecordId}>Delete Record</button>
          <button className="ghost" onClick={loadTrackingLinks} disabled={busy || !selectedRecordId}>Tracking Links</button>
          <button className="ghost" onClick={loadDeliveryAttempts} disabled={busy}>Load Attempt Audit</button>
          <button className="ghost" onClick={loadProviderFeedbackEvents} disabled={busy}>Load Provider Feedback</button>
          <button className="ghost" onClick={loadReadinessChecks} disabled={busy}>Load SMTP Readiness</button>
          <button className="ghost" onClick={loadManagedSmtpDeploymentSummary} disabled={busy}>Load SMTP Deployment</button>
          <button className="ghost" onClick={reviewDeliveryWithAi} disabled={busy}>AI Delivery Review</button>
          <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh Lists</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className="delivery-ai-review-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>AI Delivery Review</h3>
              <span className="muted">{aiDeliveryRecommendations?.length ? `${formatInt(aiDeliveryRecommendations.length)} recommendation(s)` : 'Use current queue, failure, and retry context for AI review.'}</span>
            </div>
            <button className="link-button" type="button" onClick={reviewDeliveryWithAi} disabled={busy}>Run AI Review</button>
          </div>
          {aiDeliverySummary.length ? (
            <div className="delivery-ai-summary">
              {aiDeliverySummary.slice(0, 4).map((item) => <span key={item}>{item}</span>)}
            </div>
          ) : null}
          {aiDeliveryRecommendations?.length ? (
            <div className="recommendation-list">
              {aiDeliveryRecommendations.slice(0, 5).map((item) => (
                <article key={item.code}>
                  <span className="pill">{item.priority}</span>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  <small>{item.suggested_action || item.suggested_instruction || 'Review recommendation.'}</small>
                </article>
              ))}
            </div>
          ) : (
            <div className="ai-empty-state">
              <strong>No AI delivery review loaded</strong>
              <span>Run AI Delivery Review after loading jobs and records to prioritize queue processing, retry handling, and suppression review.</span>
            </div>
          )}
        </div>
      </section>
      <section className="panel full-span delivery-audit-panel">
        <div className="panel-head">
          <div>
            <h2>Delivery Attempt Audit</h2>
            <span className="muted">Claim-blocked and dead-letter audit rows explain queue-control decisions.</span>
          </div>
          <button className="link-button" onClick={loadDeliveryAttempts} disabled={busy}>Load Attempt Audit</button>
        </div>
        {deliveryAttempts.length ? (
          <div className="delivery-audit-list">
            {deliveryAttempts.slice(0, 8).map((attempt) => {
              const metadata = attempt.metadata_json || {};
              const reason = String(metadata.reason || attempt.error_message || attempt.route_key || attempt.status);
              const domain = String(metadata.to_domain || '-');
              const policy = String(metadata.domain_delivery_policy_id || '-');
              return (
                <article className={['claim_blocked', 'dead_lettered'].includes(attempt.status) ? 'warn' : 'good'} key={attempt.id}>
                  <div>
                    <span>{attempt.status}</span>
                    <strong>{reason}</strong>
                  </div>
                  <small>{attempt.started_at}</small>
                  <dl>
                    <div><dt>record</dt><dd>{attempt.send_record_id.slice(0, 8)}</dd></div>
                    <div><dt>route</dt><dd>{attempt.route_type || '-'} / {attempt.route_key || '-'}</dd></div>
                    <div><dt>domain</dt><dd>{domain}</dd></div>
                    <div><dt>policy</dt><dd>{policy === '-' ? '-' : policy.slice(0, 8)}</dd></div>
                  </dl>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="ai-empty-state">
            <strong>No delivery attempt audit loaded</strong>
            <span>Load Attempt Audit after processing queues or selecting a record to inspect claim-blocked and dead-letter rows.</span>
          </div>
        )}
      </section>
      <section className="panel full-span provider-feedback-panel">
        <div className="panel-head">
          <div>
            <h2>Managed SMTP Readiness</h2>
            <span className="muted">Published MTA smoke, STARTTLS, DKIM, and feedback-loop checks from managed SMTP hosts.</span>
          </div>
          <button className="link-button" onClick={loadReadinessChecks} disabled={busy}>Load SMTP Readiness</button>
        </div>
        <div className="form-grid">
          <label>
            Status
            <select value={readinessFilters.status} onChange={(event) => updateReadinessFilter('status', event.target.value)}>
              <option value="">Any status</option>
              <option value="ok">ok</option>
              <option value="warning">warning</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label>
            Domain
            <input value={readinessFilters.domain} onChange={(event) => updateReadinessFilter('domain', event.target.value)} placeholder="example.com" />
          </label>
          <label>
            Host
            <input value={readinessFilters.host} onChange={(event) => updateReadinessFilter('host', event.target.value)} placeholder="smtp.example.com" />
          </label>
          <label>
            Check type
            <input value={readinessFilters.check_type} onChange={(event) => updateReadinessFilter('check_type', event.target.value)} placeholder="mta_smoke" />
          </label>
        </div>
        <div className="button-row">
          <button className="ghost" onClick={loadReadinessChecks} disabled={busy}>Apply Readiness Filters</button>
          <button className="ghost" onClick={() => setReadinessFilters({ status: '', domain: '', host: '', check_type: '' })} disabled={busy}>Clear Readiness Filters</button>
        </div>
        {readinessChecks.length ? (
          <>
            <div className="readiness-status-strip" aria-label="Managed SMTP readiness status strip">
              <div className={`readiness-status-item ${readinessWarningCount ? 'warn' : 'good'}`}>
                <span>Loaded checks</span>
                <strong>{formatInt(readinessChecks.length)}</strong>
                <small>{formatInt(readinessSummary?.total_count ?? readinessCheckTotal)} readiness check(s) match the filters.</small>
              </div>
              <div className={`readiness-status-item ${readinessWarningCount ? 'warn' : 'good'}`}>
                <span>Needs review</span>
                <strong>{formatInt(readinessWarningCount)}</strong>
                <small>{formatInt(readinessSummary?.failed_count || 0)} failed, {formatInt(readinessSummary?.warning_count || 0)} warning.</small>
              </div>
              <div className={`readiness-status-item ${readinessSummary?.ok_count ? 'good' : 'warn'}`}>
                <span>Passing checks</span>
                <strong>{formatInt(readinessSummary?.ok_count || 0)}</strong>
                <small>Backend readiness summary across matching checks.</small>
              </div>
              <div className={`readiness-status-item ${readinessTrend?.trend === 'regressing' ? 'warn' : 'good'}`}>
                <span>Recent trend</span>
                <strong>{readinessTrend?.trend || 'Not loaded'}</strong>
                <small>{readinessTrend ? `${formatPct(readinessTrend.failure_rate)} failure rate across ${formatInt(readinessTrend.sample_size)} recent check(s).` : 'Load readiness to calculate trend.'}</small>
              </div>
              <div className={`readiness-status-item ${readinessTrend && ['critical', 'warning'].includes(readinessTrend.alert_status) ? 'warn' : 'good'}`}>
                <span>Trend alert</span>
                <strong>{readinessTrend?.alert_status || 'Not loaded'}</strong>
                <small>{readinessTrend?.alert_reasons?.[0] || 'Load readiness to classify managed SMTP health.'}</small>
              </div>
              <div className={`readiness-status-item ${readinessTrend && readinessTrend.latest_window_failure_rate > readinessTrend.previous_window_failure_rate ? 'warn' : 'good'}`}>
                <span>Window comparison</span>
                <strong>{readinessTrend ? `${formatPct(readinessTrend.latest_window_failure_rate)} / ${formatPct(readinessTrend.previous_window_failure_rate)}` : '-'}</strong>
                <small>Latest window failure rate versus previous window.</small>
              </div>
              <div className={`readiness-status-item ${readinessNotification?.should_notify ? 'warn' : 'good'}`}>
                <span>Notification payload</span>
                <strong>{readinessNotification?.severity || 'Not loaded'}</strong>
                <small>{readinessNotification ? readinessNotification.title : 'Load readiness to prepare external alert payload.'}</small>
              </div>
              <div className={`readiness-status-item ${latestReadinessCheck?.status === 'ok' ? 'good' : 'warn'}`}>
                <span>Latest check</span>
                <strong>{latestReadinessCheck?.status || 'None'}</strong>
                <small>{latestReadinessCheck?.summary || latestReadinessCheck?.created_at || 'No readiness result loaded.'}</small>
              </div>
              <div className={`readiness-status-item ${latestSuccessfulReadiness ? 'good' : 'warn'}`}>
                <span>Latest pass</span>
                <strong>{latestSuccessfulReadiness ? latestSuccessfulReadiness.created_at : 'None'}</strong>
                <small>{latestSuccessfulReadiness?.host || latestSuccessfulReadiness?.domain || 'No passing MTA smoke visible in loaded checks.'}</small>
              </div>
            </div>
            {readinessNotification ? (
              <div className="operation-banner">
                <strong>{readinessNotification.should_notify ? 'Ready to notify' : 'Notification quiet'}</strong>
                <span>{readinessNotification.message} Dedupe: {readinessNotification.dedupe_key}</span>
              </div>
            ) : null}
            {readinessAlerts?.alert_checks?.length ? (
              <div className="provider-feedback-list">
                {readinessAlerts.alert_checks.slice(0, 4).map((check) => (
                  <article className="warn" key={`alert-${check.id}`}>
                    <div>
                      <span>Alert evidence</span>
                      <strong>{check.summary || `${check.status} readiness check`}</strong>
                    </div>
                    <small>{check.created_at}</small>
                    <dl>
                      <div><dt>status</dt><dd>{check.status}</dd></div>
                      <div><dt>domain</dt><dd>{check.domain || '-'}</dd></div>
                      <div><dt>host</dt><dd>{check.host || '-'}</dd></div>
                      <div><dt>reason</dt><dd>{readinessAlerts.alert_reasons[0] || readinessAlerts.alert_status}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            ) : null}
            <div className="provider-feedback-list">
              {readinessChecks.slice(0, 8).map((check) => (
                <article className={check.status === 'ok' ? 'good' : 'warn'} key={check.id}>
                  <div>
                    <span>{check.source} / {check.check_type}</span>
                    <strong>{check.summary || check.status}</strong>
                  </div>
                  <small>{check.created_at}</small>
                  <dl>
                    <div><dt>status</dt><dd>{check.status}</dd></div>
                    <div><dt>domain</dt><dd>{check.domain || '-'}</dd></div>
                    <div><dt>host</dt><dd>{check.host || '-'}</dd></div>
                    <div><dt>check</dt><dd>{check.id.slice(0, 8)}</dd></div>
                  </dl>
                  <details>
                    <summary>Readiness result</summary>
                    <pre className="json-preview">{JSON.stringify(check.result_json, null, 2)}</pre>
                  </details>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="ai-empty-state">
            <strong>No managed SMTP readiness checks loaded</strong>
            <span>Load SMTP Readiness after publishing smoke results from the managed MTA host.</span>
          </div>
        )}
      </section>
      <section className="panel full-span provider-feedback-panel">
        <div className="panel-head">
          <div>
            <h2>Provider Feedback Evidence</h2>
            <span className="muted">Retained raw provider and managed-SMTP feedback for DSN, bounce, complaint, and duplicate-event review.</span>
          </div>
          <button className="link-button" onClick={loadProviderFeedbackEvents} disabled={busy}>Load Provider Feedback</button>
        </div>
        <div className="form-grid">
          <label>
            Provider
            <input value={feedbackFilters.provider} onChange={(event) => updateFeedbackFilter('provider', event.target.value)} placeholder="managed_smtp" />
          </label>
          <label>
            Source
            <input value={feedbackFilters.source} onChange={(event) => updateFeedbackFilter('source', event.target.value)} placeholder="managed_smtp_dsn_feedback" />
          </label>
          <label>
            Event
            <input value={feedbackFilters.event_name} onChange={(event) => updateFeedbackFilter('event_name', event.target.value)} placeholder="dsn_bounce" />
          </label>
          <label>
            Email
            <input value={feedbackFilters.email} onChange={(event) => updateFeedbackFilter('email', event.target.value)} placeholder="recipient@example.com" />
          </label>
          <label className="wide-field">
            Provider message ID
            <input value={feedbackFilters.provider_message_id} onChange={(event) => updateFeedbackFilter('provider_message_id', event.target.value)} placeholder="Postfix queue ID or provider message ID" />
          </label>
        </div>
        <div className="button-row">
          <button className="ghost" onClick={useSelectedRecordForFeedbackFilters} disabled={busy || !selectedRecordId}>Use Selected Record</button>
          <button className="ghost" onClick={loadProviderFeedbackEvents} disabled={busy}>Load Provider Feedback</button>
        </div>
        {providerFeedbackEvents.length ? (
          <>
            <div className="provider-feedback-strip" aria-label="Managed SMTP provider feedback strip">
              <div className={`provider-feedback-strip-item ${providerFeedbackWarningCount ? 'warn' : 'good'}`}>
                <span>Loaded events</span>
                <strong>{formatInt(providerFeedbackEvents.length)}</strong>
                <small>{formatInt(providerFeedbackTotal)} retained event(s) match the filters.</small>
              </div>
              <div className={`provider-feedback-strip-item ${providerFeedbackWarningCount ? 'warn' : 'good'}`}>
                <span>Review signals</span>
                <strong>{formatInt(providerFeedbackWarningCount)}</strong>
                <small>Bounce, complaint, deferral, and DSN warning events.</small>
              </div>
            </div>
            <div className="provider-feedback-list">
              {providerFeedbackEvents.slice(0, 8).map((event) => {
                const metadata = event.metadata_json || {};
                const tone = ['dsn_bounce', 'bounce', 'complaint', 'tempfail', 'deferred'].includes(event.event_name) ? 'warn' : 'good';
                return (
                  <article className={tone} key={event.id}>
                    <div>
                      <span>{event.provider} / {event.source}</span>
                      <strong>{event.event_name} for {event.email}</strong>
                    </div>
                    <small>{event.received_at}</small>
                    <dl>
                      <div><dt>message</dt><dd>{event.provider_message_id || '-'}</dd></div>
                      <div><dt>idempotency</dt><dd>{event.idempotency_key.slice(0, 18)}</dd></div>
                      <div><dt>status</dt><dd>{String(metadata.dsn_status || metadata.smtp_status || '-')}</dd></div>
                      <div><dt>source key</dt><dd>{String(metadata.postfix_queue_id || metadata.maildir_key || '-')}</dd></div>
                    </dl>
                    <details>
                      <summary>Payload and metadata</summary>
                      <pre className="json-preview">{JSON.stringify({ payload: event.payload_json, metadata: event.metadata_json }, null, 2)}</pre>
                    </details>
                  </article>
                );
              })}
            </div>
          </>
        ) : (
          <div className="ai-empty-state">
            <strong>No provider feedback evidence loaded</strong>
            <span>Load Provider Feedback to inspect retained raw DSN, MTA log, SendGrid, and managed-SMTP feedback events.</span>
          </div>
        )}
      </section>
      {progress ? (
        <section className="metric-grid full-span compact-metrics">
          <MetricCard metric={{ label: 'Processed', value: formatInt(progress.processed_count), change: `${formatInt(progress.remaining_count)} remaining` }} />
          <MetricCard metric={{ label: 'Queued', value: formatInt(progress.queued_count), change: `${formatInt(progress.sending_count)} sending`, tone: progress.queued_count ? 'warn' : 'good' }} />
          <MetricCard metric={{ label: 'Sent', value: formatInt(progress.sent_count), change: 'completed sends' }} />
          <MetricCard metric={{ label: 'Failed', value: formatInt(progress.failed_count), change: `${formatInt(progress.skipped_count)} skipped`, tone: progress.failed_count ? 'warn' : 'good' }} />
          <MetricCard metric={{ label: 'Dead-lettered', value: formatInt(progress.dead_lettered_count || 0), change: 'terminal queue records', tone: progress.dead_lettered_count ? 'warn' : 'good' }} />
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
  const isNewSuppression = routeParts[0] === 'compliance' && routeParts[1] === 'new';

  useEffect(() => {
    if (isNewSuppression) {
      resetSuppressionEditor();
    } else if (routeSuppressionId) {
      const suppression = suppressions.find((item) => item.id === routeSuppressionId);
      if (suppression && selectedSuppressionId !== suppression.id) loadSuppression(suppression);
    } else if (!selectedSuppressionId && suppressions.length) {
      setSelectedSuppressionId(suppressions[0].id);
    }
  }, [isNewSuppression, routeSuppressionId, selectedSuppressionId, suppressions]);

  const manualCount = suppressions.filter((item) => item.reason === 'manual').length;
  const unsubscribeCount = suppressions.filter((item) => item.reason === 'unsubscribe').length;
  const bounceCount = suppressions.filter((item) => item.reason === 'hard_bounce').length;
  const complaintCount = suppressions.filter((item) => item.reason === 'spam_complaint').length;
  const failedWithEmail = sendRecords.filter((record) => record.status === 'failed' && record.to_email).slice(0, 10);
  const failedCandidateCount = sendRecords.filter((record) => record.status === 'failed' && record.to_email).length;
  const providerSuppressionCount = suppressions.filter((item) => item.provider_message_id).length;
  const selectedSuppression = suppressions.find((item) => item.id === selectedSuppressionId);
  const isPersistedSuppression = Boolean(selectedSuppressionId);
  const isCreatingSuppression = !isPersistedSuppression;
  const complianceFeedbackItems = [
    {
      label: 'Provider feedback',
      value: providerSuppressionCount ? 'Linked' : 'Gap',
      detail: providerSuppressionCount ? `${formatInt(providerSuppressionCount)} provider-linked suppression(s).` : 'Provider webhooks need to feed durable bounce and complaint events.',
      tone: providerSuppressionCount ? 'good' : 'warn',
    },
    {
      label: 'Bounce queue',
      value: bounceCount ? 'Protected' : 'Gap',
      detail: bounceCount ? `${formatInt(bounceCount)} hard bounce suppression(s) block future sends.` : 'Hard bounces need a dedicated review queue before retry decisions.',
      tone: bounceCount ? 'good' : 'warn',
    },
    {
      label: 'Complaint loop',
      value: complaintCount ? 'Risk' : 'Gap',
      detail: complaintCount ? `${formatInt(complaintCount)} spam complaint suppression(s) require deliverability review.` : 'Spam complaints need a feedback loop tied to reputation and suppression policy.',
      tone: 'warn',
    },
    {
      label: 'Retry safety',
      value: failedCandidateCount ? 'Review' : 'Clear',
      detail: failedCandidateCount ? `${formatInt(failedCandidateCount)} failed recipient(s) should be classified before requeue.` : 'No failed recipient candidates visible for suppression review.',
      tone: failedCandidateCount ? 'warn' : 'good',
    },
  ];
  const complianceFoundationItems = [
    {
      label: 'Consent ledger',
      value: unsubscribeCount || manualCount ? 'Partial' : 'Gap',
      detail: unsubscribeCount || manualCount
        ? 'Suppression records preserve source context, but full consent history still needs durable event storage.'
        : 'Consent capture, source attribution, and historical proof need a canonical ledger.',
      tone: 'warn',
    },
    {
      label: 'Preference center',
      value: 'Gap',
      detail: 'Contacts still need self-service preferences beyond global suppression records.',
      tone: 'warn',
    },
    {
      label: 'Suppression propagation',
      value: suppressions.length ? 'Active' : 'Gap',
      detail: suppressions.length
        ? 'Suppression checks can protect send workflows while provider sync is expanded.'
        : 'Suppressions must propagate to campaign, journey, and delivery execution before launch.',
      tone: suppressions.length ? 'good' : 'warn',
    },
    {
      label: 'Audit trail',
      value: providerSuppressionCount ? 'Provider linked' : 'Gap',
      detail: providerSuppressionCount
        ? 'Provider message references support incident review for some suppressions.'
        : 'Operator changes, provider events, and policy decisions need immutable audit history.',
      tone: providerSuppressionCount ? 'good' : 'warn',
    },
  ];
  const compliancePolicyContractItems = [
    {
      label: 'Suppression scope',
      value: suppressions.length ? 'Active' : 'Gap',
      detail: 'Suppression policy must define whether a block applies globally, by brand, by domain, or by campaign family.',
      tone: suppressions.length ? 'good' : 'warn',
    },
    {
      label: 'Bounce disposition',
      value: bounceCount ? 'Protected' : 'Gap',
      detail: 'Hard bounces should become permanent suppressions while soft bounces need retry windows and escalation rules.',
      tone: bounceCount ? 'good' : 'warn',
    },
    {
      label: 'Complaint disposition',
      value: complaintCount ? 'Risk' : 'Gap',
      detail: 'Spam complaints must permanently suppress recipients and trigger reputation review before future sends.',
      tone: 'warn',
    },
    {
      label: 'Retry block',
      value: failedCandidateCount ? 'Review' : 'Clear',
      detail: 'Failed delivery records should check suppression, complaint, and bounce policy before any requeue action.',
      tone: failedCandidateCount ? 'warn' : 'good',
    },
    {
      label: 'Provider traceability',
      value: providerSuppressionCount ? 'Linked' : 'Gap',
      detail: 'Provider event IDs, SMTP log IDs, and operator decisions need to stay attached to each suppression.',
      tone: providerSuppressionCount ? 'good' : 'warn',
    },
    {
      label: 'Audit evidence',
      value: 'Gap',
      detail: 'Compliance actions need immutable evidence for source, actor, timestamp, policy version, and downstream propagation.',
      tone: 'warn',
    },
  ];
  const complianceTriageAction = complaintCount
    ? {
      tone: 'warn',
      title: 'Review spam complaints',
      detail: `${formatInt(complaintCount)} complaint suppression(s) should block retries and trigger deliverability review.`,
      actionLabel: 'Open Delivery',
      run: () => { window.location.hash = '#delivery'; },
      disabled: busy,
    }
    : bounceCount
      ? {
        tone: 'warn',
        title: 'Watch hard bounces',
        detail: `${formatInt(bounceCount)} hard bounce suppression(s) are protecting future launches.`,
        actionLabel: 'Open Delivery',
        run: () => { window.location.hash = '#delivery'; },
        disabled: busy,
      }
      : failedCandidateCount
        ? {
          tone: 'warn',
          title: 'Suppress failed recipients',
          detail: `${formatInt(failedCandidateCount)} failed delivery recipient(s) can be reviewed before blind retries.`,
          actionLabel: 'Add Suppression',
          run: () => { window.location.hash = '#compliance/new'; },
          disabled: busy,
        }
        : unsubscribeCount
          ? {
            tone: 'warn',
            title: 'Respect opt-outs',
            detail: `${formatInt(unsubscribeCount)} unsubscribe suppression(s) are active for compliance checks.`,
            actionLabel: 'Open Analytics',
            run: () => { window.location.hash = '#analytics'; },
            disabled: busy,
          }
          : {
            tone: 'good',
            title: 'Compliance clear',
            detail: 'No complaint, bounce, unsubscribe, or failed-recipient pressure is visible.',
            actionLabel: 'Add Suppression',
            run: () => { window.location.hash = '#compliance/new'; },
            disabled: busy,
          };
  const complianceTriageItems = [
    {
      label: 'Complaint risk',
      value: formatInt(complaintCount),
      detail: complaintCount ? 'Treat complaints as permanent suppression and deliverability risk.' : 'No spam complaints visible',
      tone: complaintCount ? 'warn' : 'good',
    },
    {
      label: 'Bounce protection',
      value: formatInt(bounceCount),
      detail: bounceCount ? 'Hard bounces should stay suppressed before any requeue.' : 'No hard-bounce suppressions visible',
      tone: bounceCount ? 'warn' : 'good',
    },
    {
      label: 'Opt-out coverage',
      value: formatInt(unsubscribeCount),
      detail: unsubscribeCount ? 'Unsubscribed contacts are excluded from future sends.' : 'No unsubscribe suppressions visible',
      tone: unsubscribeCount ? 'warn' : 'good',
    },
    {
      label: 'Failed candidates',
      value: formatInt(failedCandidateCount),
      detail: providerSuppressionCount ? `${formatInt(providerSuppressionCount)} provider-linked suppression(s)` : 'Review delivery failures before retrying',
      tone: failedCandidateCount ? 'warn' : 'good',
    },
  ];

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

  function draftSuppressionFromRecord(record: EmailSendRecordRead) {
    setSelectedSuppressionId('');
    setEmail(record.to_email);
    setReason('manual');
    setSource(`delivery_failure:${providerLabel(record.provider)}`);
    setStatus(`Drafting suppression for failed delivery recipient ${record.to_email}.`);
    window.location.hash = '#compliance/new';
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

  async function deleteSuppressionRow(item: SuppressionRead) {
    if (!window.confirm(`Delete suppression for "${item.email}"?`)) return;
    await runComplianceOperation('Deleting suppression', async () => {
      await fetchJson<{ id: string }>(`/api/v1/suppressions/${item.id}`, { method: 'DELETE' });
      if (selectedSuppressionId === item.id) resetSuppressionEditor();
      await onRefresh();
      return `Deleted suppression for ${item.email}.`;
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
          <section className={`compliance-triage-panel full-span ${complianceTriageAction.tone}`}>
            <div className="compliance-triage-head">
              <div>
                <span>Compliance triage</span>
                <strong>{complianceTriageAction.title}</strong>
                <small>{complianceTriageAction.detail}</small>
              </div>
              <button className={complianceTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={complianceTriageAction.run} disabled={complianceTriageAction.disabled}>{complianceTriageAction.actionLabel}</button>
            </div>
            <div className="compliance-triage-grid">
              {complianceTriageItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
          <section className="compliance-feedback-panel full-span">
            <div className="panel-head compact-head">
              <div>
                <h3>Deliverability Feedback Loop</h3>
                <span className="muted">Provider events, bounce queues, complaint handling, and retry safety.</span>
              </div>
              <a href="#delivery">Open Delivery</a>
            </div>
            <div className="compliance-feedback-grid">
              {complianceFeedbackItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
          <section className="compliance-foundation-panel full-span">
            <div className="panel-head compact-head">
              <div>
                <h3>Compliance Foundations</h3>
                <span className="muted">Consent ledger, preference center, suppression propagation, and audit readiness.</span>
              </div>
              <a href="#contacts">Open Contacts</a>
            </div>
            <div className="compliance-foundation-grid">
              {complianceFoundationItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
          <section className="compliance-policy-panel full-span">
            <div className="panel-head compact-head">
              <div>
                <h3>Feedback Policy Contract</h3>
                <span className="muted">Suppression scope, bounce and complaint disposition, retry blocking, traceability, and audit evidence.</span>
              </div>
              <a href="#delivery">Open Delivery</a>
            </div>
            <div className="compliance-policy-grid">
              {compliancePolicyContractItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>
          {failedWithEmail.length ? (
            <section className="panel table-panel full-span compliance-candidate-panel">
              <div className="panel-head">
                <div>
                  <h2>Failed Recipient Review</h2>
                  <span className="muted">Draft suppressions from failed delivery records before retrying.</span>
                </div>
                <a href="#delivery">Open delivery</a>
              </div>
              <table>
                <thead><tr><th>Email</th><th>Status</th><th>Provider</th><th>Attempts</th><th>Error</th><th>Suppression</th></tr></thead>
                <tbody>
                  {failedWithEmail.map((record) => (
                    <tr key={record.id}>
                      <td>{record.to_email}</td>
                      <td><span className="pill">{record.status}</span></td>
                      <td>{providerLabel(record.provider)}</td>
                      <td>{record.attempt_count} / {record.max_attempts}</td>
                      <td>{record.error_message || '-'}</td>
                      <td><button className="ghost compact-button" type="button" onClick={() => draftSuppressionFromRecord(record)} disabled={busy}>Draft Suppression</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}
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
	                      onDoubleClick={() => { window.location.hash = `#compliance/${item.id}`; }}
	                    >
                      <td>{item.email}</td>
                      <td><span className="pill">{item.reason}</span></td>
                      <td>{item.source}</td>
                      <td>{item.provider_message_id || '-'}</td>
                      <td>{item.contact_id ? item.contact_id.slice(0, 8) : '-'}</td>
                      <td><RowActionMenu openHref={`#compliance/${item.id}`} onDelete={() => deleteSuppressionRow(item)} /></td>
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
          <div className="campaign-action-bar">
            <div>
              <strong>Suppression</strong>
              <button className="primary" onClick={addSuppression} disabled={busy}>{isCreatingSuppression ? 'Add Suppression' : 'Add Another'}</button>
              {isPersistedSuppression ? <button className="ghost" onClick={deleteSuppression} disabled={busy}>Delete Selected</button> : null}
            </div>
            <div>
              <strong>Data</strong>
              <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh Suppressions</button>
            </div>
          </div>
          <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
            <strong>{busy ? 'Working' : 'Status'}</strong>
            <span>{status}</span>
          </div>
          <div className={`compliance-triage-panel ${complianceTriageAction.tone}`}>
            <div className="compliance-triage-head">
              <div>
                <span>Compliance triage</span>
                <strong>{complianceTriageAction.title}</strong>
                <small>{complianceTriageAction.detail}</small>
              </div>
              <button className={complianceTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={complianceTriageAction.run} disabled={complianceTriageAction.disabled}>{complianceTriageAction.actionLabel}</button>
            </div>
            <div className="compliance-triage-grid">
              {complianceTriageItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </div>
          <div className="compliance-feedback-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Deliverability Feedback Loop</h3>
                <span className="muted">Provider events, bounce queues, complaint handling, and retry safety.</span>
              </div>
              <a href="#delivery">Open Delivery</a>
            </div>
            <div className="compliance-feedback-grid">
              {complianceFeedbackItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </div>
          <div className="compliance-foundation-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Compliance Foundations</h3>
                <span className="muted">Consent ledger, preference center, suppression propagation, and audit readiness.</span>
              </div>
              <a href="#contacts">Open Contacts</a>
            </div>
            <div className="compliance-foundation-grid">
              {complianceFoundationItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </div>
          <div className="compliance-policy-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Feedback Policy Contract</h3>
                <span className="muted">Suppression scope, bounce and complaint disposition, retry blocking, traceability, and audit evidence.</span>
              </div>
              <a href="#delivery">Open Delivery</a>
            </div>
            <div className="compliance-policy-grid">
              {compliancePolicyContractItems.map((item) => (
                <article className={item.tone} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.detail}</small>
                </article>
              ))}
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
              Selected provider message
              <input value={selectedSuppression?.provider_message_id || 'none'} readOnly />
            </label>
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
  const isNewSource = routeParts[0] === 'data' && routeParts[1] === 'new';

  useEffect(() => {
    if (isNewSource) {
      resetSourceEditor();
    } else if (routeSourceId) {
      const source = dataSources.find((item) => item.id === routeSourceId);
      if (source && selectedSourceId !== source.id) loadSource(source);
    } else if (!selectedSourceId && dataSources.length) {
      loadSource(dataSources[0]);
    }
  }, [dataSources, isNewSource, routeSourceId, selectedSourceId]);

  useEffect(() => {
    const sourceMappings = mappings.filter((mapping) => mapping.data_source_id === selectedSourceId);
    if (!selectedMappingId && sourceMappings.length) loadMapping(sourceMappings[0]);
  }, [mappings, selectedMappingId, selectedSourceId]);

  const sourceMappings = mappings.filter((mapping) => mapping.data_source_id === selectedSourceId);
  const selectedSource = dataSources.find((source) => source.id === selectedSourceId);
  const selectedMapping = mappings.find((mapping) => mapping.id === selectedMappingId);
  const isPersistedSource = Boolean(selectedSourceId);
  const isCreatingSource = !isPersistedSource;
  const completedJobs = importJobs.filter((job) => job.status === 'completed').length;
  const dryRunJobs = importJobs.filter((job) => job.status === 'dry_run').length;
  const failedJobs = importJobs.filter((job) => job.status === 'failed').length;
  const importedCount = importJobs.reduce((sum, job) => sum + Number(job.imported_count || 0), 0);
  const activeSources = dataSources.filter((source) => source.status === 'active').length;
  const mappedSourceCount = new Set(mappings.map((mapping) => mapping.data_source_id)).size;
  const skippedCount = importJobs.reduce((sum, job) => sum + Number(job.skipped_count || 0), 0);
  const importErrorCount = importJobs.reduce((sum, job) => sum + Number(job.errors?.length || 0), 0);
  const mappingCoverage = dataSources.length ? mappedSourceCount / dataSources.length : 0;
  const importReviewJobs = [...importJobs]
    .filter((job) => job.status === 'failed' || Number(job.skipped_count || 0) > 0 || (job.errors?.length || 0) > 0)
    .sort((a, b) => {
      const bWeight = (b.status === 'failed' ? 100 : 0) + Number(b.errors?.length || 0) + Number(b.skipped_count || 0);
      const aWeight = (a.status === 'failed' ? 100 : 0) + Number(a.errors?.length || 0) + Number(a.skipped_count || 0);
      return bWeight - aWeight;
    })
    .slice(0, 5);
  const dataNextAction = !dataSources.length
    ? 'Create a data source before importing contacts into the ESP.'
    : mappedSourceCount < dataSources.length
      ? 'Open unmapped sources and save contact field mappings before import.'
      : failedJobs > 0 || importErrorCount > 0
        ? 'Review failed import jobs and row errors before running another import.'
        : !completedJobs
          ? 'Run a dry run, inspect skipped rows, then import contacts.'
          : !selectedSource
          ? 'Select a source to inspect mapping and schema readiness.'
            : 'Data workflow is ready. Continue importing contacts or open Contacts to inspect results.';
  const inactiveSources = dataSources.filter((source) => source.status !== 'active').length;
  const selectedSourceMappings = mappings.filter((mapping) => mapping.data_source_id === selectedSourceId).length;
  const dataTriageAction = !selectedSourceId
    ? {
      tone: 'warn',
      title: 'Create data source',
      detail: 'Create or select a source before schema discovery, mapping, or ingest.',
      actionLabel: 'Create Source',
      run: () => { window.location.hash = '#data/new'; },
      disabled: busy,
    }
    : selectedSource?.status !== 'active'
      ? {
        tone: 'warn',
        title: 'Activate source',
        detail: `${selectedSource?.name || 'Selected source'} is ${selectedSource?.status || statusValue}; validate and activate before production import.`,
        actionLabel: 'Validate',
        run: validateSource,
        disabled: busy || !selectedSourceId,
      }
      : !validation
        ? {
          tone: 'warn',
          title: 'Validate source',
          detail: 'Run validation before trusting schema discovery or row ingest.',
          actionLabel: 'Validate',
          run: validateSource,
          disabled: busy || !selectedSourceId,
        }
        : !validation.ok
          ? {
            tone: 'warn',
            title: 'Fix validation errors',
            detail: `${formatInt(validation.errors.length)} validation issue(s) need config or credential updates.`,
            actionLabel: 'Validate',
            run: validateSource,
            disabled: busy || !selectedSourceId,
          }
          : !schema
            ? {
              tone: 'warn',
              title: 'Discover schema',
              detail: 'Load fields and sample rows before finalizing mapping.',
              actionLabel: 'Discover Schema',
              run: discoverSchema,
              disabled: busy || !selectedSourceId,
            }
            : !selectedMappingId
              ? {
                tone: 'warn',
                title: 'Save contact mapping',
                detail: 'Create a mapping so source rows can become contact records.',
                actionLabel: 'Save Mapping',
                run: saveMapping,
                disabled: busy || !selectedSourceId,
              }
              : failedJobs || importErrorCount || skippedCount
                ? {
                  tone: 'warn',
                  title: 'Review import results',
                  detail: `${formatInt(failedJobs)} failed job(s), ${formatInt(importErrorCount)} error(s), and ${formatInt(skippedCount)} skipped row(s) need review.`,
                  actionLabel: 'Dry Run',
                  run: () => ingestRows(true),
                  disabled: busy || !selectedMappingId,
                }
                : completedJobs || importedCount
                  ? {
                    tone: 'good',
                    title: 'Open imported contacts',
                    detail: `${formatInt(importedCount)} imported row(s) are available for contact and audience review.`,
                    actionLabel: 'Open Contacts',
                    run: () => { window.location.hash = '#contacts'; },
                    disabled: busy,
                  }
                  : {
                    tone: 'warn',
                    title: 'Run import dry run',
                    detail: 'Dry-run rows before importing contacts into the canonical model.',
                    actionLabel: 'Dry Run',
                    run: () => ingestRows(true),
                    disabled: busy || !selectedMappingId,
                  };
  const dataTriageItems = [
    {
      label: 'Source readiness',
      value: `${formatInt(activeSources)} active`,
      detail: inactiveSources ? `${formatInt(inactiveSources)} draft or paused source(s)` : 'All configured sources are active',
      tone: activeSources && !inactiveSources ? 'good' : 'warn',
    },
    {
      label: 'Mapping coverage',
      value: formatPct(mappingCoverage),
      detail: selectedSourceId ? `${formatInt(selectedSourceMappings)} selected-source mapping(s)` : `${formatInt(mappedSourceCount)} mapped source(s)`,
      tone: mappingCoverage >= 1 && dataSources.length ? 'good' : 'warn',
    },
    {
      label: 'Validation state',
      value: validation ? (validation.ok ? 'Passed' : 'Failed') : 'Not checked',
      detail: validation ? `${formatInt(validation.checks.length)} check(s), ${formatInt(validation.errors.length)} error(s)` : 'Run validation before import',
      tone: validation?.ok ? 'good' : 'warn',
    },
    {
      label: 'Import health',
      value: `${formatInt(importedCount)} rows`,
      detail: `${formatInt(failedJobs)} failed job(s), ${formatInt(skippedCount)} skipped row(s), ${formatInt(importErrorCount)} error(s)`,
      tone: failedJobs || skippedCount || importErrorCount ? 'warn' : 'good',
    },
  ];
  const schemaFieldNames = schema?.fields?.map((field) => field.name) || [];
  const mappingPreview = (() => {
    try {
      const parsed = parseJsonObject(mappingJson, 'mapping preview');
      const attributes = parsed.attributes && typeof parsed.attributes === 'object' && !Array.isArray(parsed.attributes)
        ? parsed.attributes as Record<string, unknown>
        : {};
      return {
        directFields: Object.entries(parsed).filter(([key]) => key !== 'attributes'),
        attributeFields: Object.entries(attributes),
      };
    } catch {
      return { directFields: [], attributeFields: [] };
    }
  })();
  const dataConfigPreview = (() => {
    try {
      return parseJsonObject(configJson, 'config preview');
    } catch {
      return {};
    }
  })();
  const relationshipSourceType = selectedSource?.source_type || sourceType;
  const relationshipFieldNames = schemaFieldNames.length
    ? schemaFieldNames
    : Object.keys(dataConfigPreview).filter((key) => key !== 'sample_rows' && key !== 'fields');
  const relationshipJoinFields = relationshipFieldNames.filter((field) => /(^id$|_id$|email|customer|account|company|contact)/i.test(field));
  const relationshipPlanStatus = ['postgres', 'mysql', 'snowflake', 'bigquery'].includes(relationshipSourceType)
    ? {
      tone: schema ? 'good' : 'warn',
      title: schema ? 'Relational schema ready' : 'Discover relational schema',
      detail: schema ? 'Use discovered keys to plan joins before canonical contact import.' : 'RDBMS and warehouse joins need schema discovery before entity mapping.',
    }
    : relationshipSourceType === 'rest_api'
      ? {
        tone: 'warn',
        title: 'Plan API entity graph',
        detail: 'REST connectors need endpoint-to-entity mapping before joins can be automated.',
      }
      : {
        tone: 'warn',
        title: 'Single-entity import',
        detail: 'Manual and CSV imports currently land as contact rows; model joins as a platform gap.',
      };
  const relationshipPlannerItems = [
    {
      label: 'Connector class',
      value: relationshipSourceType,
      detail: ['postgres', 'mysql'].includes(relationshipSourceType)
        ? 'RDBMS connector'
        : ['snowflake', 'bigquery'].includes(relationshipSourceType)
          ? 'Warehouse connector'
          : relationshipSourceType === 'rest_api'
            ? 'API connector'
            : 'Flat-file/manual connector',
      tone: ['postgres', 'mysql', 'snowflake', 'bigquery'].includes(relationshipSourceType) ? 'good' : 'warn',
    },
    {
      label: 'Join keys',
      value: formatInt(relationshipJoinFields.length),
      detail: relationshipJoinFields.slice(0, 4).join(', ') || 'No join-like keys discovered',
      tone: relationshipJoinFields.length ? 'good' : 'warn',
    },
    {
      label: 'Entity targets',
      value: schema?.object_types?.length ? formatInt(schema.object_types.length) : 'Contact',
      detail: schema?.object_types?.join(', ') || 'Canonical contact only',
      tone: schema?.object_types?.length && schema.object_types.length > 1 ? 'good' : 'warn',
    },
    {
      label: 'Client entities',
      value: 'Gap',
      detail: 'Client-owned entities still need canonical storage and relationship APIs',
      tone: 'warn',
    },
  ];
  const dataFoundationItems = [
    {
      label: 'Connector credentials',
      value: dataSources.some((source) => source.secret_ref) ? 'Linked' : 'Gap',
      detail: dataSources.some((source) => source.secret_ref)
        ? 'At least one source has a secret reference for managed credentials.'
        : 'External connectors need managed secrets, rotation policy, and credential health checks.',
      tone: dataSources.some((source) => source.secret_ref) ? 'good' : 'warn',
    },
    {
      label: 'Sync cadence',
      value: completedJobs || dryRunJobs ? 'Manual runs' : 'Gap',
      detail: completedJobs || dryRunJobs
        ? 'Manual import jobs exist; scheduled sync still needs durable orchestration.'
        : 'Scheduled sync, incremental cursors, and backfill controls remain foundation work.',
      tone: 'warn',
    },
    {
      label: 'Canonical entities',
      value: schema?.object_types?.length ? formatInt(schema.object_types.length) : 'Contact',
      detail: schema?.object_types?.length && schema.object_types.length > 1
        ? 'Discovered schema exposes multiple object targets for entity planning.'
        : 'Client-specific entities need canonical storage before multi-entity segmentation.',
      tone: schema?.object_types?.length && schema.object_types.length > 1 ? 'good' : 'warn',
    },
    {
      label: 'Lineage and replay',
      value: importJobs.length ? `${formatInt(importJobs.length)} jobs` : 'Gap',
      detail: importJobs.length
        ? 'Import job history gives basic lineage; replay and row-level provenance still need hardening.'
        : 'Row lineage, replay, and rollback controls are needed before production data sync.',
      tone: 'warn',
    },
  ];
  const dataSyncContractItems = [
    {
      label: 'Credential contract',
      value: dataSources.some((source) => source.secret_ref) ? 'Linked' : 'Gap',
      detail: 'Every production connector needs secret references, rotation metadata, and validation status exposed in the UI.',
      tone: dataSources.some((source) => source.secret_ref) ? 'good' : 'warn',
    },
    {
      label: 'Schema contract',
      value: schema?.fields?.length ? `${formatInt(schema.fields.length)} fields` : 'Pending',
      detail: 'Connectors should publish discovered fields, object types, join candidates, and sample rows before mapping.',
      tone: schema?.fields?.length ? 'good' : 'warn',
    },
    {
      label: 'Sync contract',
      value: completedJobs || dryRunJobs ? 'Manual only' : 'Gap',
      detail: 'Production sync needs schedule policy, incremental cursor state, retry rules, and backfill windows.',
      tone: 'warn',
    },
    {
      label: 'Relationship contract',
      value: relationshipJoinFields.length ? `${formatInt(relationshipJoinFields.length)} keys` : 'Gap',
      detail: 'Multi-entity joins need canonical IDs, relationship cardinality, and client-owned entity storage.',
      tone: relationshipJoinFields.length ? 'good' : 'warn',
    },
    {
      label: 'Audit contract',
      value: importJobs.length ? `${formatInt(importJobs.length)} jobs` : 'Gap',
      detail: 'Ingest records need row provenance, replay controls, rollback markers, and operator-visible failure reasons.',
      tone: importJobs.length ? 'good' : 'warn',
    },
  ];

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

  function fieldByAliases(aliases: string[]) {
    const normalized = schemaFieldNames.map((field) => ({ field, key: field.toLowerCase().replace(/[^a-z0-9]/g, '') }));
    return aliases.map((alias) => alias.toLowerCase().replace(/[^a-z0-9]/g, ''))
      .map((alias) => normalized.find((item) => item.key === alias || item.key.includes(alias))?.field)
      .find(Boolean) || '';
  }

  function applySchemaMappingSuggestion() {
    if (!schema?.fields?.length) {
      setStatus('Discover schema before generating a mapping suggestion.');
      return;
    }
    const used = new Set<string>();
    const directEntries = [
      ['email', fieldByAliases(['email', 'emailaddress'])],
      ['first_name', fieldByAliases(['first_name', 'firstname', 'fname', 'givenname'])],
      ['last_name', fieldByAliases(['last_name', 'lastname', 'lname', 'surname', 'familyname'])],
      ['source', fieldByAliases(['source', 'origin', 'signupsource'])],
    ].filter(([, field]) => {
      if (!field || used.has(field)) return false;
      used.add(field);
      return true;
    });
    const attributes = schema.fields
      .map((field) => field.name)
      .filter((field) => !used.has(field))
      .slice(0, 12)
      .reduce((acc, field) => ({ ...acc, [field]: field }), {} as Record<string, string>);
    const suggested = {
      ...Object.fromEntries(directEntries),
      ...(Object.keys(attributes).length ? { attributes } : {}),
    };
    setMappingJson(JSON.stringify(suggested, null, 2));
    setStatus(`Suggested mapping from ${formatInt(schema.fields.length)} discovered field(s).`);
  }

  function focusImportJob(job: DataSourceImportJobRead) {
    const source = dataSources.find((item) => item.id === job.data_source_id);
    const mapping = mappings.find((item) => item.id === job.mapping_id);
    if (source) loadSource(source);
    if (mapping) loadMapping(mapping);
    setStatus(`Focused import job ${job.id.slice(0, 8)}: ${formatInt(job.imported_count)} imported, ${formatInt(job.skipped_count)} skipped, ${formatInt(job.errors?.length || 0)} error(s).`);
    window.location.hash = source ? `#data/${source.id}` : '#data';
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

  async function deleteSourceRow(source: DataSourceRead) {
    if (!window.confirm(`Delete data source "${source.name}"?`)) return;
    await runDataOperation('Deleting data source', async () => {
      await fetchJson<{ id: string }>(`/api/v1/data-sources/${source.id}`, { method: 'DELETE' });
      if (selectedSourceId === source.id) resetSourceEditor();
      await onRefresh();
      return `Deleted data source: ${source.name}.`;
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
        <section className={`data-triage-panel full-span ${dataTriageAction.tone}`}>
          <div className="data-triage-head">
            <div>
              <span>Data triage</span>
              <strong>{dataTriageAction.title}</strong>
              <small>{dataTriageAction.detail}</small>
            </div>
            <button className={dataTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={dataTriageAction.run} disabled={dataTriageAction.disabled}>{dataTriageAction.actionLabel}</button>
          </div>
          <div className="data-triage-grid">
            {dataTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="data-command-strip full-span" aria-label="Data readiness summary">
          <article className={activeSources ? 'good' : 'warn'}>
            <span>Sources</span>
            <strong>{formatInt(activeSources)} active</strong>
            <small>{formatInt(dataSources.length)} configured</small>
          </article>
          <article className={mappingCoverage >= 1 && dataSources.length ? 'good' : 'warn'}>
            <span>Mapping coverage</span>
            <strong>{formatPct(mappingCoverage)}</strong>
            <small>{formatInt(mappedSourceCount)} mapped sources</small>
          </article>
          <article className={failedJobs || importErrorCount ? 'warn' : 'good'}>
            <span>Import health</span>
            <strong>{formatInt(completedJobs)} completed</strong>
            <small>{formatInt(failedJobs)} failed / {formatInt(importErrorCount)} errors</small>
          </article>
          <article className={skippedCount ? 'warn' : 'good'}>
            <span>Rows</span>
            <strong>{formatInt(importedCount)} imported</strong>
            <small>{formatInt(skippedCount)} skipped</small>
          </article>
          <article className="wide">
            <span>Recommended next action</span>
            <strong>{dataNextAction}</strong>
            <small>{selectedSource?.name || 'No source selected'}</small>
          </article>
        </section>
        <section className="data-foundation-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Data Foundations</h3>
              <span className="muted">Connector credentials, sync cadence, canonical entities, and lineage readiness.</span>
            </div>
            <a href="#contacts">Open Contacts</a>
          </div>
          <div className="data-foundation-grid">
            {dataFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="data-sync-contract-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Connector Sync Contract</h3>
              <span className="muted">Required contracts before RDBMS, warehouse, NoSQL, API, and client-entity sync can be production-grade.</span>
            </div>
            <a href="#integrations">Open Integrations</a>
          </div>
          <div className="data-sync-contract-grid">
            {dataSyncContractItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
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
	                    onDoubleClick={() => { window.location.hash = `#data/${source.id}`; }}
	                  >
                    <td>{source.name}</td>
                    <td><span className="pill">{source.source_type}</span></td>
                    <td>{source.status}</td>
                    <td>{formatInt(mappings.filter((mapping) => mapping.data_source_id === source.id).length)}</td>
                    <td>{source.secret_ref || '-'}</td>
                    <td><RowActionMenu openHref={`#data/${source.id}`} onDelete={() => deleteSourceRow(source)} /></td>
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
        {importReviewJobs.length ? (
          <section className="panel table-panel full-span data-import-review-panel">
            <div className="panel-head">
              <div>
                <h2>Import Job Review</h2>
                <span className="muted">Review failed, skipped, or error-bearing import jobs before rerunning ingest.</span>
              </div>
              <button className="link-button" type="button" onClick={() => ingestRows(true)} disabled={busy || !selectedMappingId}>Dry Run Selected</button>
            </div>
            <table>
              <thead><tr><th>Job</th><th>Status</th><th>Source</th><th>Imported</th><th>Skipped</th><th>Errors</th><th>Sample error</th><th>Action</th></tr></thead>
              <tbody>
                {importReviewJobs.map((job) => {
                  const source = dataSources.find((item) => item.id === job.data_source_id);
                  const firstError = job.errors?.length ? JSON.stringify(job.errors[0]) : '-';
                  return (
                    <tr key={job.id}>
                      <td>{job.id.slice(0, 8)}</td>
                      <td><span className="pill">{job.status}</span></td>
                      <td>{source?.name || job.data_source_id.slice(0, 8)}</td>
                      <td>{formatInt(job.imported_count)}</td>
                      <td>{formatInt(job.skipped_count)}</td>
                      <td>{formatInt(job.errors?.length || 0)}</td>
                      <td>{firstError}</td>
                      <td><button className="ghost compact-button" type="button" onClick={() => focusImportJob(job)} disabled={busy}>Review Job</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ) : null}
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
        <div className="campaign-action-bar">
          <div>
            <strong>Source</strong>
            <button className="primary" onClick={saveSource} disabled={busy}>{isCreatingSource ? 'Create Source' : 'Save Changes'}</button>
            {isPersistedSource ? <button className="ghost" onClick={validateSource} disabled={busy}>Validate</button> : null}
            {isPersistedSource ? <button className="ghost" onClick={discoverSchema} disabled={busy}>Discover Schema</button> : null}
          </div>
          {isPersistedSource ? (
            <>
              <div>
                <strong>Mapping</strong>
                <button className="ghost" onClick={saveMapping} disabled={busy}>Save Mapping</button>
                <button className="ghost" onClick={applySchemaMappingSuggestion} disabled={busy || !schema?.fields?.length}>Suggest Mapping</button>
              </div>
              <div>
                <strong>Import</strong>
                <button className="ghost" onClick={() => ingestRows(true)} disabled={busy || !selectedMappingId}>Dry Run</button>
                <button className="ghost" onClick={() => ingestRows(false)} disabled={busy || !selectedMappingId}>Import Rows</button>
              </div>
            </>
          ) : null}
          <div>
            <strong>Data</strong>
            <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh</button>
          </div>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className={`data-triage-panel ${dataTriageAction.tone}`}>
          <div className="data-triage-head">
            <div>
              <span>Data triage</span>
              <strong>{dataTriageAction.title}</strong>
              <small>{dataTriageAction.detail}</small>
            </div>
            <button className={dataTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={dataTriageAction.run} disabled={dataTriageAction.disabled}>{dataTriageAction.actionLabel}</button>
          </div>
          <div className="data-triage-grid">
            {dataTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className={`data-relationship-planner ${relationshipPlanStatus.tone}`}>
          <div className="panel-head compact-head">
            <div>
              <h3>Relationship Planner</h3>
              <span className="muted">{relationshipPlanStatus.title}</span>
            </div>
            <button className="link-button" type="button" onClick={discoverSchema} disabled={busy || !selectedSourceId}>Discover Schema</button>
          </div>
          <p>{relationshipPlanStatus.detail}</p>
          <div className="data-relationship-grid">
            {relationshipPlannerItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="data-foundation-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Data Foundations</h3>
              <span className="muted">Connector credentials, sync cadence, canonical entities, and lineage readiness.</span>
            </div>
            <a href="#contacts">Open Contacts</a>
          </div>
          <div className="data-foundation-grid">
            {dataFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        {importReviewJobs.length ? (
          <div className="data-import-review-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Import Job Review</h3>
                <span className="muted">{formatInt(importReviewJobs.length)} job(s) need import review.</span>
              </div>
              <button className="link-button" type="button" onClick={() => ingestRows(true)} disabled={busy || !selectedMappingId}>Dry Run Selected</button>
            </div>
            <div className="compact-status-list">
              {importReviewJobs.slice(0, 3).map((job) => (
                <div className={job.status === 'failed' || job.errors?.length ? 'warn' : 'ready'} key={job.id}>
                  <strong>{job.status} import {job.id.slice(0, 8)}</strong>
                  <span>{formatInt(job.imported_count)} imported, {formatInt(job.skipped_count)} skipped, {formatInt(job.errors?.length || 0)} error(s).</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {schema?.fields?.length ? (
          <div className="data-mapping-helper-panel">
            <div className="panel-head compact-head">
              <div>
                <h3>Schema Mapping Helper</h3>
                <span className="muted">{formatInt(schema.fields.length)} discovered field(s), {formatInt(mappingPreview.directFields.length)} direct map(s), {formatInt(mappingPreview.attributeFields.length)} attribute map(s)</span>
              </div>
              <button className="link-button" type="button" onClick={applySchemaMappingSuggestion} disabled={busy}>Suggest Mapping</button>
            </div>
            <div className="data-mapping-helper-grid">
              <article>
                <span>Direct contact fields</span>
                <strong>{mappingPreview.directFields.map(([key]) => key).join(', ') || 'None'}</strong>
              </article>
              <article>
                <span>Attribute fields</span>
                <strong>{mappingPreview.attributeFields.slice(0, 8).map(([key]) => key).join(', ') || 'None'}</strong>
              </article>
              <article>
                <span>Unmapped schema fields</span>
                <strong>{schemaFieldNames.filter((field) => !mappingJson.includes(field)).slice(0, 8).join(', ') || 'None'}</strong>
              </article>
            </div>
          </div>
        ) : null}
        <div className="form-grid">
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
          {isPersistedSource && sourceMappings.length ? (
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
          ) : null}
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
  const isNewContact = routeParts[0] === 'contacts' && routeParts[1] === 'new';

  useEffect(() => {
    if (isNewContact) {
      resetContactEditor();
    } else if (routeContactId) {
      const contact = contacts.find((item) => item.id === routeContactId);
      if (contact && selectedContactId !== contact.id) loadContact(contact);
    } else if (!selectedContactId && contacts.length) {
      loadContact(contacts[0]);
    }
  }, [contacts, isNewContact, routeContactId, selectedContactId]);

  const unsubscribedCount = contacts.filter((contact) => contact.is_unsubscribed).length;
  const attributedCount = contacts.filter((contact) => Object.keys(contact.attributes || {}).length).length;
  const uniqueSources = new Set(contacts.map((contact) => contact.source).filter(Boolean)).size;
  const selectedContact = contacts.find((contact) => contact.id === selectedContactId);
  const isPersistedContact = Boolean(selectedContactId);
  const isCreatingContact = !isPersistedContact;
  const sourceRows = metadata?.sources || [];
  const attributeKeys = metadata?.attribute_keys || [];
  const totalContacts = metadata?.total || contacts.length;
  const metadataCoverage = totalContacts ? attributedCount / Math.max(contacts.length, 1) : 0;
  const unsubscribedRate = contacts.length ? unsubscribedCount / contacts.length : 0;
  const contactsNextAction = totalContacts === 0
    ? 'Import contacts before building audiences or launching campaigns.'
    : attributeKeys.length < 3
      ? 'Import or enrich attributes so audiences and templates have useful personalization fields.'
      : unsubscribedRate > 0.2
        ? 'Review unsubscribed contacts and suppressions before launching a new campaign.'
        : !selectedContact
          ? 'Select a contact to inspect profile data and compliance status.'
          : 'Contacts are ready for audience rules, template variables, and journey testing.';
  const contactsTriageAction = totalContacts === 0
    ? {
      tone: 'warn',
      title: 'Import contacts',
      detail: 'Load contacts through Data Sources before building audiences, journeys, or campaigns.',
      actionLabel: 'Open Data',
      run: () => { window.location.hash = '#data'; },
      disabled: busy,
    }
    : attributeKeys.length < 3
      ? {
        tone: 'warn',
        title: 'Enrich contact attributes',
        detail: `${formatInt(attributeKeys.length)} attribute key(s) are available; import richer profile fields for targeting and personalization.`,
        actionLabel: 'Open Data',
        run: () => { window.location.hash = '#data'; },
        disabled: busy,
      }
      : unsubscribedRate > 0.2
        ? {
          tone: 'warn',
          title: 'Review opt-outs',
          detail: `${formatPct(unsubscribedRate)} of visible contacts are unsubscribed. Review suppressions before launch.`,
          actionLabel: 'Open Compliance',
          run: () => { window.location.hash = '#compliance'; },
          disabled: busy,
        }
        : !selectedContact
          ? {
            tone: 'warn',
            title: 'Select contact',
            detail: 'Select a contact to inspect attributes, source, and compliance state.',
            actionLabel: 'Create Contact',
            run: () => { window.location.hash = '#contacts/new'; },
            disabled: busy,
          }
          : selectedContact.is_unsubscribed
            ? {
              tone: 'warn',
              title: 'Inspect unsubscribe state',
              detail: `${selectedContact.email} is unsubscribed. Generate a token or review compliance history.`,
              actionLabel: 'Unsubscribe Token',
              run: loadUnsubscribeToken,
              disabled: busy || !selectedContactId,
            }
            : {
              tone: 'good',
              title: 'Use contact data',
              detail: 'Contacts are ready for audience rules, template variables, and journey enrollment testing.',
              actionLabel: 'Open Audiences',
              run: () => { window.location.hash = '#audience'; },
              disabled: busy,
            };
  const contactsTriageItems = [
    {
      label: 'Contact base',
      value: formatInt(totalContacts),
      detail: `${formatInt(contacts.length)} visible row(s), ${formatInt(metadata?.scanned_count || contacts.length)} scanned`,
      tone: totalContacts ? 'good' : 'warn',
    },
    {
      label: 'Attribute coverage',
      value: `${formatInt(attributeKeys.length)} keys`,
      detail: `${formatPct(metadataCoverage)} of visible contacts have attributes`,
      tone: attributeKeys.length >= 3 && attributedCount ? 'good' : 'warn',
    },
    {
      label: 'Source diversity',
      value: formatInt(uniqueSources || sourceRows.length),
      detail: sourceRows[0]?.source ? `Top source: ${sourceRows[0].source}` : 'No source metadata loaded',
      tone: (uniqueSources || sourceRows.length) ? 'good' : 'warn',
    },
    {
      label: 'Compliance state',
      value: formatPct(unsubscribedRate),
      detail: `${formatInt(unsubscribedCount)} unsubscribed visible contact(s)`,
      tone: unsubscribedRate > 0.2 ? 'warn' : 'good',
    },
  ];
  const currentAttributePreview = (() => {
    try {
      return parseAttributes();
    } catch {
      return {} as Record<string, unknown>;
    }
  })();
  const activeAttributeKeys = Object.keys(currentAttributePreview);
  const missingAttributeKeys = attributeKeys.filter((key) => !activeAttributeKeys.includes(key));
  const contactEntityItems = [
    {
      label: 'Canonical contact',
      value: totalContacts ? 'Ready' : 'Empty',
      detail: `${formatInt(totalContacts)} contact profile(s) available for audiences, templates, and journeys.`,
      tone: totalContacts ? 'good' : 'warn',
    },
    {
      label: 'Profile attributes',
      value: `${formatInt(attributeKeys.length)} keys`,
      detail: attributeKeys.length ? attributeKeys.slice(0, 5).join(', ') : 'Import attributes for personalization and segmentation.',
      tone: attributeKeys.length >= 3 ? 'good' : 'warn',
    },
    {
      label: 'Client entities',
      value: 'Gap',
      detail: 'Client-owned objects such as accounts, stores, orders, memberships, and contracts need canonical storage.',
      tone: 'warn',
    },
    {
      label: 'Relationships',
      value: 'Gap',
      detail: 'Contact-to-entity links still need relationship APIs before multi-entity audiences and joins are first-class.',
      tone: 'warn',
    },
  ];
  const contactFoundationItems = [
    {
      label: 'Identity resolution',
      value: totalContacts ? 'Email key' : 'Gap',
      detail: totalContacts
        ? 'Contacts currently resolve around email; cross-source identity rules still need hardening.'
        : 'Import contacts before identity matching and duplicate resolution can run.',
      tone: 'warn',
    },
    {
      label: 'Consent state',
      value: unsubscribedCount ? 'Mixed' : 'Clear',
      detail: unsubscribedCount
        ? 'Visible opt-outs need durable consent history and suppression sync.'
        : 'No visible opt-outs; consent provenance still needs audit history.',
      tone: unsubscribedCount ? 'warn' : 'good',
    },
    {
      label: 'Enrichment freshness',
      value: attributeKeys.length ? `${formatInt(attributeKeys.length)} keys` : 'Gap',
      detail: attributeKeys.length
        ? 'Profile attributes are available, but freshness timestamps and source precedence need foundation work.'
        : 'Attribute enrichment is required before personalization and segmentation scale.',
      tone: 'warn',
    },
    {
      label: 'Activation paths',
      value: totalContacts ? 'Ready' : 'Gap',
      detail: totalContacts
        ? 'Contacts can feed audiences, templates, campaigns, and journey enrollment testing.'
        : 'Contacts must exist before activation into audiences, campaigns, or journeys.',
      tone: totalContacts ? 'good' : 'warn',
    },
  ];
  const contactRelationshipContractItems = [
    {
      label: 'Entity registry',
      value: 'Gap',
      detail: 'Client-owned entities need canonical definitions for accounts, stores, orders, memberships, contracts, and custom objects.',
      tone: 'warn',
    },
    {
      label: 'Relationship API',
      value: 'Gap',
      detail: 'Contacts need typed links to client entities with cardinality, source system, confidence, and effective dates.',
      tone: 'warn',
    },
    {
      label: 'Join readiness',
      value: attributeKeys.length ? 'Partial' : 'Gap',
      detail: attributeKeys.length ? 'Contact attributes exist, but entity joins still need stable keys and relationship materialization.' : 'Import source keys before planning contact-to-entity joins.',
      tone: 'warn',
    },
    {
      label: 'Consent inheritance',
      value: unsubscribedCount ? 'Mixed' : 'Gap',
      detail: 'Consent and suppression state must define whether opt-outs inherit across related entities and brands.',
      tone: 'warn',
    },
    {
      label: 'Segment activation',
      value: totalContacts ? 'Contact-only' : 'Gap',
      detail: 'Audience rules need first-class filters for related entity attributes before multi-entity segmentation is production-ready.',
      tone: 'warn',
    },
    {
      label: 'Entity audit',
      value: 'Gap',
      detail: 'Relationship changes need source lineage, replay, conflict resolution, and operator-visible audit history.',
      tone: 'warn',
    },
  ];

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

  function applyAttributeKey(key: string) {
    const current = parseAttributes();
    setAttributesJson(JSON.stringify({ ...current, [key]: current[key] ?? `sample ${key}` }, null, 2));
    setStatus(`Added attribute key ${key} to the contact editor.`);
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

  async function deleteContactRow(contact: ContactRead) {
    if (!window.confirm(`Delete contact "${contact.email}"?`)) return;
    await runContactOperation('Deleting contact', async () => {
      await fetchJson<{ id: string }>(`/api/v1/audiences/contacts/${contact.id}`, { method: 'DELETE' });
      if (selectedContactId === contact.id) await newContact();
      await onRefresh();
      return `Deleted contact: ${contact.email}.`;
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
          <MetricCard metric={{ label: 'Contacts', value: formatInt(totalContacts), change: `${formatInt(metadata?.scanned_count || contacts.length)} scanned` }} />
          <MetricCard metric={{ label: 'Visible', value: formatInt(contacts.length), change: 'loaded rows' }} />
          <MetricCard metric={{ label: 'Attributed', value: formatInt(attributedCount), change: `${formatInt(attributeKeys.length)} keys` }} />
          <MetricCard metric={{ label: 'Sources', value: formatInt(uniqueSources || sourceRows.length), change: 'source values' }} />
          <MetricCard metric={{ label: 'Unsubscribed', value: formatInt(unsubscribedCount), change: 'visible contacts', tone: unsubscribedCount ? 'warn' : 'good' }} />
        </section>
        <section className={`contacts-triage-panel full-span ${contactsTriageAction.tone}`}>
          <div className="contacts-triage-head">
            <div>
              <span>Contacts triage</span>
              <strong>{contactsTriageAction.title}</strong>
              <small>{contactsTriageAction.detail}</small>
            </div>
            <button className={contactsTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={contactsTriageAction.run} disabled={contactsTriageAction.disabled}>{contactsTriageAction.actionLabel}</button>
          </div>
          <div className="contacts-triage-grid">
            {contactsTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="contact-entity-model-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Canonical Entity Model</h3>
              <span className="muted">Contacts, attributes, client-owned entities, and relationship readiness.</span>
            </div>
            <a href="#data">Open Data Sources</a>
          </div>
          <div className="contact-entity-model-grid">
            {contactEntityItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="contact-foundation-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Contact Foundations</h3>
              <span className="muted">Identity resolution, consent state, enrichment freshness, and activation readiness.</span>
            </div>
            <a href="#audience">Open Audiences</a>
          </div>
          <div className="contact-foundation-grid">
            {contactFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="contact-relationship-contract-panel full-span">
          <div className="panel-head compact-head">
            <div>
              <h3>Contact Relationship Contract</h3>
              <span className="muted">Entity registry, relationship API, join readiness, consent inheritance, activation, and audit requirements.</span>
            </div>
            <a href="#data">Open Data Sources</a>
          </div>
          <div className="contact-relationship-contract-grid">
            {contactRelationshipContractItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>
        <section className="contacts-command-strip full-span" aria-label="Contacts readiness summary">
          <article className={totalContacts ? 'good' : 'warn'}>
            <span>Contact base</span>
            <strong>{formatInt(totalContacts)}</strong>
            <small>{formatInt(contacts.length)} visible rows</small>
          </article>
          <article className={attributeKeys.length >= 3 ? 'good' : 'warn'}>
            <span>Personalization</span>
            <strong>{formatInt(attributeKeys.length)} keys</strong>
            <small>{formatPct(metadataCoverage)} attributed in view</small>
          </article>
          <article className={(uniqueSources || sourceRows.length) ? 'good' : 'warn'}>
            <span>Sources</span>
            <strong>{formatInt(uniqueSources || sourceRows.length)}</strong>
            <small>{sourceRows[0]?.source || 'no source metadata'}</small>
          </article>
          <article className={unsubscribedRate > 0.2 ? 'warn' : 'good'}>
            <span>Compliance</span>
            <strong>{formatPct(unsubscribedRate)}</strong>
            <small>{formatInt(unsubscribedCount)} unsubscribed visible</small>
          </article>
          <article className="wide">
            <span>Recommended next action</span>
            <strong>{contactsNextAction}</strong>
            <small>{selectedContact?.email || 'No contact selected'}</small>
          </article>
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
	                    onDoubleClick={() => { window.location.hash = `#contacts/${contact.id}`; }}
	                  >
                    <td>{contact.email}</td>
                    <td>{[contact.first_name, contact.last_name].filter(Boolean).join(' ') || '-'}</td>
                    <td>{contact.source || '-'}</td>
                    <td><span className="pill">{contact.is_unsubscribed ? 'unsubscribed' : 'subscribed'}</span></td>
                    <td>{Object.keys(contact.attributes || {}).slice(0, 6).join(', ') || '-'}</td>
                    <td><RowActionMenu openHref={`#contacts/${contact.id}`} onDelete={() => deleteContactRow(contact)} /></td>
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
        <section className="panel full-span contact-attribute-helper-panel">
          <div className="panel-head">
            <div>
              <h2>Attribute Helper</h2>
              <span className="muted">{formatInt(attributeKeys.length)} known keys, {formatInt(activeAttributeKeys.length)} active in editor, {formatInt(missingAttributeKeys.length)} missing.</span>
            </div>
            <a href="#templates">Open templates</a>
          </div>
          <div className="contact-attribute-helper-grid">
            <article>
              <span>Active attributes</span>
              <strong>{activeAttributeKeys.slice(0, 10).join(', ') || 'None'}</strong>
            </article>
            <article>
              <span>Missing known keys</span>
              <strong>{missingAttributeKeys.slice(0, 10).join(', ') || 'None'}</strong>
            </article>
            <article>
              <span>Template readiness</span>
              <strong>{activeAttributeKeys.length ? 'Variables available' : 'Add attributes'}</strong>
            </article>
          </div>
          <div className="button-row">
            {attributeKeys.slice(0, 24).map((key) => <button className="ghost" key={key} onClick={() => applyAttributeKey(key)}>{key}</button>)}
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
        <div className="campaign-action-bar">
          <div>
            <strong>Contact</strong>
            <button className="primary" onClick={saveContact} disabled={busy}>{isCreatingContact ? 'Create Contact' : 'Save Changes'}</button>
            {isPersistedContact ? <a className="ghost" href="#contacts/new">New Contact</a> : null}
          </div>
          {isPersistedContact ? (
            <div>
              <strong>Compliance</strong>
              <button className="ghost" onClick={loadUnsubscribeToken} disabled={busy}>Unsubscribe Token</button>
              <button className="ghost" onClick={deleteContact} disabled={busy}>Delete Contact</button>
            </div>
          ) : null}
          <div>
            <strong>Data</strong>
            <button className="ghost" onClick={onRefresh} disabled={busy}>Refresh</button>
          </div>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className={`contacts-triage-panel ${contactsTriageAction.tone}`}>
          <div className="contacts-triage-head">
            <div>
              <span>Contacts triage</span>
              <strong>{contactsTriageAction.title}</strong>
              <small>{contactsTriageAction.detail}</small>
            </div>
            <button className={contactsTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={contactsTriageAction.run} disabled={contactsTriageAction.disabled}>{contactsTriageAction.actionLabel}</button>
          </div>
          <div className="contacts-triage-grid">
            {contactsTriageItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="contact-entity-model-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Canonical Entity Model</h3>
              <span className="muted">Contacts, attributes, client-owned entities, and relationship readiness.</span>
            </div>
            <a href="#data">Open Data Sources</a>
          </div>
          <div className="contact-entity-model-grid">
            {contactEntityItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="contact-foundation-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Contact Foundations</h3>
              <span className="muted">Identity resolution, consent state, enrichment freshness, and activation readiness.</span>
            </div>
            <a href="#audience">Open Audiences</a>
          </div>
          <div className="contact-foundation-grid">
            {contactFoundationItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="contact-relationship-contract-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Contact Relationship Contract</h3>
              <span className="muted">Entity registry, relationship API, join readiness, consent inheritance, activation, and audit requirements.</span>
            </div>
            <a href="#data">Open Data Sources</a>
          </div>
          <div className="contact-relationship-contract-grid">
            {contactRelationshipContractItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="form-grid">
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
          {isPersistedContact ? (
            <label>
              Unsubscribed
              <select value={isUnsubscribed ? 'true' : 'false'} onChange={(event) => setIsUnsubscribed(event.target.value === 'true')}>
                <option value="false">No</option>
                <option value="true">Yes</option>
              </select>
            </label>
          ) : null}
          <label className="wide-field">
            Attributes JSON
            <textarea value={attributesJson} onChange={(event) => setAttributesJson(event.target.value)} rows={8} />
          </label>
          {isPersistedContact ? (
            <label>
              Unsubscribe token
              <textarea value={unsubscribeToken || 'Not generated'} readOnly rows={8} />
            </label>
          ) : null}
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
  const totalFailures = campaigns.reduce((sum, item) => sum + Number(item.failed_count || 0), 0);
  const totalOpens = campaigns.reduce((sum, item) => sum + Number(item.opened_count || 0), 0);
  const totalClicks = campaigns.reduce((sum, item) => sum + Number(item.clicked_count || 0), 0);
  const totalAudienceReach = audiences.reduce((sum, item) => sum + Number(item.estimated_count || 0), 0);
  const activeEnrollments = journeys.reduce((sum, item) => sum + Number(item.active_count || 0), 0);
  const journeyFailureCount = journeys.reduce((sum, item) => sum + Number(item.failed_count || 0) + Number(item.step_failed_count || 0), 0);
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
  const aggregateOpenRate = totalOpens / Math.max(totalSent, 1);
  const aggregateClickRate = totalClicks / Math.max(totalSent, 1);
  const aggregateFailureRate = totalFailures / Math.max(totalSent + totalFailures, 1);
  const analyticsAiBriefSummary = {
    sections: [
      campaigns.length ? `${formatInt(campaigns.length)} campaign(s)` : '',
      audiences.length ? `${formatInt(audiences.length)} audience(s)` : '',
      journeys.length ? `${formatInt(journeys.length)} journey report(s)` : '',
      timeline.length ? `${formatInt(timeline.length)} timeline point(s)` : '',
      domains.length ? `${formatInt(domains.length)} domain row(s)` : '',
    ].filter(Boolean),
    risk: totalFailures || journeyFailureCount || (campaignDetail?.bounced_count || 0)
      ? 'Delivery and journey risk included'
      : 'No major risk signals loaded',
  };
  const reportFocusSummary = !selectedCampaignId
    ? {
      tone: 'warn',
      title: 'Select a campaign',
      detail: 'Choose a campaign to load timeline, delivery, and domain drilldowns.',
      status: 'No campaign',
      domainStatus: 'No domains',
    }
    : !campaignDetail
      ? {
        tone: 'warn',
        title: 'Detail report not loaded',
        detail: 'Load the selected campaign report to inspect trend and deliverability signals.',
        status: 'Summary only',
        domainStatus: 'Domains pending',
      }
      : {
        tone: campaignDetail.failed_count || campaignDetail.bounced_count ? 'warn' : 'good',
        title: campaignDetail.failed_count || campaignDetail.bounced_count ? 'Review delivery issues' : 'Detail report loaded',
        detail: `${formatInt(campaignDetail.sent_count)} sent, ${formatInt(campaignDetail.failed_count)} failed, ${formatInt(campaignDetail.bounced_count)} bounced.`,
        status: `${formatInt(timeline.length)} timeline point(s)`,
        domainStatus: `${formatInt(domains.length)} domain row(s)`,
      };
  const reportsNextAction = totalFailures > 0
    ? 'Review failed delivery records and requeue or suppress bad contacts.'
    : !campaignDetail && selectedCampaignId
      ? 'Load the selected campaign report to inspect timeline and domain delivery.'
      : aggregateClickRate < 0.02 && totalSent > 0
        ? 'Compare top campaigns and improve offer clarity or call-to-action placement.'
        : journeyFailureCount > 0
        ? 'Review journey failures before the next campaign launch.'
          : 'Performance is stable. Continue monitoring campaign and audience comparisons.';
  const analyticsNextStep = !selectedCampaignId
    ? {
      tone: 'warn',
      title: 'Select report campaign',
      detail: 'Choose a campaign before loading timeline and domain analytics.',
      actionLabel: 'Select Campaign',
      run: () => setStatus('Select a campaign in Reporting Controls before loading detail.'),
    }
    : !campaignDetail
      ? {
        tone: 'warn',
        title: 'Load campaign detail',
        detail: 'Fetch timeline and domain deliverability for the selected campaign.',
        actionLabel: 'Load Report',
        run: loadReport,
      }
      : aggregateFailureRate > 0.05 || totalFailures > 0
        ? {
          tone: 'warn',
          title: 'Review delivery risk',
          detail: `${formatInt(totalFailures)} failed send(s) are visible across campaign analytics.`,
          actionLabel: 'Open Delivery',
          run: () => { window.location.hash = '#delivery'; },
        }
        : aggregateClickRate < 0.02 && totalSent > 0
          ? {
            tone: 'warn',
            title: 'Compare engagement',
            detail: 'Click rate is low. Compare campaigns and improve CTA clarity before the next send.',
            actionLabel: 'Open Campaigns',
            run: () => { window.location.hash = '#campaigns'; },
          }
          : journeyFailureCount > 0
            ? {
              tone: 'warn',
              title: 'Review journey risk',
              detail: `${formatInt(journeyFailureCount)} journey failure signal(s) need attention.`,
              actionLabel: 'Open Journeys',
              run: () => { window.location.hash = '#automations'; },
            }
            : {
              tone: 'good',
              title: 'Send brief to AI',
              detail: 'Performance is stable. Use AI Studio for the next optimization plan.',
              actionLabel: 'AI Brief',
              run: openAiActionBrief,
            };
  const analyticsAiActions = [
    {
      label: 'Delivery risk',
      value: totalFailures || (campaignDetail?.bounced_count || 0)
        ? `${formatInt(totalFailures + Number(campaignDetail?.bounced_count || 0))} issue(s)`
        : 'Stable',
      detail: totalFailures || (campaignDetail?.bounced_count || 0)
        ? 'Review failed, bounced, and retry records before the next send.'
        : 'No loaded delivery failures require immediate review.',
      tone: totalFailures || (campaignDetail?.bounced_count || 0) ? 'warn' : 'good',
      actionLabel: 'Open Delivery',
      run: () => { window.location.hash = '#delivery'; },
    },
    {
      label: 'Engagement',
      value: `${formatPct(aggregateOpenRate)} open / ${formatPct(aggregateClickRate)} click`,
      detail: aggregateClickRate < 0.02 && totalSent > 0
        ? 'Ask AI for CTA, offer, and content changes for the next campaign.'
        : 'Engagement is ready for AI optimization planning.',
      tone: aggregateClickRate < 0.02 && totalSent > 0 ? 'warn' : 'good',
      actionLabel: 'Open Campaigns',
      run: () => { window.location.hash = '#campaigns'; },
    },
    {
      label: 'Audience fit',
      value: `${formatInt(totalAudienceReach)} reachable`,
      detail: totalAudienceReach
        ? 'Use audience comparisons to refine targeting and exclusions.'
        : 'Load or build audiences before requesting targeting recommendations.',
      tone: totalAudienceReach ? 'good' : 'warn',
      actionLabel: 'Open Audiences',
      run: () => { window.location.hash = '#audiences'; },
    },
    {
      label: 'Journey follow-up',
      value: `${formatInt(journeyFailureCount)} risk signal(s)`,
      detail: journeyFailureCount
        ? 'Fix failed steps and queued sends before adding more enrollment volume.'
        : 'Journey reports do not show loaded failure pressure.',
      tone: journeyFailureCount ? 'warn' : 'good',
      actionLabel: 'Open Journeys',
      run: () => { window.location.hash = '#automations'; },
    },
  ];
  const analyticsAiPrimaryAction = analyticsAiActions.find((action) => action.tone === 'warn') || analyticsAiActions[0];
  const analyticsFoundationSignals = [
    {
      label: 'Data graph',
      value: totalAudienceReach ? 'Audience-ready' : 'Gap',
      detail: totalAudienceReach ? `${formatInt(totalAudienceReach)} reachable contact(s) across ${formatInt(audiences.length)} audience(s)` : 'Load contacts, audiences, and client entities before attribution analysis.',
      tone: totalAudienceReach ? 'good' : 'warn',
    },
    {
      label: 'Send engine',
      value: totalSent ? 'Measured' : 'Pending',
      detail: totalSent ? `${formatInt(totalSent)} sent with ${formatPct(aggregateFailureRate)} failure rate` : 'Launch and process sends before queue health can be measured.',
      tone: totalSent && aggregateFailureRate <= 0.05 ? 'good' : 'warn',
    },
    {
      label: 'Feedback loop',
      value: domains.length ? 'Domain signals' : 'Gap',
      detail: domains.length ? `${formatInt(domains.length)} domain deliverability row(s) loaded` : 'Load domain analytics and wire bounce/complaint feedback for durable deliverability signals.',
      tone: domains.length ? 'good' : 'warn',
    },
    {
      label: 'Agent follow-up',
      value: analyticsAiBriefSummary.sections.length ? 'Briefable' : 'Summary only',
      detail: 'Send analytics context to AI Studio for next-best-action planning and persistent operator handoff.',
      tone: analyticsAiBriefSummary.sections.length ? 'good' : 'warn',
    },
  ];
  const analyticsDeliverabilityContractItems = [
    {
      label: 'Domain signal contract',
      value: domains.length ? `${formatInt(domains.length)} domains` : 'Gap',
      detail: 'Domain reports need provider, DNS identity, bounce rate, complaint rate, and reputation state for each sending domain.',
      tone: domains.length ? 'good' : 'warn',
    },
    {
      label: 'Bounce signal contract',
      value: campaignDetail?.bounced_count ? `${formatInt(campaignDetail.bounced_count)} bounced` : 'Gap',
      detail: 'Bounce metrics should connect analytics rows to compliance suppressions and delivery retry decisions.',
      tone: campaignDetail?.bounced_count ? 'warn' : 'warn',
    },
    {
      label: 'Failure signal contract',
      value: totalFailures ? `${formatInt(totalFailures)} failed` : 'Stable',
      detail: 'Failed sends need error family, provider response, retry state, and operator disposition in reports.',
      tone: totalFailures ? 'warn' : 'good',
    },
    {
      label: 'Engagement signal contract',
      value: `${formatPct(aggregateOpenRate)} / ${formatPct(aggregateClickRate)}`,
      detail: 'Open and click signals need bot filtering, identity resolution, attribution window, and audience segment context.',
      tone: totalSent ? 'good' : 'warn',
    },
    {
      label: 'Feedback routing',
      value: domains.length || totalFailures ? 'Partial' : 'Gap',
      detail: 'Deliverability signals should route to Delivery, Compliance, Campaigns, and AI Studio without manual copying.',
      tone: domains.length || totalFailures ? 'warn' : 'warn',
    },
    {
      label: 'AI evidence pack',
      value: analyticsAiBriefSummary.sections.length ? 'Briefable' : 'Gap',
      detail: 'AI recommendations need the exact report rows, domain signals, suppression context, and operator action history.',
      tone: analyticsAiBriefSummary.sections.length ? 'good' : 'warn',
    },
  ];

  function openAiActionBrief() {
    const topCampaignLines = topCampaigns.map((campaign) => (
      `- ${campaign.name}: ${formatPct(campaign.open_rate)} open, ${formatPct(campaign.click_rate)} click, ${formatInt(campaign.failed_count)} failed.`
    ));
    const topAudienceLines = topAudiences.map((audience) => (
      `- ${audience.name}: ${formatInt(audience.estimated_count)} reach, ${formatPct(audience.open_rate)} open, ${formatPct(audience.click_rate)} click.`
    ));
    const journeyRiskLines = journeyRisks.map((journey) => (
      `- ${journey.name}: ${formatInt(Number(journey.failed_count || 0) + Number(journey.step_failed_count || 0))} failure signal(s), ${formatInt(journey.queued_send_count)} queued send(s).`
    ));
    const domainLines = domains.map((domain) => (
      `- ${domain.domain}: ${providerLabel(domain.provider)}, ${formatPct(domain.open_rate)} open, ${formatPct(domain.click_rate)} click, ${formatPct(domain.bounce_rate)} bounce.`
    ));
    const timelineLines = timeline.slice(-5).map((point) => (
      `- ${point.date}: ${formatInt(point.sent_count)} sent, ${formatPct(point.open_rate)} open, ${formatPct(point.click_rate)} click.`
    ));
    const briefLines = [
      `Recommended action: ${reportsNextAction}`,
      `Primary AI action: ${analyticsAiPrimaryAction.label} - ${analyticsAiPrimaryAction.detail}`,
      `Delivery health: ${formatPct(1 - aggregateFailureRate)} (${formatInt(totalFailures)} failed / ${formatInt(totalSent)} sent).`,
      `Engagement: ${formatPct(aggregateOpenRate)} open rate and ${formatPct(aggregateClickRate)} click rate.`,
      `Audience reach: ${formatInt(totalAudienceReach)} contacts across ${formatInt(audiences.length)} saved audiences.`,
      `Journey risk: ${formatInt(journeyFailureCount)} failures and ${formatInt(activeEnrollments)} active enrollments.`,
      selectedCampaign ? `Selected campaign: ${selectedCampaign.name} (${selectedCampaign.status}).` : 'No campaign selected.',
      '',
      'Top campaigns:',
      ...(topCampaignLines.length ? topCampaignLines : ['- No campaign performance rows loaded.']),
      '',
      'Audience comparison:',
      ...(topAudienceLines.length ? topAudienceLines : ['- No audience performance rows loaded.']),
      '',
      'Journey risk detail:',
      ...(journeyRiskLines.length ? journeyRiskLines : ['- No journey risk rows loaded.']),
      '',
      'Domain deliverability:',
      ...(domainLines.length ? domainLines : ['- Load a campaign report to include domain rows.']),
      '',
      'Recent campaign timeline:',
      ...(timelineLines.length ? timelineLines : ['- Load a campaign report to include timeline rows.']),
      '',
      'Operator action checklist:',
      ...analyticsAiActions.map((action) => `- ${action.label}: ${action.value}. ${action.detail}`),
    ];
    window.localStorage.setItem(AI_ACTION_BRIEF_STORAGE_KEY, briefLines.join('\n'));
    onOperation({ label: 'AI workflow', message: `Prepared analytics brief with ${formatInt(analyticsAiBriefSummary.sections.length)} section(s).`, tone: 'success' });
    window.location.hash = '#ai-studio/analytics-brief';
  }

  function csvCell(value: unknown) {
    const text = String(value ?? '');
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function exportAnalyticsCsv() {
    const sections = [
      {
        title: 'Campaign Performance',
        headers: ['Campaign', 'Status', 'Requested', 'Sent', 'Failed', 'Open Rate', 'Click Rate'],
        rows: campaigns.map((campaign) => [
          campaign.name,
          campaign.status,
          campaign.requested_count,
          campaign.sent_count,
          campaign.failed_count,
          formatPct(campaign.open_rate),
          formatPct(campaign.click_rate),
        ]),
      },
      {
        title: 'Audience Comparison',
        headers: ['Audience', 'Status', 'Reach', 'Sent', 'Open Rate', 'Click Rate'],
        rows: audiences.map((audience) => [
          audience.name,
          audience.status,
          audience.estimated_count,
          audience.sent_count,
          formatPct(audience.open_rate),
          formatPct(audience.click_rate),
        ]),
      },
      {
        title: 'Journey Risk',
        headers: ['Journey', 'Active', 'Failed', 'Step Failed', 'Queued Sends'],
        rows: journeys.map((journey) => [
          journey.name,
          journey.active_count,
          journey.failed_count,
          journey.step_failed_count,
          journey.queued_send_count,
        ]),
      },
      {
        title: 'Campaign Timeline',
        headers: ['Date', 'Sent', 'Opened', 'Clicked', 'Failed', 'Open Rate', 'Click Rate'],
        rows: timeline.map((point) => [
          point.date,
          point.sent_count,
          point.opened_count,
          point.clicked_count,
          point.failed_count,
          formatPct(point.open_rate),
          formatPct(point.click_rate),
        ]),
      },
      {
        title: 'Domain Deliverability',
        headers: ['Domain', 'Provider', 'Records', 'Sent', 'Failed', 'Open Rate', 'Click Rate', 'Bounce Rate'],
        rows: domains.map((domain) => [
          domain.domain,
          providerLabel(domain.provider),
          domain.send_record_count,
          domain.sent_count,
          domain.failed_count,
          formatPct(domain.open_rate),
          formatPct(domain.click_rate),
          formatPct(domain.bounce_rate),
        ]),
      },
    ];
    const csv = sections
      .filter((section) => section.rows.length)
      .flatMap((section) => [
        [section.title],
        section.headers,
        ...section.rows,
        [],
      ])
      .map((row) => row.map(csvCell).join(','))
      .join('\n');
    if (!csv.trim()) {
      setStatus('No analytics rows are available to export yet.');
      return;
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `email-engine-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus('Downloaded analytics CSV export.');
  }

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
      <section className="analytics-command-strip full-span" aria-label="Reports command summary">
        <article className={aggregateFailureRate > 0.05 ? 'warn' : 'good'}>
          <span>Delivery health</span>
          <strong>{formatPct(1 - aggregateFailureRate)}</strong>
          <small>{formatInt(totalFailures)} failed / {formatInt(totalSent)} sent</small>
        </article>
        <article className={aggregateOpenRate > 0 ? 'good' : 'warn'}>
          <span>Engagement</span>
          <strong>{formatPct(aggregateOpenRate)} open</strong>
          <small>{formatPct(aggregateClickRate)} click rate</small>
        </article>
        <article className={totalAudienceReach ? 'good' : 'warn'}>
          <span>Audience reach</span>
          <strong>{formatInt(totalAudienceReach)}</strong>
          <small>{formatInt(audiences.length)} saved audiences</small>
        </article>
        <article className={journeyFailureCount ? 'warn' : 'good'}>
          <span>Journey risk</span>
          <strong>{formatInt(journeyFailureCount)} failures</strong>
          <small>{formatInt(activeEnrollments)} active enrollments</small>
        </article>
        <article className="wide">
          <span>Recommended next action</span>
          <strong>{reportsNextAction}</strong>
          <small>{selectedCampaign?.name || 'Select a campaign for detail reporting'}</small>
          <button className="ghost compact-button" onClick={openAiActionBrief}>Send to AI Studio</button>
        </article>
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
          <button className="ghost" onClick={exportAnalyticsCsv} disabled={busy}>Export CSV</button>
        </div>
        <div className={`operation-banner ${status.startsWith('Error:') ? 'warn' : ''}`}>
          <strong>{busy ? 'Working' : 'Status'}</strong>
          <span>{status}</span>
        </div>
        <div className={`analytics-focus-summary ${reportFocusSummary.tone}`}>
          <div>
            <span>Report focus</span>
            <strong>{reportFocusSummary.title}</strong>
            <small>{reportFocusSummary.detail}</small>
          </div>
          <div>
            <span>Timeline window</span>
            <strong>{formatInt(days)} days</strong>
            <small>{reportFocusSummary.status}</small>
          </div>
          <div>
            <span>Deliverability</span>
            <strong>{reportFocusSummary.domainStatus}</strong>
            <small>{selectedCampaign?.name || 'No campaign selected'}</small>
          </div>
          <button className={reportFocusSummary.tone === 'good' ? 'ghost' : 'primary'} type="button" onClick={loadReport} disabled={busy || !selectedCampaignId}>Load Report</button>
        </div>
        <div className={`analytics-next-step ${analyticsNextStep.tone}`}>
          <div>
            <span>Guided analytics next step</span>
            <strong>{analyticsNextStep.title}</strong>
            <small>{analyticsNextStep.detail}</small>
          </div>
          <button className={analyticsNextStep.tone === 'good' ? 'ghost' : 'primary'} type="button" onClick={analyticsNextStep.run} disabled={busy}>{analyticsNextStep.actionLabel}</button>
        </div>
        <div className="analytics-ai-brief">
          <div>
            <span>AI analytics brief</span>
            <strong>{analyticsAiBriefSummary.sections.length ? analyticsAiBriefSummary.sections.join(' · ') : 'Summary only'}</strong>
            <small>{analyticsAiBriefSummary.risk}</small>
          </div>
          <button className="ghost" type="button" onClick={openAiActionBrief} disabled={busy}>Send to AI Studio</button>
        </div>
        <div className="analytics-ai-action-panel">
          <div className="analytics-ai-action-head">
            <div>
              <span>AI action panel</span>
              <strong>{analyticsAiPrimaryAction.label}</strong>
              <small>{analyticsAiPrimaryAction.detail}</small>
            </div>
            <button className={analyticsAiPrimaryAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={analyticsAiPrimaryAction.run} disabled={busy}>{analyticsAiPrimaryAction.actionLabel}</button>
          </div>
          <div className="analytics-ai-action-grid">
            {analyticsAiActions.map((action) => (
              <article className={action.tone} key={action.label}>
                <span>{action.label}</span>
                <strong>{action.value}</strong>
                <small>{action.detail}</small>
                <button className="ghost compact-button" type="button" onClick={action.run} disabled={busy}>{action.actionLabel}</button>
              </article>
            ))}
          </div>
        </div>
        <div className="analytics-foundation-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Foundation Signals</h3>
              <span className="muted">Data graph, send engine, feedback loop, and agent follow-up signals from reports.</span>
            </div>
            <button className="link-button" type="button" onClick={openAiActionBrief} disabled={busy}>Send to AI Studio</button>
          </div>
          <div className="analytics-foundation-grid">
            {analyticsFoundationSignals.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="analytics-deliverability-panel">
          <div className="panel-head compact-head">
            <div>
              <h3>Deliverability Signal Contract</h3>
              <span className="muted">Domain, bounce, failure, engagement, routing, and AI evidence requirements for durable feedback loops.</span>
            </div>
            <button className="link-button" type="button" onClick={openAiActionBrief} disabled={busy}>Send to AI Studio</button>
          </div>
          <div className="analytics-deliverability-grid">
            {analyticsDeliverabilityContractItems.map((item) => (
              <article className={item.tone} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
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
  const hasBrief = Boolean(brief.trim());
  const hasInstruction = Boolean(instruction.trim());
  const hasTemplateRecommendations = recommendations.length > 0;
  const hasWorkflowRecommendations = workflowRecommendations.length > 0;
  const hasPreview = Boolean(previewHtml);
  const workflowCoverageAreas = Array.from(new Set(workflowRecommendations.map((item) => item.area)));
  const aiStudioTriageAction = !openAiReady
    ? {
      tone: 'warn',
      title: 'Configure AI provider',
      detail: 'AI Studio is running in deterministic fallback mode; configure OpenAI for production-quality agent workflows.',
      actionLabel: 'Open Settings',
      run: () => { window.location.hash = '#settings'; },
      disabled: busy,
    }
    : !hasBrief
      ? {
        tone: 'warn',
        title: 'Write agent brief',
        detail: 'Start with a clear operator brief before drafting templates or reviewing workflows.',
        actionLabel: 'Focus Brief',
        run: () => setStatus('Add an AI brief that describes the desired operator outcome.'),
        disabled: busy,
      }
      : !hasWorkflowRecommendations
        ? {
          tone: 'warn',
          title: 'Run workflow review',
          detail: 'Use AI Studio as the cross-workflow agent layer across analytics, campaigns, audiences, delivery, and journeys.',
          actionLabel: 'Review Workflow',
          run: reviewWorkflow,
          disabled: busy,
        }
        : !hasTemplateRecommendations
          ? {
            tone: 'warn',
            title: 'Load template recommendations',
            detail: 'Ask AI to inspect the current template content for deliverability, layout, and copy improvements.',
            actionLabel: 'Recommendations',
            run: recommendTemplate,
            disabled: busy,
          }
          : !hasPreview
            ? {
              tone: 'warn',
              title: 'Render AI preview',
              detail: 'Preview the AI-assisted template with sample variables before saving it.',
              actionLabel: 'Preview',
              run: previewTemplate,
              disabled: busy,
            }
            : {
              tone: 'good',
              title: 'AI Studio ready',
              detail: 'Provider, workflow review, template recommendations, and preview are ready for operator handoff.',
              actionLabel: 'Save as Template',
              run: saveAsTemplate,
              disabled: busy,
            };
  const aiStudioTriageItems = [
    {
      label: 'Provider',
      value: openAiReady ? 'OpenAI' : 'Fallback',
      detail: openAiReady ? `${provider} ${model}` : 'Deterministic fallback active',
      tone: openAiReady ? 'good' : 'warn',
    },
    {
      label: 'Agent brief',
      value: hasBrief ? 'Ready' : 'Missing',
      detail: hasInstruction ? 'Brief and edit instruction available' : 'Brief available; edit instruction is empty',
      tone: hasBrief && hasInstruction ? 'good' : 'warn',
    },
    {
      label: 'Workflow review',
      value: hasWorkflowRecommendations ? formatInt(workflowRecommendations.length) : 'Not run',
      detail: hasWorkflowRecommendations ? 'Cross-workflow recommendations loaded' : 'No agent review loaded yet',
      tone: hasWorkflowRecommendations ? 'good' : 'warn',
    },
    {
      label: 'Template review',
      value: hasTemplateRecommendations ? formatInt(recommendations.length) : 'Not run',
      detail: hasTemplateRecommendations ? 'Template recommendations loaded' : 'No template recommendations loaded',
      tone: hasTemplateRecommendations ? 'good' : 'warn',
    },
    {
      label: 'Preview',
      value: hasPreview ? 'Rendered' : 'Pending',
      detail: hasPreview ? 'AI-assisted template preview is available' : 'Render before saving a generated template',
      tone: hasPreview ? 'good' : 'warn',
    },
  ];
  const aiAgentLayerItems = [
    {
      label: 'Orchestration',
      value: hasWorkflowRecommendations ? 'Active' : 'Manual',
      detail: hasWorkflowRecommendations ? `${formatInt(workflowCoverageAreas.length)} workflow area(s) reviewed` : 'Operator still triggers workflow reviews manually',
      tone: hasWorkflowRecommendations ? 'good' : 'warn',
    },
    {
      label: 'Context memory',
      value: 'Gap',
      detail: 'Persistent agent memory, decisions, and follow-up state need canonical storage.',
      tone: 'warn',
    },
    {
      label: 'Human handoff',
      value: hasWorkflowRecommendations ? 'Ready' : 'Pending',
      detail: hasWorkflowRecommendations ? 'Recommendations can be reviewed before operator action' : 'Run workflow review before handoff',
      tone: hasWorkflowRecommendations ? 'good' : 'warn',
    },
    {
      label: 'Workflow coverage',
      value: workflowCoverageAreas.length ? workflowCoverageAreas.join(', ') : 'Not run',
      detail: 'Agents should remain present across templates, campaigns, audiences, delivery, analytics, and journeys.',
      tone: workflowCoverageAreas.length >= 5 ? 'good' : 'warn',
    },
  ];
  const aiAgentFoundationItems = [
    {
      label: 'Model routing',
      value: openAiReady ? 'Configured' : 'Fallback',
      detail: openAiReady ? `${provider} ${model} is available for agent workflows.` : 'Production agents need explicit model routing beyond deterministic fallback.',
      tone: openAiReady ? 'good' : 'warn',
    },
    {
      label: 'Tool permissions',
      value: 'Gap',
      detail: 'Agent tool calls need scoped permissions, approval rules, and workspace-level policy controls.',
      tone: 'warn',
    },
    {
      label: 'Run memory',
      value: 'Gap',
      detail: 'Long-running agents need durable task memory, decision state, and resumable follow-up queues.',
      tone: 'warn',
    },
    {
      label: 'Evaluation audit',
      value: hasWorkflowRecommendations ? 'Partial' : 'Gap',
      detail: hasWorkflowRecommendations
        ? 'Recommendations are visible, but agent runs still need scoring, audit trails, and regression review.'
        : 'Agent outputs need evaluation scores, audit trails, and regression review before automation.',
      tone: 'warn',
    },
  ];
  const aiWorkflowAgentContractItems = [
    {
      label: 'Memory contract',
      value: 'Gap',
      detail: 'Agents need durable workspace memory for decisions, rejected options, user preferences, and resumed tasks.',
      tone: 'warn',
    },
    {
      label: 'Tool contract',
      value: 'Gap',
      detail: 'Each agent tool needs scoped permissions, approval thresholds, execution logs, and rollback guidance.',
      tone: 'warn',
    },
    {
      label: 'Handoff contract',
      value: hasWorkflowRecommendations ? 'Partial' : 'Gap',
      detail: hasWorkflowRecommendations ? 'Recommendations are visible, but ownership and due-next state still need persistence.' : 'Agent handoffs need owner, status, next action, and target workspace stored durably.',
      tone: 'warn',
    },
    {
      label: 'Evidence contract',
      value: workflowSummary.length ? 'Partial' : 'Gap',
      detail: workflowSummary.length ? 'Workflow review produces summary evidence, but source rows and citations still need retention.' : 'Agent decisions need source context, report rows, prompts, model, and output snapshots.',
      tone: 'warn',
    },
    {
      label: 'Evaluation contract',
      value: hasWorkflowRecommendations ? 'Partial' : 'Gap',
      detail: 'Agent runs need scoring, regression checks, operator feedback, and safety review before automation.',
      tone: 'warn',
    },
    {
      label: 'Presence contract',
      value: workflowCoverageAreas.length ? formatInt(workflowCoverageAreas.length) : 'Gap',
      detail: 'Agents should remain available across templates, campaigns, audiences, delivery, compliance, analytics, journeys, and settings.',
      tone: workflowCoverageAreas.length >= 5 ? 'good' : 'warn',
    },
  ];

  useEffect(() => {
    const storedBrief = window.localStorage.getItem(AI_ACTION_BRIEF_STORAGE_KEY);
    if (!storedBrief) return;
    window.localStorage.removeItem(AI_ACTION_BRIEF_STORAGE_KEY);
    setBrief(`Use this ESP analytics brief to recommend the next operator action.\n\n${storedBrief}`);
    setInstruction('Turn the analytics brief into a concise action plan. Prioritize delivery/compliance risk first, then campaign content, audience targeting, and journey follow-up.');
    setStatus('Analytics brief loaded from Reports. Run Review Workflow or draft a focused improvement.');
    onOperation({ label: 'AI workflow', message: 'Analytics brief loaded in AI Studio.', tone: 'success' });
  }, [onOperation]);

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
      <section className={`ai-studio-triage-panel full-span ${aiStudioTriageAction.tone}`}>
        <div className="ai-studio-triage-head">
          <div>
            <span>AI Studio triage</span>
            <strong>{aiStudioTriageAction.title}</strong>
            <small>{aiStudioTriageAction.detail}</small>
          </div>
          <button className={aiStudioTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={aiStudioTriageAction.run} disabled={aiStudioTriageAction.disabled}>{aiStudioTriageAction.actionLabel}</button>
        </div>
        <div className="ai-studio-triage-grid">
          {aiStudioTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="ai-agent-layer-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Ever-Present Agent Layer</h3>
            <span className="muted">Cross-workflow orchestration, memory, handoff, and coverage.</span>
          </div>
          <button className="link-button" type="button" onClick={reviewWorkflow} disabled={busy}>Review Workflow</button>
        </div>
        <div className="ai-agent-layer-grid">
          {aiAgentLayerItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="ai-agent-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>AI Agent Foundations</h3>
            <span className="muted">Model routing, tool permissions, run memory, and evaluation audit readiness.</span>
          </div>
          <a href="#settings">Open Settings</a>
        </div>
        <div className="ai-agent-foundation-grid">
          {aiAgentFoundationItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="ai-agent-contract-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Workflow Agent Contract</h3>
            <span className="muted">Durable memory, tool permissions, handoff state, evidence, evaluation, and product-wide presence.</span>
          </div>
          <button className="link-button" type="button" onClick={reviewWorkflow} disabled={busy}>Review Workflow</button>
        </div>
        <div className="ai-agent-contract-grid">
          {aiWorkflowAgentContractItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
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
  const schemaReady = Boolean(diagnostics?.schema.ok && !diagnostics.schema.needs_migration);
  const providerReady = smtpReady || sgReady || emailProvider === 'console';
  const publicUrlReady = /^https?:\/\//.test(baseUrl);
  const aiReady = Boolean(diagnostics?.ai.openai_configured);
  const errorCount = diagnostics?.errors.length || 0;
  const dataConnectorTableReady = tables.includes('data_sources') && tables.includes('data_source_mappings');
  const webhookContractReady = publicUrlReady && tables.includes('suppression_entries');
  const readinessChecks = [
    schemaReady,
    providerReady,
    publicUrlReady,
    aiReady,
    tables.length > 0,
    errorCount === 0,
  ];
  const readyCount = readinessChecks.filter(Boolean).length;
  const integrationNextAction = !schemaReady
    ? 'Run or verify database migrations before launching new workflow changes.'
    : !providerReady
      ? 'Configure SendGrid or SMTP before relying on production campaign delivery.'
      : !publicUrlReady
        ? 'Set PUBLIC_BASE_URL so tracking, unsubscribe, and webhook links resolve correctly.'
        : errorCount > 0
          ? 'Review diagnostics errors before the next production test.'
          : !aiReady
            ? 'OpenAI is using fallback mode; configure it when AI output quality matters.'
            : 'Core integrations are ready. Continue testing data import, delivery, and reporting flows.';
  const integrationTriageAction = !providerReady
    ? {
      tone: 'warn',
      title: 'Configure outbound provider',
      detail: 'Owned SMTP should be first-class; use provider adapters only as delivery paths.',
      actionLabel: 'Open Settings',
      run: () => { window.location.hash = '#settings'; },
      disabled: busy,
    }
    : !smtpReady && sgReady
      ? {
        tone: 'warn',
        title: 'Plan owned SMTP',
        detail: 'SendGrid is ready, but owned SMTP is not configured as a managed platform path.',
        actionLabel: 'Open Settings',
        run: () => { window.location.hash = '#settings'; },
        disabled: busy,
      }
      : !publicUrlReady
        ? {
          tone: 'warn',
          title: 'Set public base URL',
          detail: 'Tracking, unsubscribe, and webhook links need a reachable PUBLIC_BASE_URL.',
          actionLabel: 'Refresh Diagnostics',
          run: refreshDiagnostics,
          disabled: busy,
        }
        : !schemaReady
          ? {
            tone: 'warn',
            title: 'Resolve schema state',
            detail: 'Database schema must be current before integration changes are production-safe.',
            actionLabel: 'Open Settings',
            run: () => { window.location.hash = '#settings'; },
            disabled: busy,
          }
          : errorCount > 0
            ? {
              tone: 'warn',
              title: 'Review diagnostics',
              detail: `${formatInt(errorCount)} diagnostic issue(s) need review before production tests.`,
              actionLabel: 'Refresh Diagnostics',
              run: refreshDiagnostics,
              disabled: busy,
            }
            : !aiReady
              ? {
                tone: 'warn',
                title: 'Configure AI provider',
                detail: 'OpenAI is in fallback mode; configure it for production-quality AI workflows.',
                actionLabel: 'Open Settings',
                run: () => { window.location.hash = '#settings'; },
                disabled: busy,
              }
              : {
                tone: 'good',
                title: 'Integrations ready',
                detail: 'Core provider, public URL, schema, diagnostics, and AI checks are ready.',
                actionLabel: 'Refresh Diagnostics',
                run: refreshDiagnostics,
                disabled: busy,
              };
  const integrationTriageItems = [
    {
      label: 'Owned SMTP',
      value: smtpReady ? 'Ready' : 'Missing',
      detail: smtpReady ? 'Managed SMTP path is configured' : 'Owned SMTP remains a platform foundation gap',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Provider adapters',
      value: sgReady || emailProvider === 'console' ? 'Available' : 'Pending',
      detail: sgReady ? 'SendGrid adapter configured' : emailProvider === 'console' ? 'Console adapter available for testing' : 'No adapter configured',
      tone: sgReady || emailProvider === 'console' ? 'good' : 'warn',
    },
    {
      label: 'Public endpoints',
      value: publicUrlReady ? 'Ready' : 'Missing',
      detail: baseUrl.replace(/^https?:\/\//, ''),
      tone: publicUrlReady ? 'good' : 'warn',
    },
    {
      label: 'AI provider',
      value: aiReady ? 'Ready' : 'Fallback',
      detail: diagnostics?.ai.model || 'Deterministic fallback available',
      tone: aiReady ? 'good' : 'warn',
    },
  ];
  const integrationFoundationItems = [
    {
      label: 'Data connectors',
      value: dataConnectorTableReady ? 'Modeled' : 'Gap',
      detail: dataConnectorTableReady ? 'Data sources and mappings are present in schema diagnostics.' : 'Connector registry and mapping tables need schema visibility.',
      tone: dataConnectorTableReady ? 'good' : 'warn',
    },
    {
      label: 'Owned SMTP foundation',
      value: smtpReady ? 'Configured' : 'Gap',
      detail: smtpReady ? 'Managed SMTP path is configured.' : 'Owned SMTP server, MTA policy, throttling, and domain controls remain platform work.',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Feedback webhooks',
      value: webhookContractReady ? 'Routable' : 'Gap',
      detail: webhookContractReady ? 'Public URL and suppression storage can support provider feedback.' : 'Webhook routing must connect bounce and complaint events to durable compliance records.',
      tone: webhookContractReady ? 'good' : 'warn',
    },
    {
      label: 'AI operations',
      value: aiReady ? 'Configured' : 'Fallback',
      detail: aiReady ? `${diagnostics?.ai.provider || 'AI'} ${diagnostics?.ai.model || ''}` : 'Production agent workflows need OpenAI configuration and observability.',
      tone: aiReady ? 'good' : 'warn',
    },
  ];
  const integrationConnectorRoadmapItems = [
    {
      family: 'RDBMS',
      status: dataConnectorTableReady ? 'Schema-ready' : 'Gap',
      detail: 'PostgreSQL, MySQL, and SQL Server connectors need credential vaulting, table discovery, and incremental sync cursors.',
    },
    {
      family: 'Warehouse',
      status: dataConnectorTableReady ? 'Modeled' : 'Gap',
      detail: 'BigQuery, Snowflake, and Redshift imports need batch scheduling, field typing, and cost-aware preview limits.',
    },
    {
      family: 'NoSQL',
      status: 'Gap',
      detail: 'MongoDB and document-store sources need collection sampling, nested field mapping, and stable entity extraction.',
    },
    {
      family: 'API and webhook',
      status: publicUrlReady ? 'Partial' : 'Gap',
      detail: 'REST, GraphQL, and inbound webhook connectors need managed secrets, retries, and event-to-entity mapping.',
    },
    {
      family: 'Owned SMTP',
      status: smtpReady ? 'Configured' : 'Gap',
      detail: 'Owned SMTP server operations need MTA policy, queue visibility, bounce routing, throttle controls, and domain health.',
    },
    {
      family: 'AI agent tools',
      status: aiReady ? 'Configured' : 'Fallback',
      detail: 'Ever-present agents need scoped connector tools, approvals, memory, and cross-workflow audit trails.',
    },
  ];

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
      <section className="integration-command-strip full-span" aria-label="Integration readiness summary">
        <article className={schemaReady ? 'good' : 'warn'}>
          <span>Schema</span>
          <strong>{schemaReady ? 'Ready' : 'Review'}</strong>
          <small>{diagnostics?.schema.current_revision || 'no revision'} / {diagnostics?.schema.expected_revision || 'expected unknown'}</small>
        </article>
        <article className={providerReady ? 'good' : 'warn'}>
          <span>Provider</span>
          <strong>{providerReady ? emailProvider : 'Pending'}</strong>
          <small>{smtpReady ? 'SMTP ready' : sgReady ? 'SendGrid ready' : 'No outbound provider'}</small>
        </article>
        <article className={publicUrlReady ? 'good' : 'warn'}>
          <span>Public URL</span>
          <strong>{publicUrlReady ? 'Configured' : 'Missing'}</strong>
          <small>{baseUrl.replace(/^https?:\/\//, '')}</small>
        </article>
        <article className={errorCount ? 'warn' : 'good'}>
          <span>Diagnostics</span>
          <strong>{formatInt(readyCount)} / {formatInt(readinessChecks.length)} ready</strong>
          <small>{formatInt(errorCount)} active errors</small>
        </article>
        <article className="wide">
          <span>Recommended next action</span>
          <strong>{integrationNextAction}</strong>
          <small>{aiReady ? `${diagnostics?.ai.provider || 'AI'} ${diagnostics?.ai.model || ''}` : 'AI fallback mode available'}</small>
        </article>
      </section>
      <section className={`integration-triage-panel full-span ${integrationTriageAction.tone}`}>
        <div className="integration-triage-head">
          <div>
            <span>Integration triage</span>
            <strong>{integrationTriageAction.title}</strong>
            <small>{integrationTriageAction.detail}</small>
          </div>
          <button className={integrationTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={integrationTriageAction.run} disabled={integrationTriageAction.disabled}>{integrationTriageAction.actionLabel}</button>
        </div>
        <div className="integration-triage-grid">
          {integrationTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="integration-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Integration Foundation Map</h3>
            <span className="muted">Data connectors, owned SMTP, feedback webhooks, and AI operations.</span>
          </div>
          <a href="#settings">Open Settings</a>
        </div>
        <div className="integration-foundation-grid">
          {integrationFoundationItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="integration-connector-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Connector Roadmap</h3>
            <span className="muted">Source families and platform services still needed for enterprise-grade data movement.</span>
          </div>
          <a href="#data">Open Data Sources</a>
        </div>
        <div className="integration-connector-grid">
          {integrationConnectorRoadmapItems.map((item) => (
            <article className={item.status === 'Gap' || item.status === 'Fallback' ? 'warn' : 'good'} key={item.family}>
              <span>{item.family}</span>
              <strong>{item.status}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
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
  const contractEndpointCount = contractGroups.reduce((sum, group) => sum + group.endpoints.length, 0);
  const schemaReady = Boolean(diagnostics?.schema.ok && !diagnostics.schema.needs_migration);
  const smtpReady = Boolean(diagnostics?.email_provider.smtp_configured);
  const sendgridReady = Boolean(diagnostics?.email_provider.sendgrid_configured);
  const publicBaseUrl = diagnostics?.public_base_url || 'not configured';
  const publicUrlReady = /^https?:\/\//.test(publicBaseUrl);
  const providerReady = Boolean(
    smtpReady ||
    sendgridReady ||
    diagnostics?.email_provider.provider === 'console',
  );
  const checksHaveRun = Object.keys(checkResults).length > 0;
  const failingSmokeCheck = smokeChecks.find((check) => checkResults[check.key] && !checkResults[check.key].ok);
  const docsNextAction = !schemaReady
    ? 'Resolve schema readiness before treating the API contract as stable.'
    : !providerReady
      ? 'Configure a delivery provider before external clients rely on launch workflows.'
      : checksHaveRun && passedChecks < totalChecks
        ? 'Open the failing workflow card and verify the backing API endpoint.'
        : !checksHaveRun
          ? 'Run workflow checks to validate the live ESP contract from this browser session.'
          : 'Contract is ready for UI integration. Continue using Email Engine as the system of record.';
  const docsTriageAction = !schemaReady
    ? {
      tone: 'warn',
      title: 'Resolve schema contract',
      detail: 'Schema readiness must be current before external clients treat the ESP contract as stable.',
      actionLabel: 'Open Settings',
      run: () => { window.location.hash = '#settings'; },
      disabled: checking,
    }
    : !providerReady
      ? {
        tone: 'warn',
        title: 'Configure delivery contract',
        detail: 'Launch, test-send, tracking, and delivery APIs need a configured outbound provider path.',
        actionLabel: 'Open Integrations',
        run: () => { window.location.hash = '#integrations'; },
        disabled: checking,
      }
      : !smtpReady
        ? {
          tone: 'warn',
          title: 'Document owned SMTP gap',
          detail: 'Owned SMTP remains a first-class platform foundation even when provider adapters are available.',
          actionLabel: 'Open Integrations',
          run: () => { window.location.hash = '#integrations'; },
          disabled: checking,
        }
        : !publicUrlReady
          ? {
            tone: 'warn',
            title: 'Set public endpoints',
            detail: 'Tracking, unsubscribe, and webhook contracts require a reachable PUBLIC_BASE_URL.',
            actionLabel: 'Open Settings',
            run: () => { window.location.hash = '#settings'; },
            disabled: checking,
          }
          : !checksHaveRun
            ? {
              tone: 'warn',
              title: 'Run live contract checks',
              detail: 'Validate the browser-facing ESP workflow APIs before relying on this contract from clients.',
              actionLabel: 'Run Checks',
              run: runSmokeChecks,
              disabled: checking,
            }
            : failingSmokeCheck
              ? {
                tone: 'warn',
                title: 'Review failing workflow',
                detail: `${failingSmokeCheck.label} failed its live endpoint check.`,
                actionLabel: failingSmokeCheck.action,
                run: () => { window.location.hash = failingSmokeCheck.href; },
                disabled: checking,
              }
              : {
                tone: 'good',
                title: 'Contract ready',
                detail: 'Schema, delivery, public endpoint, workflow checks, and object ownership guidance are ready.',
                actionLabel: 'Open API Docs',
                run: () => { window.location.href = '/docs'; },
                disabled: checking,
              };
  const docsTriageItems = [
    {
      label: 'Schema',
      value: schemaReady ? 'Current' : 'Review',
      detail: diagnostics?.schema.current_revision || 'revision unknown',
      tone: schemaReady ? 'good' : 'warn',
    },
    {
      label: 'Owned SMTP',
      value: smtpReady ? 'Ready' : 'Gap',
      detail: smtpReady ? 'Managed SMTP path configured' : sendgridReady ? 'Adapter ready; owned SMTP not configured' : 'No managed SMTP path configured',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Public endpoints',
      value: publicUrlReady ? 'Ready' : 'Missing',
      detail: publicBaseUrl.replace(/^https?:\/\//, ''),
      tone: publicUrlReady ? 'good' : 'warn',
    },
    {
      label: 'Live checks',
      value: `${formatInt(passedChecks)} / ${formatInt(totalChecks)}`,
      detail: checksHaveRun ? 'Browser workflow checks have run' : 'Run checks before client handoff',
      tone: checksHaveRun && passedChecks === totalChecks ? 'good' : 'warn',
    },
    {
      label: 'Object ownership',
      value: formatInt(objectRows.length),
      detail: 'Email Engine remains system of record for ESP objects',
      tone: 'good',
    },
  ];
  const platformGapRows = [
    {
      area: 'Data graph',
      status: 'Gap',
      guidance: 'RDBMS, warehouse, NoSQL, API connectors, multi-entity joins, and client-owned entities need first-class contracts.',
    },
    {
      area: 'Owned SMTP',
      status: smtpReady ? 'Configured' : 'Gap',
      guidance: smtpReady ? 'Managed SMTP path is configured.' : 'SMTP server, MTA policy, send queues, throttling, and domain controls remain platform foundation work.',
    },
    {
      area: 'Deliverability feedback',
      status: publicUrlReady ? 'Partial' : 'Gap',
      guidance: 'Bounce queues, complaint loops, provider webhooks, and reputation feedback need durable event contracts.',
    },
    {
      area: 'Agent layer',
      status: diagnostics?.ai.openai_configured ? 'Configured' : 'Fallback',
      guidance: 'Ever-present agents need OpenAI configuration, persistent memory, handoff state, and workflow observability.',
    },
  ];
  const docsLifecycleItems = [
    {
      label: 'API ownership',
      value: 'Email Engine',
      detail: 'ESP objects should remain owned by Email Engine while external clients integrate through API contracts.',
      tone: 'good',
    },
    {
      label: 'Versioning policy',
      value: schemaReady ? 'Current' : 'Review',
      detail: schemaReady ? 'Schema revision is current for client contract review.' : 'Schema migrations must be current before external client release.',
      tone: schemaReady ? 'good' : 'warn',
    },
    {
      label: 'Client contract',
      value: checksHaveRun && passedChecks === totalChecks ? 'Verified' : 'Pending',
      detail: checksHaveRun ? `${formatInt(passedChecks)} of ${formatInt(totalChecks)} workflow checks passed.` : 'Run live checks before handing this contract to SentientMail or other clients.',
      tone: checksHaveRun && passedChecks === totalChecks ? 'good' : 'warn',
    },
    {
      label: 'Release evidence',
      value: publicUrlReady && providerReady ? 'Partial' : 'Gap',
      detail: publicUrlReady && providerReady ? 'Public endpoint and delivery readiness are visible; release notes still need ownership.' : 'Release evidence should capture diagnostics, smoke checks, and integration notes.',
      tone: 'warn',
    },
  ];

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
      <section className="docs-command-strip full-span" aria-label="ESP contract summary">
        <article className="good">
          <span>API surface</span>
          <strong>{formatInt(contractEndpointCount)} endpoints</strong>
          <small>{formatInt(contractGroups.length)} workflow groups</small>
        </article>
        <article className={schemaReady ? 'good' : 'warn'}>
          <span>Schema contract</span>
          <strong>{schemaReady ? 'Current' : 'Review'}</strong>
          <small>{diagnostics?.schema.current_revision || 'revision unknown'}</small>
        </article>
        <article className={providerReady ? 'good' : 'warn'}>
          <span>Delivery contract</span>
          <strong>{providerReady ? diagnostics?.email_provider.provider || 'Ready' : 'Pending'}</strong>
          <small>{diagnostics?.email_provider.default_from_email || 'default sender unavailable'}</small>
        </article>
        <article className={checksHaveRun && passedChecks === totalChecks ? 'good' : 'warn'}>
          <span>Live checks</span>
          <strong>{formatInt(passedChecks)} / {formatInt(totalChecks)}</strong>
          <small>{checking ? 'checking now' : checksHaveRun ? 'last browser run' : 'not checked'}</small>
        </article>
        <article className="wide">
          <span>Recommended next action</span>
          <strong>{docsNextAction}</strong>
          <small>SentientMail should integrate through Email Engine APIs, not duplicate ESP state.</small>
        </article>
      </section>
      <section className={`docs-triage-panel full-span ${docsTriageAction.tone}`}>
        <div className="docs-triage-head">
          <div>
            <span>Contract triage</span>
            <strong>{docsTriageAction.title}</strong>
            <small>{docsTriageAction.detail}</small>
          </div>
          <button className={docsTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={docsTriageAction.run} disabled={docsTriageAction.disabled}>{docsTriageAction.actionLabel}</button>
        </div>
        <div className="docs-triage-grid">
          {docsTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="docs-gap-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Platform Gap Register</h3>
            <span className="muted">Roadmap guidance for foundations not fully covered by the current API contract.</span>
          </div>
          <a href="#integrations">Open Integrations</a>
        </div>
        <div className="docs-gap-grid">
          {platformGapRows.map((item) => (
            <article className={item.status === 'Configured' ? 'good' : 'warn'} key={item.area}>
              <span>{item.area}</span>
              <strong>{item.status}</strong>
              <small>{item.guidance}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="docs-lifecycle-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>API Lifecycle Readiness</h3>
            <span className="muted">Ownership, versioning, client contract checks, and release evidence.</span>
          </div>
          <a href="/docs">Open API Docs</a>
        </div>
        <div className="docs-lifecycle-grid">
          {docsLifecycleItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
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

function SettingsPage({ diagnostics, onRefresh, currentUser }: {
  diagnostics: SystemDiagnostics | null;
  onRefresh: () => Promise<void>;
  currentUser: AuthUser | null;
}) {
  const [selectedTable, setSelectedTable] = useState('');
  const [status, setStatus] = useState('System settings view loaded.');
  const [busy, setBusy] = useState(false);
  const [users, setUsers] = useState<OperatorUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userStatus, setUserStatus] = useState('Operator users have not been refreshed yet.');
  const [newUser, setNewUser] = useState({
    email: '',
    displayName: '',
    role: 'admin',
    password: '',
    isActive: true,
  });
  const [passwordReset, setPasswordReset] = useState<Record<string, string>>({});
  const counts = Object.entries(diagnostics?.entity_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const tables = diagnostics?.database_tables || [];
  const tableName = selectedTable || tables[0] || '';
  const columns = tableName ? diagnostics?.database_table_columns?.[tableName] || [] : [];
  const canManageUsers = currentUser?.role === 'admin';
  const activeUsers = users.filter((user) => user.is_active).length;
  const adminUsers = users.filter((user) => user.role === 'admin').length;
  const lockedUsers = users.filter((user) => Boolean(user.locked_until)).length;
  const failedLoginCount = users.reduce((sum, user) => sum + Number(user.failed_login_count || 0), 0);
  const schemaCurrent = Boolean(diagnostics?.schema.ok && !diagnostics.schema.needs_migration);
  const smtpReady = Boolean(diagnostics?.email_provider.smtp_configured);
  const sendgridReady = Boolean(diagnostics?.email_provider.sendgrid_configured);
  const publicBaseUrl = diagnostics?.public_base_url || 'not configured';
  const publicUrlReady = /^https?:\/\//.test(publicBaseUrl);
  const aiReady = Boolean(diagnostics?.ai.openai_configured);
  const settingsFoundationItems = [
    {
      label: 'Schema control',
      value: schemaCurrent ? 'Current' : 'Review',
      detail: schemaCurrent ? 'Expected schema revision is deployed.' : 'Migration status must be resolved before production changes.',
      tone: schemaCurrent ? 'good' : 'warn',
    },
    {
      label: 'Owned SMTP control',
      value: smtpReady ? 'Configured' : 'Gap',
      detail: smtpReady ? 'Managed SMTP path is configured.' : 'Owned SMTP server settings, MTA policy, throttling, and domains need admin controls.',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Endpoint control',
      value: publicUrlReady ? 'Configured' : 'Missing',
      detail: publicUrlReady ? publicBaseUrl.replace(/^https?:\/\//, '') : 'PUBLIC_BASE_URL is required for tracking, unsubscribe, and webhook URLs.',
      tone: publicUrlReady ? 'good' : 'warn',
    },
    {
      label: 'AI control',
      value: aiReady ? 'Configured' : 'Fallback',
      detail: aiReady ? `${diagnostics?.ai.provider || 'AI'} ${diagnostics?.ai.model || ''}` : 'OpenAI configuration and model governance are needed for production agents.',
      tone: aiReady ? 'good' : 'warn',
    },
  ];
  const settingsGovernanceItems = [
    {
      label: 'Config ownership',
      value: canManageUsers ? 'Admin' : 'Limited',
      detail: 'Production configuration changes need explicit owner, approval path, and operator role boundaries.',
      tone: canManageUsers ? 'good' : 'warn',
    },
    {
      label: 'Secret governance',
      value: smtpReady || sendgridReady || aiReady ? 'Partial' : 'Gap',
      detail: 'SMTP, provider, AI, and connector secrets need vault references, rotation cadence, and access audit.',
      tone: smtpReady || sendgridReady || aiReady ? 'warn' : 'warn',
    },
    {
      label: 'Policy governance',
      value: smtpReady && aiReady ? 'Partial' : 'Gap',
      detail: 'Owned SMTP, AI tools, imports, and suppression policy need workspace-level controls before automation.',
      tone: smtpReady && aiReady ? 'warn' : 'warn',
    },
    {
      label: 'Release governance',
      value: schemaCurrent && publicUrlReady ? 'Partial' : 'Gap',
      detail: 'Schema, public URL, docs, diagnostics, and smoke-test evidence should be captured before release handoff.',
      tone: schemaCurrent && publicUrlReady ? 'warn' : 'warn',
    },
    {
      label: 'Audit governance',
      value: users.length ? 'Partial' : 'Gap',
      detail: 'Operator changes, provider changes, AI actions, and data imports need immutable audit trails.',
      tone: users.length ? 'warn' : 'warn',
    },
  ];
  const settingsNextAction = !currentUser
    ? 'Sign in to inspect operator account and system readiness.'
    : !canManageUsers
      ? 'Admin access is required to create users or reset operator passwords.'
      : lockedUsers > 0
        ? 'Review locked operator accounts and unlock only after confirming identity.'
        : failedLoginCount > 0
          ? 'Review failed login attempts and reset passwords for affected operators if needed.'
          : !schemaCurrent
            ? 'Resolve schema migration status before changing production account settings.'
            : 'Operator access is stable. Keep admin count tight and refresh users before demos.';
  const settingsTriageAction = !currentUser
    ? {
      tone: 'warn',
      title: 'Sign in to manage settings',
      detail: 'Operator identity is required before changing account, schema, or provider settings.',
      actionLabel: 'Refresh Diagnostics',
      run: refreshDiagnostics,
      disabled: busy,
    }
    : !canManageUsers
      ? {
        tone: 'warn',
        title: 'Require admin access',
        detail: 'Only admins can create operators, unlock accounts, or reset passwords.',
        actionLabel: 'Refresh Users',
        run: loadUsers,
        disabled: usersLoading,
      }
      : lockedUsers > 0
        ? {
          tone: 'warn',
          title: 'Review locked accounts',
          detail: `${formatInt(lockedUsers)} operator account(s) are locked and need identity review.`,
          actionLabel: 'Refresh Users',
          run: loadUsers,
          disabled: usersLoading,
        }
        : failedLoginCount > 0
          ? {
            tone: 'warn',
            title: 'Review failed logins',
            detail: `${formatInt(failedLoginCount)} failed login attempt(s) are present across operators.`,
            actionLabel: 'Refresh Users',
            run: loadUsers,
            disabled: usersLoading,
          }
          : !schemaCurrent
            ? {
              tone: 'warn',
              title: 'Resolve schema state',
              detail: 'Schema readiness should be current before production settings changes.',
              actionLabel: 'Refresh Diagnostics',
              run: refreshDiagnostics,
              disabled: busy,
            }
            : !smtpReady
              ? {
                tone: 'warn',
                title: 'Configure owned SMTP',
                detail: 'Owned SMTP should be managed here as a platform foundation, not only through provider adapters.',
                actionLabel: 'Refresh Diagnostics',
                run: refreshDiagnostics,
                disabled: busy,
              }
              : !publicUrlReady
                ? {
                  tone: 'warn',
                  title: 'Set public base URL',
                  detail: 'Tracking, unsubscribe, and webhook links need a reachable PUBLIC_BASE_URL.',
                  actionLabel: 'Refresh Diagnostics',
                  run: refreshDiagnostics,
                  disabled: busy,
                }
                : !aiReady
                  ? {
                    tone: 'warn',
                    title: 'Configure AI provider',
                    detail: 'OpenAI is in fallback mode; configure it before relying on AI operator workflows.',
                    actionLabel: 'Refresh Diagnostics',
                    run: refreshDiagnostics,
                    disabled: busy,
                  }
                  : {
                    tone: 'good',
                    title: 'Settings ready',
                    detail: 'Admin access, schema, owned SMTP, public URL, and AI provider checks are ready.',
                    actionLabel: 'Refresh Diagnostics',
                    run: refreshDiagnostics,
                    disabled: busy,
                  };
  const settingsTriageItems = [
    {
      label: 'Access',
      value: canManageUsers ? 'Admin' : currentUser ? 'Limited' : 'Anonymous',
      detail: currentUser?.email || 'No active operator session',
      tone: canManageUsers ? 'good' : 'warn',
    },
    {
      label: 'Owned SMTP',
      value: smtpReady ? 'Ready' : 'Missing',
      detail: smtpReady ? 'Managed SMTP configured' : sendgridReady ? 'SendGrid adapter is ready, owned SMTP is not' : 'No managed SMTP path configured',
      tone: smtpReady ? 'good' : 'warn',
    },
    {
      label: 'Public URL',
      value: publicUrlReady ? 'Ready' : 'Missing',
      detail: publicBaseUrl.replace(/^https?:\/\//, ''),
      tone: publicUrlReady ? 'good' : 'warn',
    },
    {
      label: 'Schema',
      value: schemaCurrent ? 'Current' : 'Review',
      detail: diagnostics?.schema.current_revision || 'revision unknown',
      tone: schemaCurrent ? 'good' : 'warn',
    },
    {
      label: 'AI provider',
      value: aiReady ? 'Ready' : 'Fallback',
      detail: diagnostics?.ai.model || 'Deterministic fallback available',
      tone: aiReady ? 'good' : 'warn',
    },
  ];

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

  async function loadUsers() {
    setUsersLoading(true);
    setUserStatus('Refreshing operator users...');
    try {
      const data = await fetchJson<ListResponse<OperatorUser>>('/api/v1/users/list?limit=100&offset=0');
      setUsers(data.items || []);
      setUserStatus(`${formatInt(data.total)} operator users loaded.`);
    } catch (error) {
      setUserStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUsersLoading(false);
    }
  }

  useEffect(() => {
    if (canManageUsers) {
      loadUsers();
    } else {
      setUsers([]);
      setUserStatus('Sign in as an admin to manage operator users.');
    }
  }, [canManageUsers]);

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUsersLoading(true);
    setUserStatus('Creating operator user...');
    try {
      await fetchJson<OperatorUser>('/api/v1/users', {
        method: 'POST',
        body: JSON.stringify({
          email: newUser.email,
          display_name: newUser.displayName,
          role: newUser.role,
          password: newUser.password,
          is_active: newUser.isActive,
        }),
      });
      setNewUser({ email: '', displayName: '', role: 'admin', password: '', isActive: true });
      await loadUsers();
      setUserStatus('Operator user created.');
    } catch (error) {
      setUserStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUsersLoading(false);
    }
  }

  async function updateUser(user: OperatorUser, updates: Partial<Pick<OperatorUser, 'display_name' | 'role' | 'is_active'>>) {
    setUsersLoading(true);
    setUserStatus(`Updating ${user.email}...`);
    try {
      await fetchJson<OperatorUser>(`/api/v1/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      });
      await loadUsers();
      setUserStatus(`${user.email} updated.`);
    } catch (error) {
      setUserStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUsersLoading(false);
    }
  }

  async function resetPassword(user: OperatorUser) {
    const password = passwordReset[user.id] || '';
    if (password.length < 8) {
      setUserStatus('Error: Password must be at least 8 characters.');
      return;
    }
    setUsersLoading(true);
    setUserStatus(`Resetting password for ${user.email}...`);
    try {
      await fetchJson<OperatorUser>(`/api/v1/users/${user.id}/password`, {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      setPasswordReset((current) => ({ ...current, [user.id]: '' }));
      await loadUsers();
      setUserStatus(`${user.email} password reset.`);
    } catch (error) {
      setUserStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUsersLoading(false);
    }
  }

  async function unlockUser(user: OperatorUser) {
    setUsersLoading(true);
    setUserStatus(`Unlocking ${user.email}...`);
    try {
      await fetchJson<OperatorUser>(`/api/v1/users/${user.id}/unlock`, { method: 'POST' });
      await loadUsers();
      setUserStatus(`${user.email} unlocked.`);
    } catch (error) {
      setUserStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUsersLoading(false);
    }
  }

  return (
    <section className="page-grid">
      <section className="metric-grid full-span compact-metrics">
        <MetricCard metric={{ label: 'System', value: diagnostics?.ok ? 'Healthy' : 'Review', change: diagnostics?.environment || 'environment unknown', tone: diagnostics?.ok ? 'good' : 'warn' }} />
        <MetricCard metric={{ label: 'Schema', value: diagnostics?.schema.needs_migration ? 'Migration needed' : 'Current', change: diagnostics?.schema.current_revision || 'no revision', tone: diagnostics?.schema.needs_migration ? 'warn' : 'good' }} />
        <MetricCard metric={{ label: 'Errors', value: formatInt(diagnostics?.errors.length || 0), change: 'diagnostic findings', tone: diagnostics?.errors.length ? 'warn' : 'good' }} />
      </section>
      <section className="settings-command-strip full-span" aria-label="Settings readiness summary">
        <article className={currentUser ? 'good' : 'warn'}>
          <span>Signed in</span>
          <strong>{currentUser?.display_name || 'Anonymous'}</strong>
          <small>{currentUser?.role || 'no active role'}</small>
        </article>
        <article className={canManageUsers ? 'good' : 'warn'}>
          <span>Admin access</span>
          <strong>{canManageUsers ? 'Enabled' : 'Read only'}</strong>
          <small>{formatInt(adminUsers)} admin users loaded</small>
        </article>
        <article className={lockedUsers ? 'warn' : 'good'}>
          <span>Account health</span>
          <strong>{formatInt(activeUsers)} active</strong>
          <small>{formatInt(lockedUsers)} locked / {formatInt(failedLoginCount)} failures</small>
        </article>
        <article className={schemaCurrent ? 'good' : 'warn'}>
          <span>Schema</span>
          <strong>{schemaCurrent ? 'Current' : 'Review'}</strong>
          <small>{diagnostics?.schema.current_revision || 'revision unknown'}</small>
        </article>
        <article className="wide">
          <span>Recommended next action</span>
          <strong>{settingsNextAction}</strong>
          <small>{userStatus}</small>
        </article>
      </section>
      <section className={`settings-triage-panel full-span ${settingsTriageAction.tone}`}>
        <div className="settings-triage-head">
          <div>
            <span>Settings triage</span>
            <strong>{settingsTriageAction.title}</strong>
            <small>{settingsTriageAction.detail}</small>
          </div>
          <button className={settingsTriageAction.tone === 'warn' ? 'primary' : 'ghost'} type="button" onClick={settingsTriageAction.run} disabled={settingsTriageAction.disabled}>{settingsTriageAction.actionLabel}</button>
        </div>
        <div className="settings-triage-grid">
          {settingsTriageItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="settings-foundation-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Foundation Control Plane</h3>
            <span className="muted">Schema, owned SMTP, public endpoint, and AI provider governance.</span>
          </div>
          <button className="link-button" type="button" onClick={refreshDiagnostics} disabled={busy}>Refresh Diagnostics</button>
        </div>
        <div className="settings-foundation-grid">
          {settingsFoundationItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="settings-governance-panel full-span">
        <div className="panel-head compact-head">
          <div>
            <h3>Platform Governance Contract</h3>
            <span className="muted">Configuration ownership, secrets, policy controls, release evidence, and audit governance.</span>
          </div>
          <button className="link-button" type="button" onClick={refreshDiagnostics} disabled={busy}>Refresh Diagnostics</button>
        </div>
        <div className="settings-governance-grid">
          {settingsGovernanceItems.map((item) => (
            <article className={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </article>
          ))}
        </div>
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
      {canManageUsers ? (
        <>
          <section className="panel full-span campaign-workbench">
            <div className="panel-head"><h2>Operator Accounts</h2><button className="ghost" onClick={loadUsers} disabled={usersLoading}>Refresh Users</button></div>
            <form className="form-grid" onSubmit={createUser}>
              <label>
                Email
                <input
                  autoComplete="email"
                  onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))}
                  required
                  type="email"
                  value={newUser.email}
                />
              </label>
              <label>
                Display name
                <input
                  onChange={(event) => setNewUser((current) => ({ ...current, displayName: event.target.value }))}
                  required
                  value={newUser.displayName}
                />
              </label>
              <label>
                Role
                <select
                  onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value }))}
                  value={newUser.role}
                >
                  <option value="admin">admin</option>
                  <option value="operator">operator</option>
                  <option value="viewer">viewer</option>
                </select>
              </label>
              <label>
                Temporary password
                <input
                  autoComplete="new-password"
                  minLength={8}
                  onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))}
                  required
                  type="password"
                  value={newUser.password}
                />
              </label>
              <label className="checkbox-label">
                <input
                  checked={newUser.isActive}
                  onChange={(event) => setNewUser((current) => ({ ...current, isActive: event.target.checked }))}
                  type="checkbox"
                />
                Active account
              </label>
              <div className="button-row">
                <button className="primary" disabled={usersLoading} type="submit">Create User</button>
              </div>
            </form>
            <div className={`operation-banner ${userStatus.startsWith('Error:') ? 'warn' : ''}`}>
              <strong>{usersLoading ? 'Working' : 'Status'}</strong>
              <span>{userStatus}</span>
            </div>
          </section>
          <section className="panel table-panel full-span">
            <div className="panel-head"><h2>Operator Directory</h2><span className="muted">{formatInt(users.length)} users</span></div>
            {users.length ? (
              <table>
                <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Last login</th><th>Failures</th><th>Password</th><th>Actions</th></tr></thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td><strong>{user.display_name}</strong><br /><span className="muted">{user.email}</span></td>
                      <td>
                        <select
                          aria-label={`Role for ${user.email}`}
                          onChange={(event) => updateUser(user, { role: event.target.value })}
                          value={user.role}
                        >
                          <option value="admin">admin</option>
                          <option value="operator">operator</option>
                          <option value="viewer">viewer</option>
                        </select>
                      </td>
                      <td><span className="pill">{user.is_active ? 'active' : 'inactive'}</span></td>
                      <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'never'}</td>
                      <td>{user.locked_until ? `locked until ${new Date(user.locked_until).toLocaleString()}` : formatInt(user.failed_login_count)}</td>
                      <td>
                        <input
                          aria-label={`New password for ${user.email}`}
                          minLength={8}
                          onChange={(event) => setPasswordReset((current) => ({ ...current, [user.id]: event.target.value }))}
                          placeholder="New password"
                          type="password"
                          value={passwordReset[user.id] || ''}
                        />
                      </td>
                      <td>
                        <div className="button-row compact-actions">
                          <button className="ghost" disabled={usersLoading} onClick={() => updateUser(user, { is_active: !user.is_active })}>
                            {user.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button className="ghost" disabled={usersLoading || !(passwordReset[user.id] || '')} onClick={() => resetPassword(user)}>
                            Reset
                          </button>
                          <button className="ghost" disabled={usersLoading || (!user.locked_until && user.failed_login_count === 0)} onClick={() => unlockUser(user)}>
                            Unlock
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <EmptyState title="No operator users loaded" detail="Refresh users or create the first account." />}
          </section>
        </>
      ) : (
        <section className="panel full-span">
          <div className="panel-head"><h2>Operator Accounts</h2><span className="muted">Admin only</span></div>
          <EmptyState title="Operator users require admin access" detail={userStatus} />
        </section>
      )}
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
  const [authRequired, setAuthRequired] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authRefreshKey, setAuthRefreshKey] = useState(0);
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
    onAuthRequired(() => {
      setAuthUser(null);
      setAuthRequired(true);
    });
    return () => onAuthRequired(null);
  }, []);

  useEffect(() => {
    let active = true;
    async function loadCurrentUser() {
      try {
        const response = await fetch('/api/v1/auth/me', { credentials: 'include' });
        if (!response.ok) return;
        const data = await response.json() as AuthResponse;
        if (active) setAuthUser(data.user);
      } catch {
        // Anonymous mode is allowed until REQUIRE_GUI_AUTH is enabled.
      }
    }
    loadCurrentUser();
    return () => {
      active = false;
    };
  }, [authRefreshKey]);

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
        if (error instanceof AuthRequiredError) {
          if (active) {
            setAuthRequired(true);
            setDashboard((current) => ({ ...current, loading: false, error: null }));
          }
          return;
        }
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
  }, [authRefreshKey]);

  async function handleLogout() {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' });
    setAuthUser(null);
    setAuthRequired(true);
  }

  const liveMetrics = useMemo(() => metricsFromOverview(dashboard.overview), [dashboard.overview]);
  const liveCampaigns = useMemo(
    () => campaignsFromPerformance(dashboard.campaigns),
    [dashboard.campaigns],
  );
  const status = pageSubtitle(activePage, dashboard);
  if (authRequired) {
    return (
      <LoginScreen
        onLogin={(user) => {
          setAuthUser(user);
          setAuthRequired(false);
          setDashboard((current) => ({ ...current, loading: true, error: null }));
          setAuthRefreshKey((value) => value + 1);
        }}
      />
    );
  }

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
          campaigns={dashboard.campaignItems}
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
          currentUser={authUser}
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
        <Header
          activePage={activePage}
          operation={operationNotice}
          onLogout={handleLogout}
          status={status}
          title={pageTitle(activePage)}
          user={authUser}
        />
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
