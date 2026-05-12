import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Compass, ChevronRight, ChevronLeft, Plus, X, Check, AlertTriangle, FileText,
  Settings as SettingsIcon, Inbox, Sparkles, Download, Upload, Trash2, Edit3,
  Users, ArrowRight, Circle, CheckCircle2, Clock, ShieldAlert, Filter, Loader2,
  GitBranch, Activity, ArrowUpRight, BookOpen
} from 'lucide-react';

/* =========================================================================
   DEFAULT DATA — fully editable through the Settings tab at runtime
   ========================================================================= */

const DEFAULT_FEATURES = {
  documentAnalysis: true,
  riskScoring: true,
  autoAssignment: true,
  csvExport: true,
  workExport: true,
  slaTracking: false,
  emailNotifications: false,
};

const DEFAULT_WORKFLOWS = [
  { id: 'fast', name: 'Fast-Track', stages: ['draft', 'final_qa'] },
  { id: 'standard', name: 'Standard', stages: ['draft', 'lead_review', 'final_qa'] },
  { id: 'extended', name: 'Extended', stages: ['draft', 'peer_review', 'lead_review', 'final_qa'] },
];

const STAGE_LABELS = {
  draft: 'Draft',
  peer_review: 'Peer Review',
  lead_review: 'Team Lead Review',
  final_qa: 'Final QA / QC',
  approved: 'Approved',
  returned: 'Returned',
};

const DEFAULT_TEMPLATES = [
  {
    id: 'waterfall',
    name: 'Waterfall — Linear Phase-Gate',
    description: 'Sequential phases with formal gate reviews. Best for well-defined scope with regulatory or audit requirements.',
    tags: ['infra', 'long-duration', 'regulated', 'large-team', 'fixed-scope'],
    defaultWorkflow: 'extended',
    checkpoints: ['Requirements gate', 'Design gate', 'Build gate', 'Test gate', 'Deploy gate', 'Closure review'],
    riskBase: 3,
  },
  {
    id: 'agile-sprint',
    name: 'Agile Sprint Schedule',
    description: 'Iterative 2-week sprints with retrospectives. Suits software work with evolving scope.',
    tags: ['software', 'medium-duration', 'iterative', 'small-team', 'medium-team'],
    defaultWorkflow: 'standard',
    checkpoints: ['Sprint planning', 'Daily standup', 'Sprint review', 'Retrospective', 'Backlog refinement'],
    riskBase: 2,
  },
  {
    id: 'rolling-wave',
    name: 'Rolling-Wave Planning',
    description: 'Detailed near-term planning, high-level long-term. For projects with downstream uncertainty.',
    tags: ['research', 'long-duration', 'uncertain-scope', 'medium-team'],
    defaultWorkflow: 'standard',
    checkpoints: ['Initial baseline', 'Wave 1 detail', 'Wave 2 plan', 'Periodic re-baselining'],
    riskBase: 3,
  },
  {
    id: 'short-turnaround',
    name: 'Short-Turnaround Schedule',
    description: 'Compressed schedule for sub-3-month efforts with a small team and clear scope.',
    tags: ['software', 'process', 'short-duration', 'small-team', 'low-risk', 'fixed-scope'],
    defaultWorkflow: 'fast',
    checkpoints: ['Kickoff', 'Midpoint review', 'Pre-handover check', 'Closeout'],
    riskBase: 1,
  },
  {
    id: 'program-master',
    name: 'Program Master Schedule',
    description: 'Multi-project coordination with cross-stream dependencies and integrated milestones.',
    tags: ['infra', 'software', 'long-duration', 'large-team', 'high-dependency'],
    defaultWorkflow: 'extended',
    checkpoints: ['Program charter', 'Stream integration points', 'Quarterly stage gates', 'Benefits realization'],
    riskBase: 4,
  },
];

const DEFAULT_CHANGE_TYPES = [
  {
    id: 'standard',
    name: 'Standard Change',
    description: 'Pre-approved, low-risk, follows established procedure with predictable outcome.',
    conditions: ['routine', 'low', 'team', 'easy', 'yes'],
    defaultWorkflow: 'fast',
    requiredApprovals: ['Team Lead'],
    sla: '5 business days',
    riskBase: 1,
  },
  {
    id: 'normal',
    name: 'Normal Change',
    description: 'Non-emergency change requiring CAB review and full risk assessment.',
    conditions: ['routine', 'medium', 'multi-team', 'moderate', 'no'],
    defaultWorkflow: 'standard',
    requiredApprovals: ['Team Lead', 'Change Manager'],
    sla: '10 business days',
    riskBase: 3,
  },
  {
    id: 'major',
    name: 'Major Change',
    description: 'High-impact change affecting multiple systems or org-wide processes. Full impact analysis required.',
    conditions: ['expedited', 'high', 'org', 'hard', 'no'],
    defaultWorkflow: 'extended',
    requiredApprovals: ['Team Lead', 'Change Manager', 'Executive Sponsor'],
    sla: '20 business days',
    riskBase: 4,
  },
  {
    id: 'emergency',
    name: 'Emergency Change',
    description: 'Urgent change to restore service or prevent imminent harm. Expedited approval with full retrospective required.',
    conditions: ['emergency', 'high'],
    defaultWorkflow: 'standard',
    requiredApprovals: ['On-call Lead', 'Change Manager'],
    sla: 'Same business day',
    riskBase: 5,
  },
];

const SCHEDULE_QUESTIONS = [
  { id: 'type', q: 'What is the primary project type?', options: [
    { value: 'infra', label: 'Infrastructure / Engineering / Construction' },
    { value: 'software', label: 'Software / Digital product' },
    { value: 'process', label: 'Process / Operational change' },
    { value: 'research', label: 'Research / Discovery / R&D' },
  ]},
  { id: 'duration', q: 'Expected duration?', options: [
    { value: 'short-duration', label: 'Under 3 months' },
    { value: 'medium-duration', label: '3 to 12 months' },
    { value: 'long-duration', label: 'Over 12 months' },
  ]},
  { id: 'team', q: 'Team size?', options: [
    { value: 'small-team', label: 'Fewer than 5 people' },
    { value: 'medium-team', label: '5 to 15 people' },
    { value: 'large-team', label: 'More than 15 people' },
  ]},
  { id: 'scope', q: 'How well-defined is the scope?', options: [
    { value: 'fixed-scope', label: 'Clearly defined, low likelihood of change' },
    { value: 'iterative', label: 'Will evolve as we learn' },
    { value: 'uncertain-scope', label: 'Significant downstream uncertainty' },
  ]},
  { id: 'compliance', q: 'Regulatory or audit requirements?', options: [
    { value: 'low-risk', label: 'None or minimal' },
    { value: 'regulated', label: 'Yes — formal compliance needed' },
  ]},
  { id: 'deps', q: 'Cross-team dependencies?', options: [
    { value: 'low-dependency', label: 'Few — mostly self-contained' },
    { value: 'high-dependency', label: 'Many — multiple streams must align' },
  ]},
];

