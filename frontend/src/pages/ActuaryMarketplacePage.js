import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Store, Star, MapPin, Clock, DollarSign, Award, Search,
  Send, FileCheck, CheckCircle2, XCircle, ArrowLeft, Loader2,
  MessageSquare, CreditCard, AlertTriangle, RotateCcw,
  FileText, ClipboardList, Shield,
  Upload, Download, Trash2, Paperclip, ArrowRight, ChevronRight
} from 'lucide-react';

/* ── Design Tokens (shared with Employee Portal) ── */
const C = {
  bg: '#F9F9F8', surface: '#FFFFFF',
  primary: '#1C3B35', primaryH: '#162F2A',
  secondary: '#E3EBE6', secFg: '#1C3B35',
  text: '#111827', muted: '#4B5563', light: '#9CA3AF',
  border: '#E5E7EB',
  successBg: '#E8F0EB', successTx: '#1F4D36',
  warnBg: '#FEF3C7', warnTx: '#92400E',
  dangerBg: '#FEE2E2', dangerTx: '#991B1B',
  blueBg: '#DBEAFE', blueTx: '#1E40AF',
  indigoBg: '#E0E7FF', indigoTx: '#3730A3',
  amberBg: '#FEF3C7', amberTx: '#92400E',
  tealBg: '#CCFBF1', tealTx: '#115E59',
};

const STATUS_CONFIG = {
  pending:          { label: 'Pending Review',       bg: C.warnBg,    tx: C.warnTx,    icon: Clock },
  accepted:         { label: 'Accepted',             bg: C.blueBg,    tx: C.blueTx,    icon: CheckCircle2 },
  rejected:         { label: 'Rejected',             bg: C.dangerBg,  tx: C.dangerTx,  icon: XCircle },
  paid:             { label: 'Paid — In Progress',   bg: C.indigoBg,  tx: C.indigoTx,  icon: CreditCard },
  delivered:        { label: 'Delivered',             bg: C.tealBg,    tx: C.tealTx,    icon: FileCheck },
  validated:        { label: 'Validated',             bg: C.successBg, tx: C.successTx, icon: CheckCircle2 },
  resubmit_needed:  { label: 'Revision Requested',   bg: '#FFF7ED',   tx: '#C2410C',   icon: RotateCcw },
};

function QuoteStatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider"
      style={{ background: cfg.bg, color: cfg.tx }} data-testid={`status-badge-${status}`}>
      <Icon className="w-3 h-3" /> {cfg.label}
    </span>
  );
}