const CHANGE_QUESTIONS = [
  { id: 'urgency', q: 'How urgent is this change?', options: [
    { value: 'routine', label: 'Routine — normal lead time available' },
    { value: 'expedited', label: 'Expedited — needed sooner than standard' },
    { value: 'emergency', label: 'Emergency — service restoration or imminent harm' },
  ]},
  { id: 'risk', q: 'Assessed risk level?', options: [
    { value: 'low', label: 'Low — predictable, proven, isolated' },
    { value: 'medium', label: 'Medium — some unknowns, partial precedent' },
    { value: 'high', label: 'High — novel, broad blast radius, or limited testing' },
  ]},
  { id: 'scope', q: 'Impact scope?', options: [
    { value: 'team', label: 'Single team only' },
    { value: 'multi-team', label: 'Multiple teams' },
    { value: 'org', label: 'Organisation-wide' },
  ]},
  { id: 'reversibility', q: 'How reversible if something goes wrong?', options: [
    { value: 'easy', label: 'Easy — rollback is trivial' },
    { value: 'moderate', label: 'Moderate — rollback possible but costly' },
    { value: 'hard', label: 'Difficult or irreversible' },
  ]},
  { id: 'precedent', q: 'Has a similar change been done before?', options: [
    { value: 'yes', label: 'Yes — pre-approved or repeatable' },
    { value: 'no', label: 'No — novel change' },
  ]},
];

const DEFAULT_REVIEWERS = [
  { id: 'r1', name: 'Aisha Okonkwo', role: 'Team Lead', expertise: ['software', 'iterative', 'medium-team'], capacity: 4 },
  { id: 'r2', name: 'Daniel Reyes', role: 'Team Lead', expertise: ['infra', 'regulated', 'large-team', 'fixed-scope'], capacity: 4 },
  { id: 'r3', name: 'Priya Shankar', role: 'Team Lead', expertise: ['process', 'research', 'small-team', 'uncertain-scope'], capacity: 3 },
];

/* =========================================================================
   PERSISTENT STORAGE HOOK
   ========================================================================= */

function usePersistent(key, defaultValue) {
  const [value, setValue] = useState(defaultValue);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await window.storage.get(key);
        if (!cancelled) {
          setValue(result ? JSON.parse(result.value) : defaultValue);
          setLoaded(true);
        }
      } catch {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [key]);

  useEffect(() => {
    if (!loaded) return;
    (async () => {
      try { await window.storage.set(key, JSON.stringify(value)); }
      catch (e) { console.error('Save failed:', key, e); }
    })();
  }, [key, value, loaded]);

  return [value, setValue, loaded];
}

/* =========================================================================
   SCORING & RECOMMENDATION LOGIC
   ========================================================================= */

const HIGH_RISK_TAGS = new Set([
  'high', 'emergency', 'org', 'hard', 'uncertain-scope', 'regulated',
  'high-dependency', 'large-team', 'long-duration', 'no'
]);
const MEDIUM_RISK_TAGS = new Set([
  'medium', 'expedited', 'multi-team', 'moderate', 'iterative',
  'medium-team', 'medium-duration'
]);

function computeRiskScore(answers, base = 0) {
  let score = base;
  Object.values(answers || {}).forEach(v => {
    if (HIGH_RISK_TAGS.has(v)) score += 2;
    else if (MEDIUM_RISK_TAGS.has(v)) score += 1;
  });
  return Math.min(10, score);
}

function rankTemplates(templates, answers) {
  const values = Object.values(answers);
  return templates
    .map(t => ({
      ...t,
      score: t.tags.reduce((acc, tag) => acc + (values.includes(tag) ? 1 : 0), 0)
    }))
    .sort((a, b) => b.score - a.score);
}

function rankChangeTypes(types, answers) {
  const values = Object.values(answers);
  return types
    .map(t => ({
      ...t,
      score: (t.conditions || []).reduce((acc, c) => acc + (values.includes(c) ? 1 : 0), 0)
    }))
    .sort((a, b) => b.score - a.score);
}

function pickReviewer(reviewers, items, templateOrType) {
  const tags = templateOrType.tags || templateOrType.conditions || [];
  const loadByReviewer = items
    .filter(i => i.assignedReviewer && i.currentStage !== 'approved' && i.currentStage !== 'returned')
    .reduce((m, i) => ({ ...m, [i.assignedReviewer]: (m[i.assignedReviewer] || 0) + 1 }), {});

  const scored = reviewers
    .map(r => {
      const overlap = (r.expertise || []).reduce((acc, e) => acc + (tags.includes(e) ? 1 : 0), 0);
      const load = loadByReviewer[r.id] || 0;
      const headroom = (r.capacity || 1) - load;
      return { r, score: overlap * 2 + headroom };
    })
    .filter(({ r }) => ((loadByReviewer[r.id] || 0) < (r.capacity || 1)))
    .sort((a, b) => b.score - a.score);
  return scored[0]?.r || reviewers[0] || null;
}

/* =========================================================================
   SHARED UI ATOMS
   ========================================================================= */

const Button = ({ children, variant = 'primary', size = 'md', className = '', ...props }) => {
  const base = 'inline-flex items-center justify-center gap-2 font-medium transition-all rounded-sm';
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-sm' };
  const variants = {
    primary: 'bg-[#A0432C] text-[#FAF7F2] hover:bg-[#8a3a25]',
    secondary: 'bg-[#1A1A1A] text-[#FAF7F2] hover:bg-[#2a2a2a]',
    ghost: 'bg-transparent text-[#1A1A1A] hover:bg-[#E8E2D5] border border-[#D4CCB9]',
    danger: 'bg-transparent text-[#A0432C] hover:bg-[#F2E5DE] border border-[#D4CCB9]',
  };
  return <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>{children}</button>;
};

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#FDFBF6] border border-[#E5DDC9] rounded-sm ${className}`}>{children}</div>
);

const Pill = ({ children, tone = 'neutral' }) => {
  const tones = {
    neutral: 'bg-[#E8E2D5] text-[#3A3A3A]',
    rust: 'bg-[#F2E5DE] text-[#A0432C]',
    moss: 'bg-[#E0E5DA] text-[#4A5A3A]',
    ink: 'bg-[#1A1A1A] text-[#FAF7F2]',
    warn: 'bg-[#F5E6CC] text-[#8a5a1a]',
  };
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] uppercase tracking-wider rounded-sm ${tones[tone]}`}>{children}</span>;
};

const SectionTitle = ({ children, eyebrow }) => (
  <div className="mb-6">
    {eyebrow && <div className="text-[10px] uppercase tracking-[0.2em] text-[#A0432C] mb-1.5">{eyebrow}</div>}
    <h2 className="font-display text-3xl text-[#1A1A1A] leading-tight">{children}</h2>
  </div>
);

const Input = ({ className = '', ...props }) => (
  <input className={`w-full px-3 py-2 bg-[#FDFBF6] border border-[#D4CCB9] focus:border-[#A0432C] focus:outline-none rounded-sm text-sm text-[#1A1A1A] ${className}`} {...props} />
);

const Textarea = ({ className = '', ...props }) => (
  <textarea className={`w-full px-3 py-2 bg-[#FDFBF6] border border-[#D4CCB9] focus:border-[#A0432C] focus:outline-none rounded-sm text-sm text-[#1A1A1A] resize-y ${className}`} {...props} />
);

const Label = ({ children }) => (
  <label className="block text-xs uppercase tracking-wider text-[#5A5A5A] mb-1.5">{children}</label>
);

const Select = ({ className = '', children, ...props }) => (
  <select className={`w-full px-3 py-2 bg-[#FDFBF6] border border-[#D4CCB9] focus:border-[#A0432C] focus:outline-none rounded-sm text-sm text-[#1A1A1A] ${className}`} {...props}>{children}</select>
);

const RiskBar = ({ score }) => {
  const pct = (score / 10) * 100;
  const color = score >= 7 ? '#A0432C' : score >= 4 ? '#C58A30' : '#6B7A4F';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1 bg-[#E5DDC9] rounded-full overflow-hidden">
        <div style={{ width: `${pct}%`, background: color }} className="h-full transition-all" />
      </div>
      <span className="font-display text-lg text-[#1A1A1A]">{score}<span className="text-xs text-[#8A8A8A]">/10</span></span>
    </div>
  );
};

/* =========================================================================
   WIZARD COMPONENT — used for both schedule and change
   ========================================================================= */

function Wizard({ kind, questions, options, reviewers, items, features, onSubmit, onCancel }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [title, setTitle] = useState('');
  const [submitter, setSubmitter] = useState('');
  const [notes, setNotes] = useState('');
  const [chosenId, setChosenId] = useState(null);
  const [workflowId, setWorkflowId] = useState('standard');

  const totalQuestions = questions.length;
  const phase = step < totalQuestions ? 'questions' : 'review';

  const ranked = useMemo(() => {
    if (kind === 'schedule') return rankTemplates(options, answers);
    return rankChangeTypes(options, answers);
  }, [kind, options, answers]);

  const chosen = ranked.find(o => o.id === chosenId) || ranked[0];

  useEffect(() => {
    if (chosen && !chosenId) setChosenId(chosen.id);
    if (chosen) setWorkflowId(chosen.defaultWorkflow || 'standard');
  }, [chosen?.id]);

  const risk = useMemo(() => computeRiskScore(answers, chosen?.riskBase || 0), [answers, chosen]);

  const autoReviewer = useMemo(() => {
    if (!features.autoAssignment || !chosen) return null;
    return pickReviewer(reviewers, items, chosen);
  }, [features.autoAssignment, reviewers, items, chosen]);

  const canSubmit = title.trim() && submitter.trim() && chosen;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({
      title: title.trim(),
      submittedBy: submitter.trim(),
      notes: notes.trim(),
      type: kind,
      typeId: chosen.id,
      typeName: chosen.name,
      workflowId,
      answers,
      riskScore: risk,
      assignedReviewer: autoReviewer?.id || null,
    });
  };

  if (phase === 'questions') {
    const cur = questions[step];
    return (
      <div className="max-w-2xl">
        <div className="flex items-center gap-1.5 mb-8">
          {questions.map((_, i) => (
            <div key={i} className={`h-0.5 flex-1 transition-all ${i <= step ? 'bg-[#A0432C]' : 'bg-[#E5DDC9]'}`} />
          ))}
        </div>
        <div className="text-[10px] uppercase tracking-[0.2em] text-[#A0432C] mb-2">Question {step + 1} of {totalQuestions}</div>
        <h3 className="font-display text-2xl text-[#1A1A1A] mb-6 leading-snug">{cur.q}</h3>
        <div className="space-y-2 mb-8">
          {cur.options.map(opt => (
            <button
              key={opt.value}
              onClick={() => { setAnswers(a => ({ ...a, [cur.id]: opt.value })); setTimeout(() => setStep(s => s + 1), 150); }}
              className={`w-full text-left px-4 py-3.5 border rounded-sm transition-all text-sm ${
                answers[cur.id] === opt.value
                  ? 'border-[#A0432C] bg-[#F2E5DE] text-[#1A1A1A]'
                  : 'border-[#D4CCB9] bg-[#FDFBF6] hover:border-[#A0432C] text-[#3A3A3A]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={() => step === 0 ? onCancel() : setStep(s => s - 1)}>
            <ChevronLeft size={14} /> {step === 0 ? 'Cancel' : 'Back'}
          </Button>
          {answers[cur.id] && (
            <Button size="sm" onClick={() => setStep(s => s + 1)}>
              {step === totalQuestions - 1 ? 'See recommendation' : 'Next'} <ChevronRight size={14} />
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <SectionTitle eyebrow="Recommendation">Based on your answers</SectionTitle>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-6">
        {ranked.slice(0, 3).map((opt, idx) => (
          <button
            key={opt.id}
            onClick={() => { setChosenId(opt.id); setWorkflowId(opt.defaultWorkflow || 'standard'); }}
            className={`text-left p-4 border rounded-sm transition-all ${
              chosenId === opt.id
                ? 'border-[#A0432C] bg-[#F2E5DE]'
                : 'border-[#D4CCB9] bg-[#FDFBF6] hover:border-[#A0432C]'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <Pill tone={idx === 0 ? 'rust' : 'neutral'}>{idx === 0 ? 'Top match' : `Option ${idx + 1}`}</Pill>
              <span className="font-display text-2xl text-[#A0432C]">{opt.score}</span>
            </div>
            <div className="font-display text-lg text-[#1A1A1A] leading-tight mb-1">{opt.name}</div>
            <div className="text-xs text-[#5A5A5A] leading-relaxed">{opt.description}</div>
          </button>
        ))}
      </div>

      {chosen && (
        <Card className="p-5 mb-6">
          <div className="font-display text-xl text-[#1A1A1A] mb-1">{chosen.name}</div>
          <p className="text-sm text-[#5A5A5A] mb-4">{chosen.description}</p>

          {chosen.checkpoints && (
            <div className="mb-4">
              <Label>Built-in checkpoints</Label>
              <div className="flex flex-wrap gap-1.5">
                {chosen.checkpoints.map(c => <Pill key={c} tone="neutral">{c}</Pill>)}
              </div>
            </div>
          )}

          {chosen.requiredApprovals && (
            <div className="mb-4">
              <Label>Required approvals</Label>
              <div className="flex flex-wrap gap-1.5">
                {chosen.requiredApprovals.map(a => <Pill key={a} tone="ink">{a}</Pill>)}
              </div>
            </div>
          )}

          {chosen.sla && (
            <div className="mb-4 flex items-center gap-2">
              <Clock size={14} className="text-[#5A5A5A]" />
              <span className="text-sm text-[#3A3A3A]">SLA: {chosen.sla}</span>
            </div>
          )}

          {features.riskScoring && (
            <div className="pt-4 border-t border-[#E5DDC9]">
              <Label>Risk profile</Label>
              <RiskBar score={risk} />
              {risk >= 7 && (
                <div className="mt-2 text-xs text-[#A0432C] flex items-start gap-1.5">
                  <ShieldAlert size={12} className="mt-0.5 shrink-0" />
                  <span>High risk — recommend escalating to Extended workflow and flagging for executive review.</span>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      <Card className="p-5 mb-6 space-y-4">
        <div>
          <Label>Submission title</Label>
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder={kind === 'schedule' ? 'e.g. Q3 platform migration schedule' : 'e.g. Database failover procedure update'} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Submitted by</Label>
            <Input value={submitter} onChange={e => setSubmitter(e.target.value)} placeholder="Your name" />
          </div>
          <div>
            <Label>Workflow</Label>
            <Select value={workflowId} onChange={e => setWorkflowId(e.target.value)}>
              {DEFAULT_WORKFLOWS.map(w => (
                <option key={w.id} value={w.id}>{w.name} ({w.stages.length} stages)</option>
              ))}
            </Select>
          </div>
        </div>
        <div>
          <Label>Notes for reviewers (optional)</Label>
          <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} placeholder="Context, links, anything reviewers should know..." />
        </div>
        {features.autoAssignment && autoReviewer && (
          <div className="flex items-center gap-2 text-xs text-[#5A5A5A] pt-2 border-t border-[#E5DDC9]">
            <Users size={12} />
            <span>Auto-assigned reviewer: <strong className="text-[#1A1A1A]">{autoReviewer.name}</strong> ({autoReviewer.role})</span>
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="ghost" size="md" onClick={() => setStep(s => s - 1)}>
          <ChevronLeft size={14} /> Back to questions
        </Button>
        <Button onClick={handleSubmit} disabled={!canSubmit}>
          Submit to pipeline <ChevronRight size={14} />
        </Button>
      </div>
    </div>
  );
}

/* =========================================================================
   PIPELINE / ITEM DETAIL
   ========================================================================= */

function PipelineView({ items, setItems, workflows, reviewers, features, openDetail }) {
  const [stageFilter, setStageFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    return items.filter(i => {
      if (stageFilter !== 'all' && i.currentStage !== stageFilter) return false;
      if (typeFilter !== 'all' && i.type !== typeFilter) return false;
      if (search && !i.title.toLowerCase().includes(search.toLowerCase()) && !i.submittedBy.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    }).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
  }, [items, stageFilter, typeFilter, search]);

  const exportCsv = () => {
    const headers = ['ID', 'Title', 'Type', 'Template/Change Type', 'Workflow', 'Current Stage', 'Risk', 'Submitted By', 'Reviewer', 'Created', 'Notes'];
    const rows = filtered.map(i => [
      i.id, i.title, i.type, i.typeName, i.workflowId, STAGE_LABELS[i.currentStage] || i.currentStage,
      i.riskScore ?? '', i.submittedBy, reviewers.find(r => r.id === i.assignedReviewer)?.name || '',
      new Date(i.createdAt).toISOString(), (i.notes || '').replace(/\n/g, ' ')
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `pmo-pipeline-${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const stages = Array.from(new Set(workflows.flatMap(w => w.stages))).concat(['approved', 'returned']);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <SectionTitle eyebrow="In flight">Pipeline</SectionTitle>
        {features.csvExport && filtered.length > 0 && (
          <Button variant="ghost" size="sm" onClick={exportCsv}><Download size={14} /> Export CSV</Button>
        )}
      </div>

      <Card className="p-3 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <Input placeholder="Search title or submitter…" value={search} onChange={e => setSearch(e.target.value)} />
          <Select value={stageFilter} onChange={e => setStageFilter(e.target.value)}>
            <option value="all">All stages</option>
            {stages.map(s => <option key={s} value={s}>{STAGE_LABELS[s] || s}</option>)}
          </Select>
          <Select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
            <option value="all">All types</option>
            <option value="schedule">Schedules</option>
            <option value="change">Change Requests</option>
          </Select>
          <div className="flex items-center justify-end text-xs text-[#5A5A5A]">
            {filtered.length} of {items.length} {items.length === 1 ? 'item' : 'items'}
          </div>
        </div>
      </Card>

      {filtered.length === 0 ? (
        <Card className="p-12 text-center">
          <Inbox className="mx-auto mb-3 text-[#C4B999]" size={32} />
          <div className="font-display text-xl text-[#1A1A1A] mb-1">{items.length === 0 ? 'No submissions yet' : 'Nothing matches those filters'}</div>
          <div className="text-sm text-[#5A5A5A]">{items.length === 0 ? 'Use the Submit tab to add your first item.' : 'Try clearing the filters above.'}</div>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map(item => {
            const wf = workflows.find(w => w.id === item.workflowId);
            const reviewer = reviewers.find(r => r.id === item.assignedReviewer);
            return (
              <button key={item.id} onClick={() => openDetail(item.id)} className="w-full text-left">
                <Card className="p-4 hover:border-[#A0432C] transition-all group">
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Pill tone={item.type === 'schedule' ? 'moss' : 'rust'}>{item.type}</Pill>
                        <Pill tone="neutral">{item.typeName}</Pill>
                        {item.currentStage === 'approved' && <Pill tone="moss"><Check size={10} /> Approved</Pill>}
                        {item.currentStage === 'returned' && <Pill tone="warn">Returned</Pill>}
                      </div>
                      <div className="font-display text-lg text-[#1A1A1A] leading-tight truncate mb-1">{item.title}</div>
                      <div className="text-xs text-[#5A5A5A]">
                        {item.submittedBy} · {new Date(item.createdAt).toLocaleDateString()} {reviewer && <>· Reviewer: {reviewer.name}</>}
                      </div>
                    </div>
                    <div className="shrink-0 w-72">
                      <StageTrack workflow={wf} current={item.currentStage} compact />
                    </div>
                    {features.riskScoring && (
                      <div className="shrink-0 text-right">
                        <div className="text-[10px] uppercase tracking-wider text-[#8A8A8A]">Risk</div>
                        <div className="font-display text-xl text-[#1A1A1A]">{item.riskScore ?? '—'}</div>
                      </div>
                    )}
                    <ArrowUpRight size={16} className="text-[#C4B999] group-hover:text-[#A0432C] transition-colors mt-1" />
                  </div>
                </Card>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StageTrack({ workflow, current, compact }) {
  if (!workflow) return null;
  const allStages = [...workflow.stages, current === 'returned' ? 'returned' : 'approved'];
  const currentIdx = allStages.indexOf(current);
  return (
    <div className="flex items-center gap-1">
      {allStages.map((s, idx) => {
        const isDone = idx < currentIdx || (current === 'approved' && idx <= currentIdx);
        const isCurrent = idx === currentIdx;
        const isReturned = s === 'returned' && current === 'returned';
        return (
          <React.Fragment key={s + idx}>
            <div className={`flex flex-col items-center ${compact ? '' : 'min-w-[80px]'}`}>
              <div className={`w-3 h-3 rounded-full flex items-center justify-center border-2 ${
                isReturned ? 'bg-[#C58A30] border-[#C58A30]' :
                isDone ? 'bg-[#6B7A4F] border-[#6B7A4F]' :
                isCurrent ? 'bg-[#A0432C] border-[#A0432C]' :
                'bg-[#FDFBF6] border-[#D4CCB9]'
              }`}>
                {isDone && <Check size={8} className="text-[#FAF7F2]" />}
              </div>
              {!compact && <div className={`text-[10px] mt-1.5 text-center leading-tight ${isCurrent ? 'text-[#A0432C] font-semibold' : 'text-[#5A5A5A]'}`}>{STAGE_LABELS[s]}</div>}
            </div>
            {idx < allStages.length - 1 && (
              <div className={`flex-1 h-px ${idx < currentIdx ? 'bg-[#6B7A4F]' : 'bg-[#D4CCB9]'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function ItemDetail({ item, workflows, reviewers, features, onUpdate, onClose }) {
  const [note, setNote] = useState('');
  const wf = workflows.find(w => w.id === item.workflowId);
  const reviewer = reviewers.find(r => r.id === item.assignedReviewer);

  if (!wf) return null;
  const stages = wf.stages;
  const curIdx = stages.indexOf(item.currentStage);
  const nextStage = item.currentStage === 'approved' || item.currentStage === 'returned' ? null
    : curIdx === stages.length - 1 ? 'approved' : stages[curIdx + 1];

  const advance = () => {
    if (!nextStage) return;
    const event = { at: Date.now(), action: `Advanced to ${STAGE_LABELS[nextStage]}`, note: note.trim() };
    onUpdate({ ...item, currentStage: nextStage, history: [...(item.history || []), event] });
    setNote('');
  };
  const returnItem = () => {
    const event = { at: Date.now(), action: 'Returned to submitter', note: note.trim() || 'Returned for revision.' };
    onUpdate({ ...item, currentStage: 'returned', history: [...(item.history || []), event] });
    setNote('');
  };
  const reopen = () => {
    const event = { at: Date.now(), action: `Reopened to ${STAGE_LABELS[stages[0]]}`, note: note.trim() };
    onUpdate({ ...item, currentStage: stages[0], history: [...(item.history || []), event] });
    setNote('');
  };

  return (
    <div className="fixed inset-0 bg-[#1A1A1A]/40 z-40 flex justify-end" onClick={onClose}>
      <div className="bg-[#FAF7F2] w-full max-w-2xl h-full overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-[#FAF7F2] border-b border-[#E5DDC9] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Pill tone={item.type === 'schedule' ? 'moss' : 'rust'}>{item.type}</Pill>
            <span className="text-xs text-[#8A8A8A]">{item.id}</span>
          </div>
          <button onClick={onClose} className="text-[#5A5A5A] hover:text-[#1A1A1A]"><X size={20} /></button>
        </div>

        <div className="p-6">
          <h2 className="font-display text-3xl text-[#1A1A1A] leading-tight mb-1">{item.title}</h2>
          <div className="text-sm text-[#5A5A5A] mb-6">
            {item.typeName} · Submitted by {item.submittedBy} · {new Date(item.createdAt).toLocaleString()}
          </div>

          <Card className="p-5 mb-5">
            <Label>Workflow progress</Label>
            <StageTrack workflow={wf} current={item.currentStage} />
          </Card>

          {features.riskScoring && (
            <Card className="p-5 mb-5">
              <Label>Risk profile</Label>
              <RiskBar score={item.riskScore || 0} />
            </Card>
          )}

          {item.notes && (
            <Card className="p-5 mb-5">
              <Label>Submitter notes</Label>
              <div className="text-sm text-[#3A3A3A] whitespace-pre-wrap">{item.notes}</div>
            </Card>
          )}

          {reviewer && (
            <Card className="p-5 mb-5">
              <Label>Assigned reviewer</Label>
              <div className="text-sm text-[#1A1A1A]"><strong>{reviewer.name}</strong> · {reviewer.role}</div>
            </Card>
          )}

          <Card className="p-5 mb-5">
            <Label>Selected criteria</Label>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(item.answers || {}).map(([k, v]) => (
                <Pill key={k} tone="neutral">{k}: {v}</Pill>
              ))}
            </div>
          </Card>

          <Card className="p-5 mb-5">
            <Label>Take action</Label>
            <Textarea value={note} onChange={e => setNote(e.target.value)} rows={2} placeholder="Add a note (optional)…" className="mb-3" />
            <div className="flex flex-wrap gap-2">
              {nextStage && <Button size="sm" onClick={advance}><Check size={14} /> Advance to {STAGE_LABELS[nextStage]}</Button>}
              {item.currentStage !== 'returned' && item.currentStage !== 'approved' && (
                <Button size="sm" variant="danger" onClick={returnItem}>Return to submitter</Button>
              )}
              {(item.currentStage === 'approved' || item.currentStage === 'returned') && (
                <Button size="sm" variant="ghost" onClick={reopen}>Reopen</Button>
              )}
            </div>
          </Card>

          <Card className="p-5">
            <Label>Activity</Label>
            <div className="space-y-3">
              <div className="text-xs text-[#5A5A5A]">
                <strong className="text-[#1A1A1A]">Created</strong> · {new Date(item.createdAt).toLocaleString()}
              </div>
              {(item.history || []).map((h, i) => (
                <div key={i} className="text-xs text-[#5A5A5A] pl-3 border-l-2 border-[#E5DDC9]">
                  <strong className="text-[#1A1A1A]">{h.action}</strong> · {new Date(h.at).toLocaleString()}
                  {h.note && <div className="text-[#3A3A3A] mt-0.5">{h.note}</div>}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* =========================================================================
   DOCUMENT ANALYSIS via Anthropic API
   ========================================================================= */

function DocumentsView({ features }) {
  const [analysisType, setAnalysisType] = useState('schedule');
  const [text, setText] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfBase64, setPdfBase64] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [customCriteria, setCustomCriteria] = useState('');

  if (!features.documentAnalysis) {
    return (
      <div>
        <SectionTitle eyebrow="Document analysis">Disabled</SectionTitle>
        <Card className="p-8 text-center">
          <BookOpen className="mx-auto mb-3 text-[#C4B999]" size={32} />
          <p className="text-sm text-[#5A5A5A]">Enable Document Analysis in Settings to use this tab.</p>
        </Card>
      </div>
    );
  }

  const handlePdf = async (file) => {
    if (!file) return;
    setPdfFile(file);
    const reader = new FileReader();
    reader.onload = () => setPdfBase64(reader.result.split(',')[1]);
    reader.onerror = () => setError('Failed to read PDF');
    reader.readAsDataURL(file);
  };

  const prompts = {
    schedule: `You are reviewing a project schedule document for a PMO. Evaluate it across these dimensions and produce a structured review:

1. Completeness — are key sections present (scope, milestones, dependencies, resources, assumptions, risks)?
2. Realism — are durations, resource loads, and dependencies plausible?
3. Risk flags — any single points of failure, unstated assumptions, or unresolved dependencies?
4. Template fit — based on the structure shown, what kind of schedule template was used and does it fit the apparent work?
5. Quality issues to surface to the team lead before final QA

Return your analysis as: TOP-LINE VERDICT (1-2 sentences), then STRENGTHS, ISSUES (ordered by severity), and RECOMMENDED NEXT ACTIONS. Be specific. Cite what you see.`,
    change: `You are reviewing a change request document for a PMO. Evaluate it as a change manager would, covering:

1. Classification check — does this look like a Standard, Normal, Major, or Emergency change? Is the classification appropriate?
2. Risk and impact assessment — completeness, identified blast radius, mitigation
3. Rollback plan — present, credible, tested?
4. Approval chain — does the requested approval level match the assessed risk?
5. Testing and validation evidence

Return your analysis as: TOP-LINE VERDICT (1-2 sentences), then STRENGTHS, ISSUES (ordered by severity), and RECOMMENDED NEXT ACTIONS. Be specific. Cite what you see.`,
    custom: customCriteria,
  };

  const analyze = async () => {
    setError(null); setResult(null); setLoading(true);
    try {
      const content = [];
      if (pdfBase64) {
        content.push({ type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: pdfBase64 } });
      } else if (text.trim()) {
        content.push({ type: 'text', text: `Document content:\n\n${text}` });
      } else {
        throw new Error('Provide a document — paste text or upload a PDF.');
      }
      content.push({ type: 'text', text: prompts[analysisType] || 'Review this document.' });

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1500,
          messages: [{ role: 'user', content }],
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || 'Analysis failed');
      const reply = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n').trim();
      setResult(reply);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <SectionTitle eyebrow="Pre-screen">Document Analysis</SectionTitle>
      <p className="text-sm text-[#5A5A5A] mb-6 max-w-2xl">Drop a schedule, change request, or any document below. Claude will pre-screen it against the relevant criteria so your team leads see a focused review rather than a blank page.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <Label>Analysis lens</Label>
          <Select value={analysisType} onChange={e => setAnalysisType(e.target.value)} className="mb-4">
            <option value="schedule">Schedule template review</option>
            <option value="change">Change request review</option>
            <option value="custom">Custom criteria</option>
          </Select>

          {analysisType === 'custom' && (
            <div className="mb-4">
              <Label>Your criteria</Label>
              <Textarea value={customCriteria} onChange={e => setCustomCriteria(e.target.value)} rows={4} placeholder="Tell Claude what to look for..." />
            </div>
          )}

          <Label>Upload PDF</Label>
          <div className="mb-4">
            <input type="file" accept="application/pdf" onChange={e => handlePdf(e.target.files?.[0])} className="text-xs text-[#5A5A5A] file:mr-3 file:px-3 file:py-1.5 file:border-0 file:bg-[#1A1A1A] file:text-[#FAF7F2] file:rounded-sm file:text-xs file:cursor-pointer" />
            {pdfFile && <div className="text-xs text-[#5A5A5A] mt-1.5">📄 {pdfFile.name}</div>}
          </div>

          <Label>Or paste text</Label>
          <Textarea value={text} onChange={e => setText(e.target.value)} rows={8} placeholder="Paste document content here..." />

          <div className="mt-4 flex items-center gap-3">
            <Button onClick={analyze} disabled={loading || (!text.trim() && !pdfBase64) || (analysisType === 'custom' && !customCriteria.trim())}>
              {loading ? <><Loader2 size={14} className="animate-spin" /> Analysing…</> : <><Sparkles size={14} /> Run analysis</>}
            </Button>
            {(text || pdfFile) && <Button variant="ghost" size="sm" onClick={() => { setText(''); setPdfFile(null); setPdfBase64(null); setResult(null); setError(null); }}>Clear</Button>}
          </div>
        </Card>

        <Card className="p-5 min-h-[400px]">
          <Label>Result</Label>
          {error && <div className="text-sm text-[#A0432C] flex items-start gap-2"><AlertTriangle size={14} className="mt-0.5 shrink-0" /><span>{error}</span></div>}
          {!error && !result && !loading && (
            <div className="text-sm text-[#8A8A8A] italic">Analysis output will appear here.</div>
          )}
          {loading && (
            <div className="text-sm text-[#5A5A5A] flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Reading the document…</div>
          )}
          {result && (
            <div className="text-sm text-[#1A1A1A] whitespace-pre-wrap leading-relaxed">{result}</div>
          )}
        </Card>
      </div>
    </div>
  );
}

/* =========================================================================
   SETTINGS — feature toggles + editable templates / change types / reviewers
   ========================================================================= */

function SettingsView({ features, setFeatures, templates, setTemplates, changeTypes, setChangeTypes, reviewers, setReviewers, onReset }) {
  const [editing, setEditing] = useState(null);

  const toggleFeature = (k) => setFeatures({ ...features, [k]: !features[k] });

  const FEATURE_META = [
    { key: 'documentAnalysis', name: 'Document Analysis', desc: 'AI pre-screens uploaded documents against your criteria.' },
    { key: 'riskScoring', name: 'Risk Scoring', desc: 'Auto-computes 0–10 risk score from wizard answers.' },
    { key: 'autoAssignment', name: 'Reviewer Auto-Assignment', desc: 'Picks the best-fit reviewer based on expertise and current load.' },
    { key: 'csvExport', name: 'CSV Export', desc: 'Export filtered pipeline as CSV.' },
    { key: 'workExport', name: 'Work Export (JSON)', desc: 'Export complete data set for backup or handover.' },
    { key: 'slaTracking', name: 'SLA Tracking (coming soon)', desc: 'Flags items breaching their SLA. Wire up when ready.', preview: true },
    { key: 'emailNotifications', name: 'Email Notifications (coming soon)', desc: 'Email reviewers on assignment. Needs backend integration.', preview: true },
  ];

  return (
    <div>
      <SectionTitle eyebrow="Configure">Settings</SectionTitle>

      <Card className="p-5 mb-5">
        <Label>Features</Label>
        <div className="space-y-2">
          {FEATURE_META.map(f => (
            <div key={f.key} className="flex items-start justify-between gap-4 py-2 border-b border-[#E5DDC9] last:border-0">
              <div className="flex-1">
                <div className="text-sm text-[#1A1A1A] font-medium">{f.name}</div>
                <div className="text-xs text-[#5A5A5A] mt-0.5">{f.desc}</div>
              </div>
              <button
                onClick={() => !f.preview && toggleFeature(f.key)}
                disabled={f.preview}
                className={`relative w-10 h-5 rounded-full transition-all shrink-0 ${
                  features[f.key] ? 'bg-[#A0432C]' : 'bg-[#D4CCB9]'
                } ${f.preview ? 'opacity-50' : 'cursor-pointer'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-[#FAF7F2] rounded-full transition-all ${features[f.key] ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
          ))}
        </div>
      </Card>

      <EditableList
        title="Schedule templates"
        items={templates}
        setItems={setTemplates}
        kind="template"
        onEdit={setEditing}
      />

      <EditableList
        title="Change request types"
        items={changeTypes}
        setItems={setChangeTypes}
        kind="changeType"
        onEdit={setEditing}
      />

      <EditableList
        title="Team leads / reviewers"
        items={reviewers}
        setItems={setReviewers}
        kind="reviewer"
        onEdit={setEditing}
      />

      <Card className="p-5 mb-5 border-[#A0432C]/30">
        <Label>Reset</Label>
        <div className="text-xs text-[#5A5A5A] mb-3">Wipe all submissions and restore defaults. Cannot be undone.</div>
        <Button variant="danger" size="sm" onClick={() => { if (confirm('Wipe all data and reset to defaults?')) onReset(); }}>
          <Trash2 size={14} /> Reset all data
        </Button>
      </Card>

      {editing && (
        <ItemEditorModal
          item={editing.item}
          kind={editing.kind}
          onSave={(updated) => {
            if (editing.kind === 'template') setTemplates(prev => updated.id ? prev.map(p => p.id === updated.id ? updated : p) : [...prev, { ...updated, id: `tpl_${Date.now()}` }]);
            if (editing.kind === 'changeType') setChangeTypes(prev => updated.id ? prev.map(p => p.id === updated.id ? updated : p) : [...prev, { ...updated, id: `ch_${Date.now()}` }]);
            if (editing.kind === 'reviewer') setReviewers(prev => updated.id ? prev.map(p => p.id === updated.id ? updated : p) : [...prev, { ...updated, id: `r_${Date.now()}` }]);
            setEditing(null);
          }}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function EditableList({ title, items, setItems, kind, onEdit }) {
  return (
    <Card className="p-5 mb-5">
      <div className="flex items-center justify-between mb-3">
        <Label>{title}</Label>
        <Button variant="ghost" size="sm" onClick={() => onEdit({ item: null, kind })}><Plus size={12} /> Add</Button>
      </div>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.id} className="flex items-center justify-between p-3 bg-[#FAF7F2] border border-[#E5DDC9] rounded-sm">
            <div className="flex-1 min-w-0">
              <div className="text-sm text-[#1A1A1A] font-medium truncate">{item.name}</div>
              <div className="text-xs text-[#5A5A5A] truncate">
                {kind === 'reviewer' ? `${item.role || ''} · ${(item.expertise || []).join(', ')}` : item.description}
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button onClick={() => onEdit({ item, kind })} className="p-1.5 text-[#5A5A5A] hover:text-[#A0432C]"><Edit3 size={14} /></button>
              <button onClick={() => { if (confirm(`Remove "${item.name}"?`)) setItems(prev => prev.filter(p => p.id !== item.id)); }} className="p-1.5 text-[#5A5A5A] hover:text-[#A0432C]"><Trash2 size={14} /></button>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="text-xs text-[#8A8A8A] italic py-3 text-center">None yet — add one above.</div>}
      </div>
    </Card>
  );
}

function ItemEditorModal({ item, kind, onSave, onClose }) {
  const isReviewer = kind === 'reviewer';
  const [draft, setDraft] = useState(item || (isReviewer
    ? { name: '', role: 'Team Lead', expertise: [], capacity: 4 }
    : { name: '', description: '', tags: [], defaultWorkflow: 'standard', checkpoints: [], requiredApprovals: [], sla: '', conditions: [], riskBase: 2 }
  ));

  const update = (k, v) => setDraft({ ...draft, [k]: v });
  const csvField = (k) => (Array.isArray(draft[k]) ? draft[k].join(', ') : '');
  const setCsv = (k, v) => update(k, v.split(',').map(s => s.trim()).filter(Boolean));

  return (
    <div className="fixed inset-0 bg-[#1A1A1A]/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="w-full max-w-xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-[#FDFBF6] border-b border-[#E5DDC9] px-5 py-3 flex items-center justify-between">
          <div className="font-display text-xl text-[#1A1A1A]">{item ? 'Edit' : 'Add'} {kind === 'template' ? 'template' : kind === 'changeType' ? 'change type' : 'reviewer'}</div>
          <button onClick={onClose}><X size={18} /></button>
        </div>
        <div className="p-5 space-y-3">
          <div><Label>Name</Label><Input value={draft.name || ''} onChange={e => update('name', e.target.value)} /></div>
          {!isReviewer && <div><Label>Description</Label><Textarea value={draft.description || ''} onChange={e => update('description', e.target.value)} rows={3} /></div>}
          {isReviewer && (
            <>
              <div><Label>Role</Label><Input value={draft.role || ''} onChange={e => update('role', e.target.value)} /></div>
              <div><Label>Expertise tags (comma-separated)</Label><Input value={csvField('expertise')} onChange={e => setCsv('expertise', e.target.value)} placeholder="software, regulated, large-team" /></div>
              <div><Label>Capacity (max concurrent items)</Label><Input type="number" value={draft.capacity || 4} onChange={e => update('capacity', parseInt(e.target.value) || 1)} /></div>
            </>
          )}
          {kind === 'template' && (
            <>
              <div><Label>Tags (comma-separated — match wizard answers)</Label><Input value={csvField('tags')} onChange={e => setCsv('tags', e.target.value)} placeholder="software, medium-duration, iterative" /></div>
              <div><Label>Checkpoints (comma-separated)</Label><Input value={csvField('checkpoints')} onChange={e => setCsv('checkpoints', e.target.value)} placeholder="Kickoff, Midpoint, Closeout" /></div>
              <div><Label>Default workflow</Label>
                <Select value={draft.defaultWorkflow || 'standard'} onChange={e => update('defaultWorkflow', e.target.value)}>
                  {DEFAULT_WORKFLOWS.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </Select>
              </div>
              <div><Label>Risk base (0–5)</Label><Input type="number" min="0" max="5" value={draft.riskBase ?? 2} onChange={e => update('riskBase', parseInt(e.target.value) || 0)} /></div>
            </>
          )}
          {kind === 'changeType' && (
            <>
              <div><Label>Conditions (comma-separated — match wizard answers)</Label><Input value={csvField('conditions')} onChange={e => setCsv('conditions', e.target.value)} placeholder="routine, low, team" /></div>
              <div><Label>Required approvals (comma-separated)</Label><Input value={csvField('requiredApprovals')} onChange={e => setCsv('requiredApprovals', e.target.value)} /></div>
              <div><Label>SLA</Label><Input value={draft.sla || ''} onChange={e => update('sla', e.target.value)} placeholder="5 business days" /></div>
              <div><Label>Default workflow</Label>
                <Select value={draft.defaultWorkflow || 'standard'} onChange={e => update('defaultWorkflow', e.target.value)}>
                  {DEFAULT_WORKFLOWS.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </Select>
              </div>
              <div><Label>Risk base (0–5)</Label><Input type="number" min="0" max="5" value={draft.riskBase ?? 2} onChange={e => update('riskBase', parseInt(e.target.value) || 0)} /></div>
            </>
          )}
        </div>
        <div className="sticky bottom-0 bg-[#FDFBF6] border-t border-[#E5DDC9] px-5 py-3 flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={() => draft.name?.trim() && onSave(draft)}>Save</Button>
        </div>
      </Card>
    </div>
  );
}

/* =========================================================================
   HOME / DASHBOARD
   ========================================================================= */

function HomeView({ items, reviewers, workflows, features, goTo, exportWork }) {
  const counts = useMemo(() => {
    const out = { total: items.length, schedule: 0, change: 0, byStage: {}, mine: 0, approved: 0 };
    items.forEach(i => {
      out[i.type]++;
      out.byStage[i.currentStage] = (out.byStage[i.currentStage] || 0) + 1;
      if (i.currentStage === 'final_qa') out.mine++;
      if (i.currentStage === 'approved') out.approved++;
    });
    return out;
  }, [items]);

  return (
    <div>
      <div className="mb-8">
        <div className="text-[10px] uppercase tracking-[0.2em] text-[#A0432C] mb-1.5">Today at the bench</div>
        <h1 className="font-display text-4xl text-[#1A1A1A] leading-tight">Hand the routine work to the structure.</h1>
        <p className="text-sm text-[#5A5A5A] mt-2 max-w-2xl">Wizards guide your teams to the right template or change type. Reviewers see clean, scored submissions. You see only what reaches Final QA.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatCard label="In pipeline" value={counts.total - counts.approved} />
        <StatCard label="Awaiting your QA" value={counts.mine} accent />
        <StatCard label="Schedules" value={counts.schedule} />
        <StatCard label="Change requests" value={counts.change} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        <button onClick={() => goTo('submit')} className="text-left">
          <Card className="p-5 hover:border-[#A0432C] transition-all group h-full">
            <GitBranch className="text-[#A0432C] mb-3" size={20} />
            <div className="font-display text-xl text-[#1A1A1A] mb-1">Submit something new</div>
            <div className="text-sm text-[#5A5A5A]">Run a team member through the schedule or change request wizard.</div>
            <div className="mt-3 text-xs text-[#A0432C] flex items-center gap-1">Open submit <ArrowRight size={12} /></div>
          </Card>
        </button>
        <button onClick={() => goTo('pipeline')} className="text-left">
          <Card className="p-5 hover:border-[#A0432C] transition-all group h-full">
            <Activity className="text-[#A0432C] mb-3" size={20} />
            <div className="font-display text-xl text-[#1A1A1A] mb-1">Check the pipeline</div>
            <div className="text-sm text-[#5A5A5A]">See where every item is, who's reviewing, and what's blocked.</div>
            <div className="mt-3 text-xs text-[#A0432C] flex items-center gap-1">Open pipeline <ArrowRight size={12} /></div>
          </Card>
        </button>
      </div>

      <Card className="p-5 mb-3">
        <div className="flex items-center justify-between mb-3">
          <Label>Reviewer load</Label>
          {features.workExport && <Button variant="ghost" size="sm" onClick={exportWork}><Download size={12} /> Export workspace</Button>}
        </div>
        <div className="space-y-2">
          {reviewers.map(r => {
            const load = items.filter(i => i.assignedReviewer === r.id && i.currentStage !== 'approved' && i.currentStage !== 'returned').length;
            const pct = Math.min(100, (load / (r.capacity || 1)) * 100);
            return (
              <div key={r.id} className="flex items-center gap-3">
                <div className="w-40 text-sm text-[#1A1A1A] truncate">{r.name}</div>
                <div className="flex-1 h-1 bg-[#E5DDC9] rounded-full overflow-hidden">
                  <div className="h-full bg-[#A0432C]" style={{ width: `${pct}%` }} />
                </div>
                <div className="text-xs text-[#5A5A5A] w-16 text-right">{load} / {r.capacity}</div>
              </div>
            );
          })}
          {reviewers.length === 0 && <div className="text-xs text-[#8A8A8A] italic">Add reviewers in Settings.</div>}
        </div>
      </Card>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <Card className={`p-4 ${accent ? 'border-[#A0432C] bg-[#F2E5DE]' : ''}`}>
      <div className="text-[10px] uppercase tracking-wider text-[#5A5A5A] mb-1">{label}</div>
      <div className="font-display text-4xl text-[#1A1A1A] leading-none">{value}</div>
    </Card>
  );
}

/* =========================================================================
   SUBMIT VIEW — selects which wizard to run
   ========================================================================= */

function SubmitView({ templates, changeTypes, reviewers, items, features, onSubmit }) {
  const [kind, setKind] = useState(null);

  if (!kind) {
    return (
      <div>
        <SectionTitle eyebrow="New submission">What are you submitting?</SectionTitle>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          <button onClick={() => setKind('schedule')} className="text-left">
            <Card className="p-6 hover:border-[#A0432C] transition-all h-full">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#A0432C] mb-2">Scheduling team</div>
              <div className="font-display text-2xl text-[#1A1A1A] mb-2 leading-tight">Schedule template</div>
              <div className="text-sm text-[#5A5A5A]">Walk through 6 checkpoints to pick the right schedule template for your project.</div>
            </Card>
          </button>
          <button onClick={() => setKind('change')} className="text-left">
            <Card className="p-6 hover:border-[#A0432C] transition-all h-full">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#A0432C] mb-2">Change management team</div>
              <div className="font-display text-2xl text-[#1A1A1A] mb-2 leading-tight">Change request</div>
              <div className="text-sm text-[#5A5A5A]">Classify a change correctly before submitting — Standard, Normal, Major, or Emergency.</div>
            </Card>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button onClick={() => setKind(null)} className="text-xs text-[#5A5A5A] hover:text-[#A0432C] mb-4 flex items-center gap-1">
        <ChevronLeft size={12} /> Pick a different wizard
      </button>
      <SectionTitle eyebrow={kind === 'schedule' ? 'Scheduling' : 'Change management'}>
        {kind === 'schedule' ? 'Schedule Template Wizard' : 'Change Request Wizard'}
      </SectionTitle>
      <Wizard
        kind={kind}
        questions={kind === 'schedule' ? SCHEDULE_QUESTIONS : CHANGE_QUESTIONS}
        options={kind === 'schedule' ? templates : changeTypes}
        reviewers={reviewers}
        items={items}
        features={features}
        onSubmit={(payload) => { onSubmit(payload); setKind(null); }}
        onCancel={() => setKind(null)}
      />
    </div>
  );
}

/* =========================================================================
   MAIN APP
   ========================================================================= */

export default function App() {
  const [tab, setTab] = useState('home');
  const [detailId, setDetailId] = useState(null);

  const [features, setFeatures, fl] = usePersistent('pmo:features', DEFAULT_FEATURES);
  const [templates, setTemplates, tl] = usePersistent('pmo:templates', DEFAULT_TEMPLATES);
  const [changeTypes, setChangeTypes, cl] = usePersistent('pmo:changeTypes', DEFAULT_CHANGE_TYPES);
  const [reviewers, setReviewers, rl] = usePersistent('pmo:reviewers', DEFAULT_REVIEWERS);
  const [workflows, setWorkflows, wl] = usePersistent('pmo:workflows', DEFAULT_WORKFLOWS);
  const [items, setItems, il] = usePersistent('pmo:items', []);

  const loaded = fl && tl && cl && rl && wl && il;

  const handleSubmit = useCallback((payload) => {
    const wf = workflows.find(w => w.id === payload.workflowId) || workflows[0];
    const item = {
      ...payload,
      id: `item_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      currentStage: wf.stages[0],
      history: [],
      createdAt: Date.now(),
    };
    setItems(prev => [item, ...prev]);
    setTab('pipeline');
  }, [workflows, setItems]);

  const handleUpdate = useCallback((updated) => {
    setItems(prev => prev.map(i => i.id === updated.id ? updated : i));
  }, [setItems]);

  const handleReset = useCallback(() => {
    setFeatures(DEFAULT_FEATURES);
    setTemplates(DEFAULT_TEMPLATES);
    setChangeTypes(DEFAULT_CHANGE_TYPES);
    setReviewers(DEFAULT_REVIEWERS);
    setWorkflows(DEFAULT_WORKFLOWS);
    setItems([]);
  }, [setFeatures, setTemplates, setChangeTypes, setReviewers, setWorkflows, setItems]);

  const exportWork = useCallback(() => {
    const payload = { exportedAt: new Date().toISOString(), features, templates, changeTypes, reviewers, workflows, items };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `pmo-compass-workspace-${Date.now()}.json`; a.click();
    URL.revokeObjectURL(url);
  }, [features, templates, changeTypes, reviewers, workflows, items]);

  const TABS = [
    { id: 'home', label: 'Home', icon: Compass },
    { id: 'submit', label: 'Submit', icon: Plus },
    { id: 'pipeline', label: 'Pipeline', icon: Activity },
    ...(features.documentAnalysis ? [{ id: 'documents', label: 'Documents', icon: FileText }] : []),
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  const detailItem = detailId ? items.find(i => i.id === detailId) : null;

  return (
    <div className="font-body min-h-screen bg-[#FAF7F2] text-[#1A1A1A]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Manrope:wght@400;500;600;700&display=swap');
        .font-display { font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; }
        .font-body { font-family: 'Manrope', system-ui, sans-serif; }
      `}</style>

      <header className="border-b border-[#E5DDC9] bg-[#FAF7F2] sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-[#1A1A1A] flex items-center justify-center rounded-sm">
              <Compass size={14} className="text-[#FAF7F2]" />
            </div>
            <div>
              <div className="font-display text-xl text-[#1A1A1A] leading-none">PMO Compass</div>
              <div className="text-[9px] uppercase tracking-[0.2em] text-[#8A8A8A] mt-0.5">Decision support · Routing · QA</div>
            </div>
          </div>
          <nav className="flex items-center gap-0">
            {TABS.map(t => {
              const Icon = t.icon;
              const active = tab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-2 text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors border-b-2 ${
                    active ? 'border-[#A0432C] text-[#1A1A1A]' : 'border-transparent text-[#5A5A5A] hover:text-[#1A1A1A]'
                  }`}
                >
                  <Icon size={12} /> {t.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {!loaded ? (
          <div className="text-sm text-[#5A5A5A] flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Loading workspace…</div>
        ) : (
          <>
            {tab === 'home' && <HomeView items={items} reviewers={reviewers} workflows={workflows} features={features} goTo={setTab} exportWork={exportWork} />}
            {tab === 'submit' && <SubmitView templates={templates} changeTypes={changeTypes} reviewers={reviewers} items={items} features={features} onSubmit={handleSubmit} />}
            {tab === 'pipeline' && <PipelineView items={items} setItems={setItems} workflows={workflows} reviewers={reviewers} features={features} openDetail={setDetailId} />}
            {tab === 'documents' && features.documentAnalysis && <DocumentsView features={features} />}
            {tab === 'settings' && <SettingsView features={features} setFeatures={setFeatures} templates={templates} setTemplates={setTemplates} changeTypes={changeTypes} setChangeTypes={setChangeTypes} reviewers={reviewers} setReviewers={setReviewers} onReset={handleReset} />}
          </>
        )}
      </main>

      {detailItem && (
        <ItemDetail
          item={detailItem}
          workflows={workflows}
          reviewers={reviewers}
          features={features}
          onUpdate={handleUpdate}
          onClose={() => setDetailId(null)}
        />
      )}

      <footer className="max-w-6xl mx-auto px-6 py-6 text-center text-[10px] uppercase tracking-[0.2em] text-[#A89E85] border-t border-[#E5DDC9] mt-12">
        PMO Compass · v1 · Data persists locally
      </footer>
    </div>
  );
}