export default function ActuaryMarketplacePage() {
  const { user, token, API, selectedEmployer } = useAuth();
  const [actuaries, setActuaries] = useState([]);
  const [plans, setPlans] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('rating');
  const [tab, setTab] = useState(user?.role === 'actuary' ? 'quotes' : 'directory');
  const [showQuoteDialog, setShowQuoteDialog] = useState(false);
  const [selectedActuary, setSelectedActuary] = useState(null);
  const [quoteForm, setQuoteForm] = useState({ plan_id: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [activeReview, setActiveReview] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const preselectedPlanId = searchParams.get('plan_id');
  const preselectedQuoteId = searchParams.get('quote_id');
  const headers = { Authorization: `Bearer ${token}` };

  const loadActuaries = useCallback(async () => { try { const r = await axios.get(`${API}/actuary-marketplace`, { headers }); setActuaries(r.data); } catch {} }, [API, token]);
  const loadPlans = useCallback(async () => { if (!selectedEmployer?.id) return; try { const r = await axios.get(`${API}/enrollment/plans/${selectedEmployer.id}`, { headers }); setPlans(r.data); } catch {} }, [API, token, selectedEmployer?.id]);
  const loadQuotes = useCallback(async () => { try { const r = await axios.get(`${API}/marketplace/quotes`, { headers }); setQuotes(r.data); } catch {} }, [API, token]);

  useEffect(() => { loadActuaries(); loadQuotes(); }, [loadActuaries, loadQuotes]);
  useEffect(() => { loadPlans(); }, [loadPlans]);
  useEffect(() => {
    if (preselectedQuoteId && quotes.length > 0 && !activeReview) { const q = quotes.find(q => q.id === preselectedQuoteId); if (q) openReview(q); }
  }, [preselectedQuoteId, quotes]);

  const openReview = async (quote) => { setReviewLoading(true); try { const r = await axios.get(`${API}/marketplace/quotes/${quote.id}`, { headers }); setActiveReview(r.data); } catch { setActiveReview(quote); } setReviewLoading(false); };
  const refreshReview = async () => { if (!activeReview) return; try { const r = await axios.get(`${API}/marketplace/quotes/${activeReview.id}`, { headers }); setActiveReview(r.data); } catch {} };
  const closeReview = () => { setActiveReview(null); setSearchParams({}); };

  const handleRequestQuote = (actuary) => { setSelectedActuary(actuary); setQuoteForm({ plan_id: preselectedPlanId || '', message: '' }); setShowQuoteDialog(true); };

  const handleSubmitQuote = async () => {
    if (!quoteForm.plan_id) { toast.error('Select a plan'); return; }
    if (!selectedEmployer?.id) { toast.error('Select an employer first'); return; }
    setSubmitting(true);
    try {
      const plan = plans.find(p => p.id === quoteForm.plan_id);
      await axios.post(`${API}/marketplace/quotes`, { actuary_id: selectedActuary.id, plan_id: quoteForm.plan_id, employer_id: selectedEmployer.id, plan_name: plan?.plan_name || 'Unknown Plan', message: quoteForm.message }, { headers });
      toast.success('Quote request sent'); setShowQuoteDialog(false); loadQuotes(); setTab('quotes');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setSubmitting(false);
  };

  const handleAction = async (action, quoteId, ...args) => {
    try {
      if (action === 'pay') { await axios.put(`${API}/marketplace/quotes/${quoteId}/pay`, { payment_method: 'platform' }, { headers }); toast.success('Payment processed'); }
      else if (action === 'validate') { const [valid, reason] = args; await axios.put(`${API}/marketplace/quotes/${quoteId}/validate`, { valid, rejection_reason: reason || '' }, { headers }); toast.success(valid ? 'Certification validated' : 'Sent back for revision'); }
      else if (action === 'respond') { const [act, price, days, msg] = args; await axios.put(`${API}/marketplace/quotes/${quoteId}/respond`, { action: act, quoted_price: price, turnaround_days: days, actuary_message: msg }, { headers }); toast.success(act === 'accept' ? 'Quote accepted' : 'Quote declined'); }
      else if (action === 'deliver') { const [mvPct, notes] = args; await axios.put(`${API}/marketplace/quotes/${quoteId}/deliver`, { mv_percentage: mvPct, certification_notes: notes, document_name: `MV_Cert_${Date.now()}.pdf` }, { headers }); toast.success('Certification delivered'); }
      loadQuotes(); refreshReview();
    } catch (err) { toast.error(err.response?.data?.detail || 'Action failed'); }
  };

  const filtered = actuaries
    .filter(a => !search || a.name.toLowerCase().includes(search.toLowerCase()) || a.firm.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortBy === 'rating' ? b.rating - a.rating : sortBy === 'price_low' ? a.price - b.price : sortBy === 'price_high' ? b.price - a.price : a.turnaround_days - b.turnaround_days);

  const pendingQuotes = quotes.filter(q => q.status === 'pending');
  const acceptedQuotes = quotes.filter(q => ['accepted', 'paid', 'delivered', 'resubmit_needed'].includes(q.status));
  const rejectedQuotes = quotes.filter(q => q.status === 'rejected');
  const completedQuotes = quotes.filter(q => q.status === 'validated');

  // ── INLINE REVIEW PAGE ──
  if (activeReview) {
    return <CertificationReviewPage quote={activeReview} userRole={user?.role} onBack={closeReview} onAction={handleAction} API={API} headers={headers} onRefresh={refreshReview} loading={reviewLoading} />;
  }

  const isActuary = user?.role === 'actuary';

  return (
    <div className="min-h-screen" style={{ background: C.bg, fontFamily: "'Work Sans', sans-serif" }} data-testid="actuary-marketplace-page">
      {/* ── Hero Banner ── */}
      <div className="relative overflow-hidden" style={{ background: C.primary }}>
        <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")' }} />
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-8 relative">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: "'Manrope', sans-serif" }}>
                {isActuary ? 'Certification Requests' : 'Actuary Marketplace'}
              </h1>
              <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {isActuary ? 'Review and respond to MV certification requests' : 'Request MV certifications from qualified actuaries'}
              </p>
            </div>
            {/* Quick Stats */}
            <div className="flex gap-3">
              {pendingQuotes.length > 0 && (
                <div className="px-4 py-2 rounded-xl" style={{ background: 'rgba(255,255,255,0.1)' }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.5)' }}>Pending</p>
                  <p className="text-xl font-bold text-white tabular-nums" style={{ fontFamily: "'Manrope', sans-serif" }}>{pendingQuotes.length}</p>
                </div>
              )}
              {completedQuotes.length > 0 && (
                <div className="px-4 py-2 rounded-xl" style={{ background: 'rgba(255,255,255,0.1)' }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.5)' }}>Completed</p>
                  <p className="text-xl font-bold text-white tabular-nums" style={{ fontFamily: "'Manrope', sans-serif" }}>{completedQuotes.length}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 md:px-8 py-6">
        {/* ── Tabs ── */}
        <div className="flex gap-1.5 mb-6 p-1 rounded-xl w-fit" style={{ background: C.secondary }} data-testid="marketplace-tabs">
          {!isActuary && <TabBtn active={tab === 'directory'} onClick={() => setTab('directory')} icon={Store} label="Directory" testId="tab-directory" />}
          <TabBtn active={tab === 'quotes'} onClick={() => setTab('quotes')} icon={MessageSquare} label={isActuary ? 'All Requests' : 'My Requests'} testId="tab-quotes" badge={pendingQuotes.length || null} />
          {acceptedQuotes.length > 0 && !isActuary && <TabBtn active={tab === 'accepted'} onClick={() => setTab('accepted')} icon={CheckCircle2} label="Active" testId="tab-accepted" badge={acceptedQuotes.length} />}
          {rejectedQuotes.length > 0 && !isActuary && <TabBtn active={tab === 'rejected'} onClick={() => setTab('rejected')} icon={XCircle} label="Rejected" testId="tab-rejected" />}
          {completedQuotes.length > 0 && <TabBtn active={tab === 'completed'} onClick={() => setTab('completed')} icon={FileCheck} label="Completed" testId="tab-completed" badge={completedQuotes.length} />}
        </div>

        {/* ── Directory ── */}
        {tab === 'directory' && (
          <>
            <div className="flex items-center gap-3 mb-5">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: C.light }} />
                <Input data-testid="actuary-search" placeholder="Search actuaries..." value={search} onChange={e => setSearch(e.target.value)}
                  className="h-10 text-sm pl-10 rounded-xl border" style={{ borderColor: C.border, background: C.surface }} />
              </div>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="h-10 text-sm w-48 rounded-xl" style={{ borderColor: C.border }}>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rating">Highest Rated</SelectItem>
                  <SelectItem value="price_low">Price: Low to High</SelectItem>
                  <SelectItem value="price_high">Price: High to Low</SelectItem>
                  <SelectItem value="turnaround">Fastest Turnaround</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filtered.map(actuary => (
                <div key={actuary.id} className="rounded-2xl border p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
                  style={{ background: C.surface, borderColor: C.border }} data-testid={`actuary-card-${actuary.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: C.secondary }}>
                        <Award className="w-5 h-5" style={{ color: C.primary }} />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{actuary.name}</h3>
                        <p className="text-xs" style={{ color: C.muted }}>{actuary.firm}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 px-2.5 py-1 rounded-full" style={{ background: '#FFFBEB' }}>
                      <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                      <span className="text-xs font-bold text-amber-700">{actuary.rating}</span>
                      <span className="text-[10px]" style={{ color: C.muted }}>({actuary.reviews})</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="flex items-center gap-1.5 text-xs" style={{ color: C.muted }}>
                      <DollarSign className="w-3 h-3" /><span className="font-semibold" style={{ color: C.text }}>${actuary.price?.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs" style={{ color: C.muted }}>
                      <Clock className="w-3 h-3" /><span>{actuary.turnaround_days} days</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs" style={{ color: C.muted }}>
                      <MapPin className="w-3 h-3" /><span className="truncate">{actuary.location}</span>
                    </div>
                  </div>

                  {actuary.email && <p className="text-xs truncate mb-2" style={{ color: C.muted }} data-testid={`actuary-email-${actuary.id}`}>{actuary.email}</p>}

                  <div className="flex flex-wrap gap-1 mb-3">
                    {actuary.specialties?.map((s, i) => (
                      <span key={i} className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: C.secondary, color: C.secFg }}>{s}</span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-3" style={{ borderTop: `1px solid ${C.border}` }}>
                    <span className="text-xs" style={{ color: C.muted }}>{actuary.experience_years} yrs experience</span>
                    <button onClick={() => handleRequestQuote(actuary)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 hover:shadow-md"
                      style={{ background: C.primary, color: '#fff' }} data-testid={`request-quote-${actuary.id}`}>
                      <Send className="w-3 h-3" /> Request Quote
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── Quote Lists ── */}
        {tab === 'quotes' && <QuoteList quotes={isActuary ? quotes : [...pendingQuotes, ...acceptedQuotes, ...completedQuotes]} onOpen={openReview} userRole={user?.role} emptyMsg={isActuary ? 'No certification requests' : 'No quote requests yet'} onDirectory={() => setTab('directory')} />}
        {tab === 'accepted' && <QuoteList quotes={acceptedQuotes} onOpen={openReview} userRole={user?.role} emptyMsg="No active quotes" onDirectory={() => setTab('directory')} />}
        {tab === 'rejected' && <QuoteList quotes={rejectedQuotes} onOpen={openReview} userRole={user?.role} emptyMsg="No rejected quotes" onDirectory={() => setTab('directory')} />}
        {tab === 'completed' && <QuoteList quotes={completedQuotes} onOpen={openReview} userRole={user?.role} emptyMsg="No completed certifications" onDirectory={() => setTab('directory')} />}
      </div>

      {/* ── Request Quote Dialog ── */}
      <Dialog open={showQuoteDialog} onOpenChange={setShowQuoteDialog}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "'Manrope', sans-serif", color: C.text }}>Request MV Certification</DialogTitle>
            <DialogDescription className="text-xs" style={{ color: C.muted }}>Select a plan and send your request</DialogDescription>
          </DialogHeader>
          {selectedActuary && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-xl" style={{ background: C.secondary }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: C.surface }}>
                  <Award className="w-5 h-5" style={{ color: C.primary }} />
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: C.text }}>{selectedActuary.name}</p>
                  <p className="text-xs" style={{ color: C.muted }}>{selectedActuary.firm}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl" style={{ background: C.bg, border: `1px solid ${C.border}` }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: C.muted }}>Est. Price</p>
                  <p className="text-lg font-bold tabular-nums" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>${selectedActuary.price?.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-xl" style={{ background: C.bg, border: `1px solid ${C.border}` }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: C.muted }}>Turnaround</p>
                  <p className="text-lg font-bold tabular-nums" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>{selectedActuary.turnaround_days} days</p>
                </div>
              </div>
              <div>
                <Label className="text-xs font-medium" style={{ color: C.text }}>Select Plan *</Label>
                <Select value={quoteForm.plan_id} onValueChange={v => setQuoteForm(p => ({ ...p, plan_id: v }))}>
                  <SelectTrigger className="h-10 text-sm mt-1 rounded-xl" data-testid="quote-plan-select"><SelectValue placeholder="Choose a plan" /></SelectTrigger>
                  <SelectContent>{plans.map(p => <SelectItem key={p.id} value={p.id}>{p.plan_name} {p.mv_percentage ? `(MV: ${p.mv_percentage}%)` : ''}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium" style={{ color: C.text }}>Message (optional)</Label>
                <Textarea data-testid="quote-message" value={quoteForm.message} onChange={e => setQuoteForm(p => ({ ...p, message: e.target.value }))} placeholder="Special circumstances..." className="text-sm mt-1 min-h-[80px] rounded-xl" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowQuoteDialog(false)} className="h-10 text-sm rounded-xl">Cancel</Button>
            <button onClick={handleSubmitQuote} disabled={submitting || !quoteForm.plan_id}
              className="h-10 px-5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
              style={{ background: C.primary, color: '#fff' }} data-testid="submit-quote-request">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Send Request
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ── Tab Button ── */
function TabBtn({ active, onClick, icon: Icon, label, testId, badge }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
      style={{
        background: active ? C.surface : 'transparent',
        color: active ? C.primary : C.muted,
        fontWeight: active ? 600 : 400,
        boxShadow: active ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
      }}
      data-testid={testId}>
      <Icon className="w-3.5 h-3.5" />{label}
      {badge && <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full text-white" style={{ background: C.primary }}>{badge}</span>}
    </button>
  );
}

/* ── Quote List ── */
function QuoteList({ quotes, onOpen, userRole, emptyMsg, onDirectory }) {
  if (quotes.length === 0) return (
    <div className="rounded-2xl border-2 border-dashed p-16 text-center" style={{ borderColor: C.border }}>
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: C.secondary }}>
        <MessageSquare className="w-7 h-7" style={{ color: C.primary }} />
      </div>
      <p className="text-sm" style={{ color: C.muted }}>{emptyMsg}</p>
      {userRole !== 'actuary' && (
        <button onClick={onDirectory} className="mt-4 flex items-center gap-1.5 mx-auto px-4 py-2 rounded-xl text-xs font-semibold transition-colors"
          style={{ background: C.secondary, color: C.primary }}>
          <Store className="w-3 h-3" /> Browse Directory
        </button>
      )}
    </div>
  );

  return (
    <div className="space-y-3">
      {quotes.map(q => (
        <div key={q.id} onClick={() => onOpen(q)}
          className="rounded-2xl border p-4 flex items-center justify-between cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
          style={{ background: C.surface, borderColor: C.border }} data-testid={`quote-card-${q.id}`}>
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: C.secondary }}>
              <FileText className="w-5 h-5" style={{ color: C.primary }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <h4 className="text-sm font-bold truncate" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{q.plan_name}</h4>
                <QuoteStatusBadge status={q.status} />
              </div>
              <p className="text-xs" style={{ color: C.muted }}>
                {userRole === 'employer' ? `Actuary: ${q.actuary_name}` : `Employer: ${q.employer_name}`} · ${q.quoted_price?.toLocaleString()} · {q.turnaround_days} days
              </p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 ml-3 flex-shrink-0" style={{ color: C.light }} />
        </div>
      ))}
    </div>
  );
}

/* ════════════════════════════════════════════════
   FULL-PAGE CERTIFICATION REVIEW
   ════════════════════════════════════════════════ */
function CertificationReviewPage({ quote, userRole, onBack, onAction, API, headers, onRefresh, loading }) {
  const [respondPrice, setRespondPrice] = useState(quote.quoted_price || 0);
  const [respondDays, setRespondDays] = useState(quote.turnaround_days || 14);
  const [respondMsg, setRespondMsg] = useState('');
  const [mvPct, setMvPct] = useState('');
  const [certNotes, setCertNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fp = quote.full_plan || {};

  const steps = [
    { key: 'pending', label: 'Requested', icon: Clock },
    { key: 'accepted', label: 'Accepted', icon: CheckCircle2 },
    { key: 'paid', label: 'Paid', icon: CreditCard },
    { key: 'delivered', label: 'Delivered', icon: FileCheck },
    { key: 'validated', label: 'Validated', icon: CheckCircle2 },
  ];
  const statusOrder = ['pending', 'accepted', 'paid', 'delivered', 'validated'];
  const currentIdx = statusOrder.indexOf(quote.status === 'resubmit_needed' ? 'delivered' : quote.status === 'rejected' ? 'pending' : quote.status);

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin" style={{ color: C.primary }} /></div>;

  return (
    <div className="min-h-screen" style={{ background: C.bg, fontFamily: "'Work Sans', sans-serif" }} data-testid="certification-review-page">
      {/* Hero */}
      <div style={{ background: C.primary }}>
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-6">
          <button onClick={onBack} className="flex items-center gap-1 text-xs mb-3 transition-colors" style={{ color: 'rgba(255,255,255,0.6)' }} data-testid="back-btn">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Marketplace
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold text-white" style={{ fontFamily: "'Manrope', sans-serif" }}>Certification Review</h1>
              <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {quote.plan_name} · {userRole === 'actuary' ? `Employer: ${quote.employer_name}` : `Actuary: ${quote.actuary_name}`}
              </p>
            </div>
            <QuoteStatusBadge status={quote.status} />
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 md:px-8 py-6">
        {/* ── Progress Steps ── */}
        {quote.status !== 'rejected' && (
          <div className="flex items-center gap-0 mb-8 -mt-3 relative z-10">
            {steps.map((s, i) => {
              const done = i <= currentIdx;
              const Icon = s.icon;
              return (
                <div key={s.key} className="flex-1 flex flex-col items-center">
                  <div className="w-full flex items-center">
                    <div className="flex-1 h-1 rounded-full" style={{ background: done ? C.primary : C.border }} />
                    <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all"
                      style={{ background: done ? C.primary : C.surface, border: `2px solid ${done ? C.primary : C.border}` }}>
                      <Icon className="w-3.5 h-3.5" style={{ color: done ? '#fff' : C.light }} />
                    </div>
                    <div className="flex-1 h-1 rounded-full" style={{ background: i < currentIdx ? C.primary : C.border }} />
                  </div>
                  <p className="text-[10px] mt-2 font-medium" style={{ color: done ? C.primary : C.muted }}>{s.label}</p>
                </div>
              );
            })}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* ── LEFT: Plan Details + Documents ── */}
          <div className="lg:col-span-8 space-y-5">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4">
              <StatBox label="Quote Amount" value={`$${quote.quoted_price?.toLocaleString()}`} accent={C.primary} />
              <StatBox label="Turnaround" value={`${quote.turnaround_days} days`} accent={C.indigoTx} />
              <StatBox label="Employees" value={quote.employee_count || '—'} accent={C.successTx} />
            </div>

            {/* Plan Details */}
            {fp.plan_name && (
              <div className="rounded-2xl border overflow-hidden" style={{ background: C.surface, borderColor: C.border }} data-testid="plan-details-section">
                <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: `1px solid ${C.border}` }}>
                  <Shield className="w-4 h-4" style={{ color: C.primary }} />
                  <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>Plan Details</h3>
                </div>
                <div className="p-5 space-y-5">
                  <div className="grid grid-cols-4 gap-3">
                    <InfoCell label="Carrier" value={fp.carrier_name} />
                    <InfoCell label="Plan Type" value={fp.plan_type} />
                    <InfoCell label="Current MV %" value={fp.mv_percentage != null ? `${fp.mv_percentage}%` : 'Not set'} warn={fp.mv_percentage != null && fp.mv_percentage < 60} />
                    <InfoCell label="MEC Qualified" value={fp.mec_qualified ? 'Yes' : 'No'} />
                  </div>

                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.15em] mb-3" style={{ color: C.muted }}>Premiums & Contributions</p>
                    <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${C.border}` }}>
                      <table className="w-full text-xs">
                        <thead><tr style={{ background: C.bg }}>
                          <th className="py-2.5 px-4 text-left text-[10px] font-bold uppercase tracking-wider" style={{ color: C.muted }}>Tier</th>
                          <th className="py-2.5 px-4 text-right text-[10px] font-bold uppercase tracking-wider" style={{ color: C.muted }}>Total</th>
                          <th className="py-2.5 px-4 text-right text-[10px] font-bold uppercase tracking-wider" style={{ color: C.muted }}>Employer</th>
                          <th className="py-2.5 px-4 text-right text-[10px] font-bold uppercase tracking-wider" style={{ color: C.muted }}>Employee</th>
                        </tr></thead>
                        <tbody>
                          {[['Self-Only','self_only'],['EE + Spouse','employee_spouse'],['EE + Children','employee_children'],['Family','family']].map(([l,k]) => (
                            <tr key={k} style={{ borderTop: `1px solid ${C.border}` }}>
                              <td className="py-2.5 px-4 font-medium" style={{ color: C.text }}>{l}</td>
                              <td className="py-2.5 px-4 text-right tabular-nums" style={{ color: C.muted }}>${fp.premiums?.[k]?.toLocaleString() || 0}</td>
                              <td className="py-2.5 px-4 text-right tabular-nums" style={{ color: C.successTx }}>${fp.employer_contribution?.[k]?.toLocaleString() || 0}</td>
                              <td className="py-2.5 px-4 text-right tabular-nums font-semibold" style={{ color: C.text }}>${fp.employee_cost?.[k]?.toLocaleString() || 0}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.15em] mb-3" style={{ color: C.muted }}>Cost Sharing & Copays</p>
                    <div className="grid grid-cols-5 gap-2">
                      <InfoCell label="Deductible (Ind)" value={`$${fp.individual_deductible?.toLocaleString() || 0}`} />
                      <InfoCell label="Deductible (Fam)" value={`$${fp.family_deductible?.toLocaleString() || 0}`} />
                      <InfoCell label="Coinsurance" value={`${fp.coinsurance_rate || 0}%`} />
                      <InfoCell label="OOP Max (Ind)" value={`$${fp.oop_max_individual?.toLocaleString() || 0}`} />
                      <InfoCell label="OOP Max (Fam)" value={`$${fp.oop_max_family?.toLocaleString() || 0}`} />
                    </div>
                    <div className="grid grid-cols-5 gap-2 mt-2">
                      <InfoCell label="PCP Copay" value={`$${fp.copay_primary || 0}`} />
                      <InfoCell label="Specialist" value={`$${fp.copay_specialist || 0}`} />
                      <InfoCell label="ER Visit" value={`$${fp.copay_er || 0}`} />
                      <InfoCell label="Generic Rx" value={`$${fp.copay_generic_rx || 0}`} />
                      <InfoCell label="Brand Rx" value={`$${fp.copay_brand_rx || 0}`} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Document Checklist */}
            {quote.document_checklist?.length > 0 && (
              <div className="rounded-2xl border overflow-hidden" style={{ background: C.surface, borderColor: C.border }} data-testid="document-checklist-section">
                <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: `1px solid ${C.border}` }}>
                  <ClipboardList className="w-4 h-4" style={{ color: C.amberTx }} />
                  <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>Document Checklist</h3>
                </div>
                <div className="p-5 space-y-2">
                  {quote.document_checklist.map((doc, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-xl transition-colors"
                      style={{ background: doc.available ? C.successBg : C.bg, border: `1px solid ${doc.available ? '#A7F3D0' : C.border}` }}>
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{ background: doc.available ? '#D1FAE5' : '#F3F4F6' }}>
                          <FileText className="w-4 h-4" style={{ color: doc.available ? C.successTx : C.light }} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold truncate" style={{ color: C.text }}>{doc.name}</p>
                          <p className="text-[10px] truncate" style={{ color: C.muted }}>{doc.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        <span className="px-2 py-0.5 rounded text-[9px] font-medium" style={{ background: C.bg, color: C.muted }}>{doc.format}</span>
                        {doc.required && <span className="px-2 py-0.5 rounded text-[9px] font-bold" style={{ background: C.warnBg, color: C.warnTx }}>Required</span>}
                        {doc.available ? <CheckCircle2 className="w-4 h-4" style={{ color: C.successTx }} /> : <XCircle className="w-4 h-4" style={{ color: C.light }} />}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ── RIGHT SIDEBAR ── */}
          <div className="lg:col-span-4 space-y-5">
            {/* Chat */}
            {['accepted', 'paid', 'delivered', 'resubmit_needed', 'validated'].includes(quote.status) && (
              <ChatSection quoteId={quote.id} userRole={userRole} API={API} headers={headers} />
            )}

            {/* Messages (pre-acceptance) */}
            {(quote.message || quote.actuary_message) && !['accepted', 'paid', 'delivered', 'resubmit_needed', 'validated'].includes(quote.status) && (
              <div className="rounded-2xl border p-5" style={{ background: C.surface, borderColor: C.border }}>
                <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-3 flex items-center gap-2" style={{ color: C.muted }}>
                  <MessageSquare className="w-4 h-4" style={{ color: C.blueTx }} /> Messages
                </h3>
                {quote.message && <div className="p-3 rounded-xl mb-2" style={{ background: C.bg }}><p className="text-[10px] mb-0.5" style={{ color: C.muted }}>Employer</p><p className="text-xs" style={{ color: C.text }}>{quote.message}</p></div>}
                {quote.actuary_message && <div className="p-3 rounded-xl" style={{ background: C.blueBg }}><p className="text-[10px] mb-0.5" style={{ color: C.muted }}>Actuary</p><p className="text-xs" style={{ color: C.text }}>{quote.actuary_message}</p></div>}
              </div>
            )}

            {/* Employer Documents */}
            <DocSection title="Employer Documents" subtitle="Plan documents for review" docs={quote.employer_documents || []}
              canUpload={userRole === 'employer' && ['accepted', 'pending'].includes(quote.status)}
              canDelete={userRole === 'employer' && ['accepted', 'pending'].includes(quote.status)}
              quoteId={quote.id} docType="employer" API={API} headers={headers} uploading={uploading} setUploading={setUploading} onRefresh={onRefresh}
              uploadLabels={['Summary Plan Description (SPD)', 'Summary of Benefits & Coverage (SBC)', 'Plan Document', 'Rate Sheets', 'Evidence of Coverage (EOC)', 'Network Details', 'Prescription Formulary', 'Recent Claims Data', 'Employer Contributions', 'Non-Standard Features', 'Demographics', 'Prior MV Certification', 'Other']} />

            {/* Actuary Deliverables */}
            <DocSection title="Actuary Deliverables" subtitle="Certification documents & analysis" docs={quote.actuary_documents || []}
              canUpload={userRole === 'actuary' && ['paid', 'resubmit_needed'].includes(quote.status)}
              canDelete={userRole === 'actuary' && ['paid', 'resubmit_needed'].includes(quote.status)}
              quoteId={quote.id} docType="actuary" API={API} headers={headers} uploading={uploading} setUploading={setUploading} onRefresh={onRefresh}
              uploadLabels={['MV Certification Report', 'Technical Memorandum', 'ASOP 5 Compliance', 'Actuarial Value Analysis', 'Supporting Calculations', 'Other']} />

            {/* Certification Result */}
            {quote.certification && (
              <div className="rounded-2xl border-2 p-5" style={{ background: quote.status === 'validated' ? C.successBg : C.tealBg, borderColor: quote.status === 'validated' ? '#A7F3D0' : '#99F6E4' }}>
                <div className="flex items-center gap-2 mb-2"><FileCheck className="w-4 h-4" style={{ color: C.successTx }} /><p className="text-xs font-bold" style={{ color: C.successTx }}>Certification Result</p></div>
                <p className="text-4xl font-bold tabular-nums" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>{quote.certification.mv_percentage}%</p>
                <p className="text-xs mt-1" style={{ color: C.muted }}>{quote.certification.certification_notes}</p>
              </div>
            )}

            {quote.validation && !quote.validation.valid && (
              <div className="rounded-2xl border-2 p-5" style={{ background: '#FFF7ED', borderColor: '#FDBA74' }}>
                <div className="flex items-center gap-2 mb-1"><AlertTriangle className="w-4 h-4" style={{ color: '#C2410C' }} /><p className="text-xs font-bold" style={{ color: '#C2410C' }}>Revision Requested</p></div>
                <p className="text-xs" style={{ color: '#9A3412' }}>{quote.validation.rejection_reason}</p>
              </div>
            )}

            {/* ==== ACTIONS ==== */}

            {/* Actuary: Accept/Reject */}
            {userRole === 'actuary' && quote.status === 'pending' && (
              <div className="rounded-2xl border p-5 space-y-3" style={{ background: C.surface, borderColor: C.border }} data-testid="respond-section">
                <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>Respond to Request</h3>
                <div className="grid grid-cols-2 gap-2">
                  <div><Label className="text-xs" style={{ color: C.muted }}>Price ($)</Label><Input type="number" value={respondPrice} onChange={e => setRespondPrice(parseFloat(e.target.value) || 0)} className="h-9 text-sm mt-1 rounded-xl" data-testid="respond-price" /></div>
                  <div><Label className="text-xs" style={{ color: C.muted }}>Days</Label><Input type="number" value={respondDays} onChange={e => setRespondDays(parseInt(e.target.value) || 0)} className="h-9 text-sm mt-1 rounded-xl" data-testid="respond-days" /></div>
                </div>
                <div><Label className="text-xs" style={{ color: C.muted }}>Message</Label><Textarea value={respondMsg} onChange={e => setRespondMsg(e.target.value)} className="text-sm mt-1 min-h-[60px] rounded-xl" placeholder="Optional..." data-testid="respond-message" /></div>
                <div className="flex gap-2">
                  <button className="flex-1 h-9 rounded-xl text-xs font-semibold flex items-center justify-center gap-1 transition-colors"
                    style={{ background: C.primary, color: '#fff' }} onClick={() => onAction('respond', quote.id, 'accept', respondPrice, respondDays, respondMsg)} data-testid="accept-quote-btn">
                    <CheckCircle2 className="w-3 h-3" /> Accept
                  </button>
                  <button className="flex-1 h-9 rounded-xl text-xs font-semibold flex items-center justify-center gap-1 border-2 transition-colors"
                    style={{ borderColor: '#FECACA', color: C.dangerTx, background: C.dangerBg }} onClick={() => onAction('respond', quote.id, 'reject', 0, 0, respondMsg)} data-testid="reject-quote-btn">
                    <XCircle className="w-3 h-3" /> Decline
                  </button>
                </div>
              </div>
            )}

            {/* Actuary: Awaiting Payment */}
            {userRole === 'actuary' && quote.status === 'accepted' && (
              <div className="rounded-2xl border-2 p-5 text-center" style={{ background: C.blueBg, borderColor: '#93C5FD' }}>
                <CreditCard className="w-6 h-6 mx-auto mb-2" style={{ color: C.blueTx }} />
                <p className="text-xs font-bold" style={{ color: C.blueTx }}>Awaiting Payment</p>
                <p className="text-[10px] mt-0.5" style={{ color: '#3B82F6' }}>Employer must pay & upload documents</p>
              </div>
            )}

            {/* Actuary: Deliver */}
            {userRole === 'actuary' && ['paid', 'resubmit_needed'].includes(quote.status) && (() => {
              const hasActuaryDocs = (quote.actuary_documents || []).length > 0;
              return (
                <div className="rounded-2xl border p-5 space-y-3" style={{ background: C.surface, borderColor: C.border }} data-testid="deliver-section">
                  <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                    {quote.status === 'resubmit_needed' ? 'Resubmit Certification' : 'Deliver Certification'}
                  </h3>
                  {!hasActuaryDocs && (
                    <div className="flex items-center gap-2 p-3 rounded-xl" style={{ background: C.warnBg, border: `1px solid #FDE68A` }} data-testid="upload-actuary-docs-warning">
                      <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: C.warnTx }} />
                      <p className="text-[11px]" style={{ color: C.warnTx }}>Upload at least one document above before delivering.</p>
                    </div>
                  )}
                  {hasActuaryDocs && <p className="text-[11px]" style={{ color: C.muted }}>Deliverables uploaded. Enter MV result below.</p>}
                  <div><Label className="text-xs" style={{ color: C.muted }}>MV Percentage (%)</Label><Input type="number" step="0.01" value={mvPct} onChange={e => setMvPct(e.target.value)} className="h-9 text-sm mt-1 rounded-xl" placeholder="e.g., 65.4" data-testid="deliver-mv-pct" /></div>
                  <div><Label className="text-xs" style={{ color: C.muted }}>Certification Notes</Label><Textarea value={certNotes} onChange={e => setCertNotes(e.target.value)} className="text-sm mt-1 min-h-[60px] rounded-xl" placeholder="Methodology, observations..." data-testid="deliver-notes" /></div>
                  <button className="w-full h-9 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                    style={{ background: C.primary, color: '#fff' }} onClick={() => onAction('deliver', quote.id, parseFloat(mvPct) || 0, certNotes)} disabled={!mvPct || !hasActuaryDocs} data-testid="deliver-cert-btn">
                    <FileCheck className="w-3 h-3" /> {quote.status === 'resubmit_needed' ? 'Resubmit' : 'Deliver'} Certification
                  </button>
                </div>
              );
            })()}

            {/* Employer: Pay */}
            {userRole === 'employer' && quote.status === 'accepted' && (() => {
              const hasDocuments = (quote.employer_documents || []).length > 0;
              return (
                <div className="rounded-2xl border p-5 space-y-3" style={{ background: C.surface, borderColor: C.border }} data-testid="pay-section">
                  {!hasDocuments && (
                    <div className="flex items-center gap-2 p-3 rounded-xl" style={{ background: C.warnBg, border: `1px solid #FDE68A` }} data-testid="upload-docs-warning">
                      <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: C.warnTx }} />
                      <p className="text-[11px]" style={{ color: C.warnTx }}>Upload documents above before paying.</p>
                    </div>
                  )}
                  {hasDocuments && <p className="text-xs" style={{ color: C.muted }}>Documents uploaded. Pay to start certification.</p>}
                  <button className="w-full h-10 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                    style={{ background: C.primary, color: '#fff' }} onClick={() => onAction('pay', quote.id)} disabled={!hasDocuments} data-testid="pay-quote-btn">
                    <CreditCard className="w-4 h-4" /> Pay ${quote.quoted_price?.toLocaleString()}
                  </button>
                </div>
              );
            })()}

            {/* Employer: Validate */}
            {userRole === 'employer' && quote.status === 'delivered' && (
              <div className="rounded-2xl border p-5 space-y-3" style={{ background: C.surface, borderColor: C.border }} data-testid="validate-section">
                <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>Review Certification</h3>
                {!showRejectForm ? (
                  <div className="flex gap-2">
                    <button className="flex-1 h-9 rounded-xl text-xs font-semibold flex items-center justify-center gap-1 transition-colors"
                      style={{ background: C.successBg, color: C.successTx, border: `2px solid #A7F3D0` }} onClick={() => onAction('validate', quote.id, true)} data-testid="validate-accept-btn">
                      <CheckCircle2 className="w-3 h-3" /> Accept
                    </button>
                    <button className="flex-1 h-9 rounded-xl text-xs font-semibold flex items-center justify-center gap-1 border-2 transition-colors"
                      style={{ borderColor: '#FECACA', color: C.dangerTx, background: C.dangerBg }} onClick={() => setShowRejectForm(true)} data-testid="validate-reject-open-btn">
                      <XCircle className="w-3 h-3" /> Reject
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="text-sm min-h-[60px] rounded-xl" placeholder="Reason for rejection..." data-testid="reject-reason-input" />
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" className="h-8 text-xs rounded-xl" onClick={() => setShowRejectForm(false)}>Cancel</Button>
                      <button className="h-8 px-4 rounded-xl text-xs font-semibold disabled:opacity-50"
                        style={{ background: C.dangerTx, color: '#fff' }} onClick={() => { onAction('validate', quote.id, false, rejectReason); setShowRejectForm(false); }} disabled={!rejectReason} data-testid="submit-rejection-btn">Send Back</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Chat Section ── */
function ChatSection({ quoteId, userRole, API, headers }) {
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef(null);

  const loadMessages = useCallback(async () => { try { const r = await axios.get(`${API}/marketplace/quotes/${quoteId}/messages`, { headers }); setMessages(r.data); } catch {} setLoading(false); }, [API, quoteId]);
  useEffect(() => { loadMessages(); }, [loadMessages]);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);
  useEffect(() => { const i = setInterval(loadMessages, 8000); return () => clearInterval(i); }, [loadMessages]);

  const handleSend = async () => {
    if (!newMsg.trim()) return;
    setSending(true);
    try { await axios.post(`${API}/marketplace/quotes/${quoteId}/messages`, { message: newMsg.trim() }, { headers }); setNewMsg(''); loadMessages(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setSending(false);
  };

  const fmtTime = (iso) => iso ? new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <div className="rounded-2xl border overflow-hidden" style={{ background: C.surface, borderColor: C.border }} data-testid="chat-section">
      <div className="px-5 py-3 flex items-center gap-2" style={{ borderBottom: `1px solid ${C.border}` }}>
        <MessageSquare className="w-4 h-4" style={{ color: C.primary }} />
        <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: C.muted }}>Chat</h3>
        {messages.length > 0 && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: C.secondary, color: C.primary }}>{messages.length}</span>}
      </div>
      <div ref={scrollRef} className="px-4 overflow-y-auto max-h-[280px] min-h-[100px] space-y-2 py-3" data-testid="chat-messages">
        {loading && <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 animate-spin" style={{ color: C.primary }} /></div>}
        {!loading && messages.length === 0 && <p className="text-xs text-center py-4" style={{ color: C.muted }}>No messages yet. Start the conversation.</p>}
        {messages.map(msg => {
          const isMe = msg.sender_role === userRole;
          return (
            <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`} data-testid={`chat-msg-${msg.id}`}>
              <div className="max-w-[85%] rounded-2xl px-3.5 py-2.5"
                style={{ background: isMe ? C.primary : C.secondary, color: isMe ? '#fff' : C.text }}>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[10px] font-semibold" style={{ opacity: 0.7 }}>{msg.sender_name} ({msg.sender_role === 'employer' ? 'Employer' : 'Actuary'})</span>
                </div>
                <p className="text-xs whitespace-pre-wrap break-words">{msg.message}</p>
                <p className="text-[9px] mt-1" style={{ opacity: 0.5 }}>{fmtTime(msg.created_at)}</p>
              </div>
            </div>
          );
        })}
      </div>
      <div className="px-4 pb-3 pt-2" style={{ borderTop: `1px solid ${C.border}` }}>
        <div className="flex gap-2">
          <Input value={newMsg} onChange={e => setNewMsg(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Type a message..." className="h-9 text-xs flex-1 rounded-xl" data-testid="chat-input" />
          <button onClick={handleSend} disabled={sending || !newMsg.trim()}
            className="h-9 w-9 rounded-xl flex items-center justify-center disabled:opacity-50 transition-colors"
            style={{ background: C.primary, color: '#fff' }} data-testid="chat-send-btn">
            {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Document Section ── */
function DocSection({ title, subtitle, docs, canUpload, canDelete, quoteId, docType, API, headers, uploading, setUploading, onRefresh, uploadLabels }) {
  const [selectedLabel, setSelectedLabel] = useState(uploadLabels?.[0] || 'Other');
  let fileInputRef = null;

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append('file', file); fd.append('doc_type', docType); fd.append('doc_label', selectedLabel);
      await axios.post(`${API}/marketplace/quotes/${quoteId}/upload`, fd, { headers: { ...headers, 'Content-Type': 'multipart/form-data' } });
      toast.success(`Uploaded: ${file.name}`); if (onRefresh) onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Upload failed'); }
    setUploading(false); e.target.value = '';
  };

  const handleDelete = async (docId) => { try { await axios.delete(`${API}/marketplace/documents/${docId}`, { headers }); toast.success('Removed'); if (onRefresh) onRefresh(); } catch { toast.error('Failed'); } };
  const handleDownload = async (doc) => { try { const r = await axios.get(`${API}/marketplace/documents/${doc.id}/download`, { headers, responseType: 'blob' }); const u = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = u; a.download = doc.filename; a.click(); URL.revokeObjectURL(u); } catch { toast.error('Download failed'); } };
  const fmtSize = (b) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

  return (
    <div className="rounded-2xl border overflow-hidden" style={{ background: C.surface, borderColor: C.border }} data-testid={`doc-section-${docType}`}>
      <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2">
          <Paperclip className="w-4 h-4" style={{ color: C.indigoTx }} />
          <div>
            <h3 className="text-xs font-bold" style={{ color: C.text }}>{title}</h3>
            <p className="text-[10px]" style={{ color: C.muted }}>{subtitle}</p>
          </div>
        </div>
        {docs.length > 0 && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: C.secondary, color: C.primary }}>{docs.length}</span>}
      </div>
      <div className="p-4 space-y-2">
        {docs.map(doc => (
          <div key={doc.id} className="flex items-center justify-between p-3 rounded-xl" style={{ background: C.bg }} data-testid={`uploaded-doc-${doc.id}`}>
            <div className="flex items-center gap-2.5 flex-1 min-w-0">
              <FileText className="w-4 h-4 shrink-0" style={{ color: C.muted }} />
              <div className="min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: C.text }}>{doc.doc_label || doc.filename}</p>
                <p className="text-[10px] truncate" style={{ color: C.muted }}>{doc.filename} · {fmtSize(doc.size)} · {doc.uploaded_by_name}</p>
              </div>
            </div>
            <div className="flex gap-1 ml-2">
              <button onClick={() => handleDownload(doc)} className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors hover:bg-gray-100" data-testid={`download-doc-${doc.id}`}>
                <Download className="w-3.5 h-3.5" style={{ color: C.muted }} />
              </button>
              {canDelete && <button onClick={() => handleDelete(doc.id)} className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors hover:bg-red-50" data-testid={`delete-doc-${doc.id}`}>
                <Trash2 className="w-3.5 h-3.5" style={{ color: C.dangerTx }} />
              </button>}
            </div>
          </div>
        ))}
        {canUpload && (
          <div className="flex items-center gap-2 pt-1">
            <Select value={selectedLabel} onValueChange={setSelectedLabel}>
              <SelectTrigger className="h-8 text-[11px] flex-1 rounded-lg" data-testid={`doc-label-select-${docType}`}><SelectValue /></SelectTrigger>
              <SelectContent>{uploadLabels.map(l => <SelectItem key={l} value={l} className="text-xs">{l}</SelectItem>)}</SelectContent>
            </Select>
            <input type="file" className="hidden" ref={el => fileInputRef = el} onChange={handleUpload} accept=".pdf,.xlsx,.xls,.csv,.doc,.docx,.txt" />
            <button onClick={() => fileInputRef?.click()} disabled={uploading}
              className="h-8 px-3 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors disabled:opacity-50"
              style={{ background: C.secondary, color: C.primary }} data-testid={`upload-doc-btn-${docType}`}>
              {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />} Upload
            </button>
          </div>
        )}
        {docs.length === 0 && !canUpload && <p className="text-xs text-center py-3" style={{ color: C.muted }}>No documents yet</p>}
      </div>
    </div>
  );
}

/* ── Small Components ── */
function StatBox({ label, value, accent }) {
  return (
    <div className="rounded-2xl border p-4 text-center" style={{ background: C.surface, borderColor: C.border }}>
      <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: C.muted }}>{label}</p>
      <p className="text-2xl font-bold tabular-nums mt-1" style={{ color: accent, fontFamily: "'Manrope', sans-serif" }}>{value}</p>
    </div>
  );
}

function InfoCell({ label, value, warn }) {
  return (
    <div className="p-2.5 rounded-xl" style={{ background: warn ? C.warnBg : C.bg, border: warn ? `1px solid #FDE68A` : 'none' }}>
      <p className="text-[10px]" style={{ color: C.muted }}>{label}</p>
      <p className="font-semibold text-xs" style={{ color: warn ? C.warnTx : C.text }}>{value || 'N/A'}</p>
    </div>
  );
}
