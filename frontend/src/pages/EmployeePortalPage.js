import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import {
  CheckCircle2, XCircle, Shield, DollarSign, Stethoscope, Loader2,
  Building2, Pill, Briefcase, CalendarDays, Heart,
  CreditCard, Eye, ChevronDown, ChevronUp,
  CircleDot, FileText, Download, ArrowRight, TrendingUp, Activity,
  Lock, Timer, Clock, Send
} from 'lucide-react';

/* ── Design Tokens ─────────────────────────────────── */
const C = {
  bg:      '#F9F9F8',
  surface: '#FFFFFF',
  primary: '#1C3B35',
  primaryH:'#162F2A',
  secondary:'#E3EBE6',
  secFg:   '#1C3B35',
  text:    '#111827',
  muted:   '#4B5563',
  border:  '#E5E7EB',
  successBg:'#E8F0EB', successTx:'#1F4D36',
  warnBg:  '#FEF3C7', warnTx:  '#92400E',
  dangerBg:'#FEE2E2', dangerTx:'#991B1B',
};

const TIER_LABELS = {
  self_only: 'Self Only',
  employee_spouse: 'Employee + Spouse',
  employee_children: 'Employee + Children',
  family: 'Family',
};

export default function EmployeePortalPage() {
  const { user, token, API } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [selectedTier, setSelectedTier] = useState('self_only');
  const [selectedAddOns, setSelectedAddOns] = useState([]);
  const [showDecline, setShowDecline] = useState(false);
  const [declineReason, setDeclineReason] = useState('');
  const [declineDetail, setDeclineDetail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState(null);
  const [downloading1095c, setDownloading1095c] = useState(false);
  const [enrollPeriod, setEnrollPeriod] = useState(null);
  const [hasException, setHasException] = useState(false);
  const [excReason, setExcReason] = useState('');
  const [excSubmitting, setExcSubmitting] = useState(false);
  const [excRequested, setExcRequested] = useState(false);
  const [exceptionStatus, setExceptionStatus] = useState(null); // null, 'pending', 'approved', 'rejected'

  const loadPortal = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/enrollment/employee/my-plans`, { headers });
      setData(res.data);
      // Fetch enrollment period
      const employerId = res.data?.employer_id || user?.employer_id;
      if (employerId) {
        try {
          const epRes = await axios.get(`${API}/enrollment/periods/${employerId}/active`, { headers });
          setEnrollPeriod(epRes.data?.period || null);
          setHasException(epRes.data?.has_exception || false);
          const excStatus = epRes.data?.exception_status || null;
          setExceptionStatus(excStatus);
          if (excStatus === 'pending' || excStatus === 'rejected') {
            setExcRequested(true);
          }
        } catch (e) {}
      }
    } catch (err) { console.error(err); }
    setLoading(false);
  }, [API, token]);

  useEffect(() => { loadPortal(); }, [loadPortal]);

  const handleEnroll = async () => {
    if (!selectedPlan) { toast.error('Select a plan'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/enrollment/employee/enroll`, {
        plan_id: selectedPlan.id, coverage_tier: selectedTier, add_on_plan_ids: selectedAddOns,
      }, { headers });
      toast.success('Enrollment confirmed!');
      loadPortal();
    } catch (err) { toast.error(err.response?.data?.detail || 'Enrollment failed'); }
    setSubmitting(false);
  };

  const handleDecline = async () => {
    if (!declineReason) { toast.error('Select a reason'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/enrollment/employee/decline`, {
        reason: declineReason, reason_detail: declineDetail,
      }, { headers });
      toast.success('Coverage declined');
      setShowDecline(false);
      loadPortal();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setSubmitting(false);
  };

  const toggleAddOn = (planId) => {
    setSelectedAddOns(prev =>
      prev.includes(planId) ? prev.filter(id => id !== planId) : [...prev, planId]
    );
  };

  const download1095c = async () => {
    setDownloading1095c(true);
    try {
      const res = await axios.get(`${API}/enrollment/employee/my-1095c/pdf`, { headers, responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `1095-C_${user?.name?.replace(/\s+/g, '_') || 'form'}_${new Date().getFullYear()}.pdf`;
      link.click();
      URL.revokeObjectURL(link.href);
      toast.success('Form 1095-C downloaded');
    } catch (err) { toast.error(err.response?.data?.detail || 'Form 1095-C not available'); }
    setDownloading1095c(false);
  };

  const requestException = async () => {
    setExcSubmitting(true);
    try {
      await axios.post(`${API}/enrollment/exceptions`, { reason: excReason }, { headers });
      toast.success('Exception request submitted to your employer');
      setExcRequested(true);
      setExcReason('');
    } catch (err) { toast.error(err.response?.data?.detail || 'Request failed'); }
    setExcSubmitting(false);
  };

  // Enrollment period helpers
  const isEnrollmentOpen = (() => {
    if (!enrollPeriod) return true; // No period configured = open by default
    if (enrollPeriod.status === 'active') {
      const today = new Date().toISOString().slice(0, 10);
      return today >= enrollPeriod.start_date && today <= enrollPeriod.end_date;
    }
    return false;
  })();
  const canEnroll = isEnrollmentOpen || hasException;
  const daysRemaining = (() => {
    if (!enrollPeriod || enrollPeriod.status !== 'active') return null;
    const end = new Date(enrollPeriod.end_date + 'T23:59:59');
    return Math.max(0, Math.ceil((end - new Date()) / (1000 * 60 * 60 * 24)));
  })();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]" style={{ background: C.bg }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: C.primary }} />
      </div>
    );
  }

  const enrollment = data?.current_enrollment;
  const planDetail = data?.enrolled_plan_detail;
  const addonDetails = data?.enrolled_addon_details || [];
  const employerName = data?.employer_name || user?.employer_name || '';
  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

  // ════════════════════════════════════════
  //  ENROLLED / DECLINED VIEW
  // ════════════════════════════════════════
  if (enrollment) {
    const isEnrolled = enrollment.status === 'enrolled';
    const empPremium = enrollment.employee_premium || 0;
    const erContrib = enrollment.employer_contribution || 0;
    const totalPremium = enrollment.total_premium || 0;
    const erPct = totalPremium > 0 ? Math.round((erContrib / totalPremium) * 100) : 0;

    return (
      <div className="min-h-screen" style={{ background: C.bg, fontFamily: "'Work Sans', sans-serif" }} data-testid="employee-portal-page">
        {/* ── Hero Banner ── */}
        <div className="relative overflow-hidden" style={{ background: C.primary }}>
          <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")' }} />
          <div className="max-w-6xl mx-auto px-6 md:px-8 py-8 relative">
            <div className="flex items-center gap-5">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-xl font-bold shadow-lg"
                style={{ background: C.secondary, color: C.primary, fontFamily: "'Manrope', sans-serif" }}>
                {initials}
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: "'Manrope', sans-serif" }}>
                  {user?.name}
                </h1>
                <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  {employerName} · {new Date().getFullYear()} Plan Year
                </p>
              </div>
              <div className="ml-auto">
                {isEnrolled ? (
                  <Badge className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider"
                    style={{ background: C.successBg, color: C.successTx, border: 'none' }}
                    data-testid="enrollment-status-badge">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                    {enrollment.approved ? 'Active Coverage' : 'Pending Approval'}
                  </Badge>
                ) : (
                  <Badge className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider"
                    style={{ background: C.dangerBg, color: C.dangerTx, border: 'none' }}
                    data-testid="enrollment-status-badge">
                    <XCircle className="w-3.5 h-3.5 mr-1.5" /> Declined
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── Content ── */}
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-8">
          {/* ── Quick Stats Row (enrolled only) ── */}
          {isEnrolled && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 -mt-12 mb-8 relative z-10">
              <StatCard icon={DollarSign} label="Your Monthly Cost" value={`$${empPremium.toFixed(2)}`} accent={C.primary} />
              <StatCard icon={TrendingUp} label="Employer Contribution" value={`$${erContrib.toFixed(2)}`} accent={C.successTx} sub={`${erPct}% of total`} />
              <StatCard icon={CreditCard} label="Total Premium" value={`$${totalPremium.toFixed(2)}`} accent={C.muted} />
            </div>
          )}

          {/* ── Declined offset ── */}
          {!isEnrolled && <div className="-mt-4 mb-8" />}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* ── Left Sidebar ── */}
            <div className="lg:col-span-4 space-y-5">
              {/* Profile Details */}
              <div className="rounded-2xl border p-5" style={{ background: C.surface, borderColor: C.border }} data-testid="profile-card">
                <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-4" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                  Profile Details
                </h3>
                <div className="space-y-3.5">
                  <ProfileRow icon={Building2} label="Employer" value={employerName} />
                  <ProfileRow icon={Briefcase} label="Role" value={user?.role} />
                  <ProfileRow icon={CalendarDays} label="Plan Year" value={new Date().getFullYear()} />
                  {enrollment.offer_code && (
                    <ProfileRow icon={Shield} label="Offer Code" value={enrollment.offer_code} />
                  )}
                </div>
              </div>

              {/* Declined Info */}
              {!isEnrolled && (
                <div className="rounded-2xl border-2 p-5" style={{ background: C.dangerBg, borderColor: '#FECACA' }} data-testid="decline-info-card">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(153,27,27,0.08)' }}>
                      <XCircle className="w-5 h-5" style={{ color: C.dangerTx }} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold" style={{ color: C.dangerTx, fontFamily: "'Manrope', sans-serif" }}>Coverage Declined</h3>
                      <p className="text-xs mt-1 capitalize" style={{ color: '#B91C1C' }}>
                        {enrollment.decline_reason?.replace(/_/g, ' ')}
                      </p>
                      {enrollment.decline_reason_detail && (
                        <p className="text-xs mt-1.5" style={{ color: C.muted }}>{enrollment.decline_reason_detail}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Employer Coverage Bar (enrolled) */}
              {isEnrolled && (
                <div className="rounded-2xl border p-5" style={{ background: C.surface, borderColor: C.border }} data-testid="cost-summary-card">
                  <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-4" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                    Cost Breakdown
                  </h3>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="flex-1">
                      <div className="h-3 rounded-full overflow-hidden" style={{ background: C.border }}>
                        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${erPct}%`, background: C.primary }} />
                      </div>
                    </div>
                    <span className="text-sm font-bold tabular-nums" style={{ color: C.primary }}>{erPct}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <div>
                      <span style={{ color: C.muted }}>Employer</span>
                      <p className="font-bold tabular-nums" style={{ color: C.successTx }}>${erContrib.toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <span style={{ color: C.muted }}>You Pay</span>
                      <p className="font-bold tabular-nums" style={{ color: C.text }}>${empPremium.toFixed(2)}</p>
                    </div>
                  </div>
                  {addonDetails.length > 0 && (
                    <>
                      <Separator className="my-3" />
                      {addonDetails.map(ao => (
                        <div key={ao.id} className="flex justify-between text-xs py-1">
                          <span style={{ color: C.muted }}>{ao.plan_name}</span>
                          <span className="font-semibold tabular-nums">${(ao.employee_cost?.self_only || 0).toFixed(2)}</span>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}

              {/* 1095-C Download */}
              <div className="rounded-2xl border p-5" style={{ background: C.surface, borderColor: C.border }} data-testid="form-1095c-card">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: C.secondary }}>
                    <FileText className="w-5 h-5" style={{ color: C.primary }} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>Form 1095-C</h3>
                    <p className="text-[11px]" style={{ color: C.muted }}>IRS Health Coverage Statement</p>
                  </div>
                </div>
                <p className="text-xs mb-4" style={{ color: C.muted }}>
                  Download your IRS Form 1095-C documenting the health coverage offered by your employer.
                </p>
                <button
                  onClick={download1095c}
                  disabled={downloading1095c}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:shadow-md disabled:opacity-50"
                  style={{ background: C.secondary, color: C.primary }}
                  data-testid="download-1095c-btn"
                >
                  {downloading1095c
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Downloading...</>
                    : <><Download className="w-4 h-4" /> Download PDF</>
                  }
                </button>
              </div>
            </div>

            {/* ── Main Content ── */}
            <div className="lg:col-span-8 space-y-5">
              {/* Enrolled Plan */}
              {isEnrolled && planDetail && (
                <>
                  <div className="rounded-2xl border p-6" style={{ background: C.surface, borderColor: C.border }} data-testid="enrolled-plan-card">
                    <div className="flex items-start justify-between mb-5">
                      <div>
                        <div className="flex items-center gap-2.5 mb-1">
                          <h2 className="text-lg font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{enrollment.plan_name}</h2>
                          <Badge className="rounded-full text-[10px] font-semibold px-2.5" style={{ background: C.secondary, color: C.secFg, border: 'none' }}>
                            {enrollment.plan_type}
                          </Badge>
                          {planDetail.mec_qualified && (
                            <Badge className="rounded-full text-[10px] font-semibold px-2.5" style={{ background: '#DBEAFE', color: '#1E40AF', border: 'none' }}>MEC</Badge>
                          )}
                          {(() => {
                            const erContrib = planDetail.employer_contribution?.self_only || 0;
                            const totalPrem = planDetail.premiums?.self_only || 0;
                            const erPct = totalPrem > 0 ? (erContrib / totalPrem * 100) : 0;
                            const mvPasses = (planDetail.mv_percentage || 0) >= 60 && erPct >= 60;
                            if (planDetail.mv_certified || planDetail.mv_percentage) {
                              return (
                                <Badge className="rounded-full text-[10px] font-semibold px-2.5" style={{
                                  background: mvPasses ? C.successBg : C.warnBg,
                                  color: mvPasses ? C.successTx : C.warnTx, border: 'none'
                                }} data-testid="mv-badge">
                                  MV {planDetail.mv_percentage}%{!mvPasses ? ' (Fail)' : ''}
                                </Badge>
                              );
                            }
                            return null;
                          })()}
                        </div>
                        <p className="text-sm" style={{ color: C.muted }}>{enrollment.carrier_name}</p>
                      </div>
                      <Badge className="rounded-full text-xs font-semibold px-3 py-1 capitalize" style={{ background: C.secondary, color: C.primary, border: 'none' }}>
                        {enrollment.coverage_tier?.replace(/_/g, ' ')}
                      </Badge>
                    </div>

                    {/* Bento Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                      <BentoStat label="Deductible" sub="Individual" value={`$${(planDetail.individual_deductible || 0).toLocaleString()}`} />
                      <BentoStat label="Deductible" sub="Family" value={`$${(planDetail.family_deductible || 0).toLocaleString()}`} />
                      <BentoStat label="OOP Max" sub="Individual" value={`$${(planDetail.oop_max_individual || 0).toLocaleString()}`} />
                      <BentoStat label="OOP Max" sub="Family" value={`$${(planDetail.oop_max_family || 0).toLocaleString()}`} />
                    </div>

                    {/* Benefit Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="rounded-xl p-4" style={{ background: C.bg }}>
                        <h4 className="text-xs font-bold uppercase tracking-[0.15em] mb-3 flex items-center gap-1.5" style={{ color: C.muted }}>
                          <Stethoscope className="w-3.5 h-3.5" /> Copays
                        </h4>
                        <div className="space-y-2">
                          <BenefitLine label="Primary Care" value={`$${planDetail.copay_primary || 0}`} />
                          <BenefitLine label="Specialist" value={`$${planDetail.copay_specialist || 0}`} />
                          <BenefitLine label="Emergency Room" value={`$${planDetail.copay_er || 0}`} />
                        </div>
                      </div>
                      <div className="rounded-xl p-4" style={{ background: C.bg }}>
                        <h4 className="text-xs font-bold uppercase tracking-[0.15em] mb-3 flex items-center gap-1.5" style={{ color: C.muted }}>
                          <Pill className="w-3.5 h-3.5" /> Prescriptions
                        </h4>
                        <div className="space-y-2">
                          <BenefitLine label="Generic Drugs" value={`$${planDetail.copay_generic_rx || 0}`} />
                          <BenefitLine label="Brand Name" value={`$${planDetail.copay_brand_rx || 0}`} />
                          <BenefitLine label="Coinsurance" value={`${planDetail.coinsurance_rate || 0}%`} />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Premium Breakdown */}
                  <div className="rounded-2xl border p-6" style={{ background: C.surface, borderColor: C.border }} data-testid="premium-tiers-card">
                    <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-5" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                      Premium Breakdown — All Coverage Tiers
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                            <th className="text-left py-3 pr-4 text-xs font-bold uppercase tracking-wider" style={{ color: C.muted }}>Tier</th>
                            <th className="text-right py-3 px-4 text-xs font-bold uppercase tracking-wider" style={{ color: C.muted }}>Total</th>
                            <th className="text-right py-3 px-4 text-xs font-bold uppercase tracking-wider" style={{ color: C.muted }}>Employer</th>
                            <th className="text-right py-3 pl-4 text-xs font-bold uppercase tracking-wider" style={{ color: C.muted }}>You Pay</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(TIER_LABELS).map(([key, label]) => {
                            const total = planDetail.premiums?.[key] || 0;
                            const er = planDetail.employer_contribution?.[key] || 0;
                            const ee = planDetail.employee_cost?.[key] || 0;
                            const isCurrent = enrollment.coverage_tier === key;
                            return (
                              <tr key={key} className="transition-colors duration-150"
                                style={{ background: isCurrent ? C.secondary : 'transparent', borderBottom: `1px solid ${C.border}` }}>
                                <td className="py-4 pr-4 flex items-center gap-2">
                                  {isCurrent && <CircleDot className="w-3.5 h-3.5" style={{ color: C.primary }} />}
                                  <span className={isCurrent ? 'font-semibold' : ''} style={{ color: isCurrent ? C.primary : C.text }}>
                                    {label}
                                  </span>
                                  {isCurrent && (
                                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full" style={{ background: C.primary, color: '#fff' }}>
                                      Current
                                    </span>
                                  )}
                                </td>
                                <td className="py-4 px-4 text-right tabular-nums" style={{ color: C.muted }}>${total.toFixed(0)}/mo</td>
                                <td className="py-4 px-4 text-right tabular-nums" style={{ color: C.successTx }}>${er.toFixed(0)}/mo</td>
                                <td className="py-4 pl-4 text-right tabular-nums font-semibold" style={{ color: C.text }}>${ee.toFixed(0)}/mo</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Add-on Benefits */}
                  {addonDetails.length > 0 && (
                    <div className="rounded-2xl border p-6" style={{ background: C.surface, borderColor: C.border }} data-testid="addon-details-card">
                      <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-4" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                        Add-On Benefits
                      </h3>
                      <div className="space-y-3">
                        {addonDetails.map(ao => (
                          <div key={ao.id} className="flex items-center gap-4 p-4 rounded-xl" style={{ background: C.bg }}>
                            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: ao.category === 'dental' ? '#DBEAFE' : '#EDE9FE' }}>
                              {ao.category === 'dental' ? <Heart className="w-5 h-5 text-blue-600" /> : <Eye className="w-5 h-5 text-violet-600" />}
                            </div>
                            <div className="flex-1">
                              <p className="text-sm font-semibold" style={{ color: C.text }}>{ao.plan_name}</p>
                              <p className="text-xs capitalize" style={{ color: C.muted }}>{ao.category} · {ao.carrier_name}</p>
                            </div>
                            <p className="text-base font-bold tabular-nums" style={{ color: C.text }}>${(ao.employee_cost?.self_only || 0).toFixed(0)}<span className="text-xs font-normal" style={{ color: C.muted }}>/mo</span></p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Declined — empty state */}
              {!isEnrolled && (
                <div className="rounded-2xl border-2 border-dashed p-12 text-center" style={{ borderColor: C.border }}>
                  <Shield className="w-12 h-12 mx-auto mb-4" style={{ color: '#D1D5DB' }} />
                  <p className="text-base font-semibold" style={{ color: C.text }}>No Active Coverage</p>
                  <p className="text-sm mt-2 max-w-md mx-auto" style={{ color: C.muted }}>
                    You have declined coverage for this plan year. Contact your HR department if you need to make changes.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════
  //  OPEN ENROLLMENT VIEW
  // ════════════════════════════════════════
  return (
    <div className="min-h-screen" style={{ background: C.bg, fontFamily: "'Work Sans', sans-serif" }} data-testid="employee-portal-page">
      {/* ── Hero Banner ── */}
      <div className="relative overflow-hidden" style={{ background: C.primary }}>
        <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")' }} />
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-8 relative">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-xl font-bold shadow-lg"
              style={{ background: C.secondary, color: C.primary, fontFamily: "'Manrope', sans-serif" }}>
              {initials}
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: "'Manrope', sans-serif" }}>
                Open Enrollment
              </h1>
              <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {employerName} · {new Date().getFullYear()} Plan Year
              </p>
            </div>
            <div className="ml-auto flex items-center gap-3">
              {daysRemaining !== null && isEnrollmentOpen && (
                <div className="px-4 py-2 rounded-xl" style={{ background: 'rgba(255,255,255,0.12)' }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.5)' }}>Closes in</p>
                  <p className="text-xl font-bold text-white tabular-nums" style={{ fontFamily: "'Manrope', sans-serif" }}>{daysRemaining}d</p>
                </div>
              )}
              <Badge className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider"
                style={{ background: canEnroll ? C.successBg : C.warnBg, color: canEnroll ? C.successTx : C.warnTx, border: 'none' }}
                data-testid="enrollment-window-badge">
                {canEnroll ? <><CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> ACA Coverage Available</> : <><Lock className="w-3.5 h-3.5 mr-1.5" /> Enrollment Closed</>}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 md:px-8 py-8">
        {/* Enrollment Closed Banner + Exception Request */}
        {!canEnroll && (
          <div className="rounded-2xl border-2 p-5 mb-6" style={{ background: exceptionStatus === 'rejected' ? '#FEE2E2' : '#FFF8ED', borderColor: exceptionStatus === 'rejected' ? '#FECACA' : '#F5D5A0' }} data-testid="enrollment-closed-banner">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: exceptionStatus === 'rejected' ? C.dangerBg : C.warnBg }}>
                <Lock className="w-6 h-6" style={{ color: exceptionStatus === 'rejected' ? C.dangerTx : C.warnTx }} />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>
                  {exceptionStatus === 'rejected' ? 'Exception Request Rejected' : 'Enrollment Window Closed'}
                </h3>
                <p className="text-xs mt-1" style={{ color: C.muted }}>
                  {enrollPeriod ? `The enrollment period "${enrollPeriod.period_name}" ended on ${new Date(enrollPeriod.end_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}.` : 'There is no active enrollment window.'}
                </p>

                {/* No request submitted yet */}
                {!excRequested && exceptionStatus === null && (
                  <>
                    <p className="text-xs mt-2" style={{ color: C.muted }}>You may request an exception from your employer.</p>
                    <div className="flex items-center gap-2 mt-3">
                      <Textarea
                        placeholder="Briefly explain why you need to enroll outside the window..."
                        value={excReason}
                        onChange={e => setExcReason(e.target.value)}
                        className="h-9 min-h-[36px] text-xs resize-none"
                        style={{ maxWidth: 400 }}
                        data-testid="exception-reason-input"
                      />
                      <Button
                        size="sm" className="h-9 text-xs"
                        style={{ background: C.primary, color: '#fff' }}
                        onClick={requestException}
                        disabled={!excReason.trim() || excSubmitting}
                        data-testid="request-exception-btn">
                        {excSubmitting ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Send className="w-3 h-3 mr-1" />}
                        Request Exception
                      </Button>
                    </div>
                  </>
                )}

                {/* Request pending review */}
                {exceptionStatus === 'pending' && (
                  <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded-lg" style={{ background: C.warnBg }}>
                    <Clock className="w-4 h-4" style={{ color: C.warnTx }} />
                    <p className="text-xs font-semibold" style={{ color: C.warnTx }}>
                      Your exception request is being reviewed by HR. You will be notified once a decision is made.
                    </p>
                  </div>
                )}

                {/* Request rejected */}
                {exceptionStatus === 'rejected' && (
                  <div className="flex items-center gap-2 mt-3 px-3 py-2.5 rounded-lg" style={{ background: '#FEE2E2' }}>
                    <XCircle className="w-4 h-4 flex-shrink-0" style={{ color: C.dangerTx }} />
                    <p className="text-xs font-semibold" style={{ color: C.dangerTx }}>
                      Your HR admin has rejected your exception request. For more information, please contact your HR administrator.
                    </p>
                  </div>
                )}

                {/* Just submitted (before page refresh picks up pending status) */}
                {excRequested && exceptionStatus === null && (
                  <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded-lg" style={{ background: C.successBg }}>
                    <CheckCircle2 className="w-4 h-4" style={{ color: C.successTx }} />
                    <p className="text-xs font-semibold" style={{ color: C.successTx }}>Exception request submitted. Your employer will review it shortly.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-3 space-y-5">
            {/* Coverage Level Selector */}
            <div className="rounded-2xl border p-5" style={{ background: C.surface, borderColor: C.border }} data-testid="tier-selector-card">
              <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-4" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                Coverage Level
              </h3>
              <div className="space-y-1.5">
                {Object.entries(TIER_LABELS).map(([value, label]) => (
                  <button
                    key={value}
                    onClick={() => setSelectedTier(value)}
                    className="w-full text-left px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200"
                    style={{
                      background: selectedTier === value ? C.secondary : 'transparent',
                      color: selectedTier === value ? C.primary : C.muted,
                      fontWeight: selectedTier === value ? 600 : 400,
                      border: selectedTier === value ? `1.5px solid ${C.primary}` : '1.5px solid transparent',
                    }}
                    data-testid={`tier-${value}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Plan Summary */}
            {selectedPlan && (
              <div className="rounded-2xl border p-5" style={{ background: C.secondary, borderColor: C.primary }}>
                <h3 className="text-xs font-bold uppercase tracking-[0.15em] mb-3" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>
                  Selected Plan
                </h3>
                <p className="text-sm font-bold mb-1" style={{ color: C.primary }}>{selectedPlan.plan_name}</p>
                <p className="text-3xl font-bold tabular-nums" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>
                  ${(selectedPlan.employee_cost?.[selectedTier] || 0).toFixed(0)}
                  <span className="text-sm font-normal" style={{ color: C.muted }}>/mo</span>
                </p>
              </div>
            )}

            {/* Decline Button */}
            <button
              onClick={() => setShowDecline(true)}
              disabled={!canEnroll}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: canEnroll ? C.dangerBg : '#f3f4f6', color: canEnroll ? C.dangerTx : '#9CA3AF', border: `1px solid ${canEnroll ? '#FECACA' : '#E5E7EB'}` }}
              data-testid="decline-btn"
            >
              {canEnroll ? <XCircle className="w-4 h-4" /> : <Lock className="w-4 h-4" />} Decline All Coverage
            </button>
          </div>

          {/* ── Main: Plans ── */}
          <div className="lg:col-span-9 space-y-5">
            {/* Medical Plans */}
            {data?.medical_plans?.length > 0 ? (
              <>
                <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                  Medical Plans
                </h3>
                <div className="space-y-3">
                  {data.medical_plans.map(plan => {
                    const isSelected = selectedPlan?.id === plan.id;
                    const isExpanded = expandedPlan === plan.id;
                    const eeCost = plan.employee_cost?.[selectedTier] || plan.employee_cost?.self_only || 0;
                    const erCost = plan.employer_contribution?.[selectedTier] || plan.employer_contribution?.self_only || 0;

                    return (
                      <div
                        key={plan.id}
                        className="rounded-2xl border-2 transition-all duration-200 overflow-hidden"
                        style={{
                          background: isSelected ? '#FAFDF9' : C.surface,
                          borderColor: isSelected ? C.primary : C.border,
                          boxShadow: isSelected ? '0 4px 12px rgba(28,59,53,0.08)' : 'none',
                        }}
                        data-testid={`plan-option-${plan.id}`}
                      >
                        <div className="p-5 cursor-pointer" onClick={() => setSelectedPlan(plan)}>
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2.5 mb-1">
                                <div className="w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-200"
                                  style={{ borderColor: isSelected ? C.primary : C.border, background: isSelected ? C.primary : 'transparent' }}>
                                  {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                                </div>
                                <h4 className="text-base font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{plan.plan_name}</h4>
                                <Badge className="rounded-full text-[10px] font-semibold px-2" style={{ background: '#F3F4F6', color: C.muted, border: 'none' }}>{plan.plan_type}</Badge>
                                {plan.mec_qualified && <Badge className="rounded-full text-[10px] font-semibold px-2" style={{ background: '#DBEAFE', color: '#1E40AF', border: 'none' }}>MEC</Badge>}
                                {(() => {
                                  const erC = plan.employer_contribution?.self_only || 0;
                                  const tP = plan.premiums?.self_only || 0;
                                  const eP = tP > 0 ? (erC / tP * 100) : 0;
                                  const passes = (plan.mv_percentage || 0) >= 60 && eP >= 60;
                                  if (plan.mv_certified || plan.mv_percentage) {
                                    return <Badge className="rounded-full text-[10px] font-semibold px-2" style={{ background: passes ? C.successBg : C.warnBg, color: passes ? C.successTx : C.warnTx, border: 'none' }}>MV {plan.mv_percentage}%{!passes ? ' (Fail)' : ''}</Badge>;
                                  }
                                  return null;
                                })()}
                              </div>
                              <p className="text-xs ml-8" style={{ color: C.muted }}>{plan.carrier_name}</p>

                              <div className="grid grid-cols-4 gap-3 mt-3 ml-8 text-xs">
                                <span style={{ color: C.muted }}><Shield className="w-3 h-3 inline mr-1" />Ded: <strong>${(plan.individual_deductible || 0).toLocaleString()}</strong></span>
                                <span style={{ color: C.muted }}><Stethoscope className="w-3 h-3 inline mr-1" />PCP: <strong>${plan.copay_primary}</strong></span>
                                <span style={{ color: C.muted }}><Pill className="w-3 h-3 inline mr-1" />Rx: <strong>${plan.copay_generic_rx}</strong></span>
                                <span style={{ color: C.muted }}><DollarSign className="w-3 h-3 inline mr-1" />OOP: <strong>${(plan.oop_max_individual || 0).toLocaleString()}</strong></span>
                              </div>
                            </div>

                            <div className="text-right ml-6 flex-shrink-0">
                              <p className="text-2xl font-bold tabular-nums" style={{ color: C.primary, fontFamily: "'Manrope', sans-serif" }}>${eeCost.toFixed(0)}</p>
                              <p className="text-[10px]" style={{ color: C.muted }}>/month (your cost)</p>
                              <p className="text-[10px] mt-0.5" style={{ color: C.successTx }}>Employer pays ${erCost.toFixed(0)}</p>
                            </div>
                          </div>
                        </div>

                        <div style={{ borderTop: `1px solid ${C.border}` }}>
                          <button
                            onClick={(e) => { e.stopPropagation(); setExpandedPlan(isExpanded ? null : plan.id); }}
                            className="w-full px-5 py-2 text-xs flex items-center justify-center gap-1 transition-colors duration-200 hover:bg-gray-50"
                            style={{ color: C.muted }}
                            data-testid={`expand-plan-${plan.id}`}
                          >
                            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            {isExpanded ? 'Hide Details' : 'View Full Benefits'}
                          </button>
                          {isExpanded && (
                            <div className="px-5 pb-5 pt-1" style={{ borderTop: `1px solid ${C.border}` }}>
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
                                <ExpandSection title="Deductibles">
                                  <BenefitLine label="Individual" value={`$${(plan.individual_deductible || 0).toLocaleString()}`} />
                                  <BenefitLine label="Family" value={`$${(plan.family_deductible || 0).toLocaleString()}`} />
                                </ExpandSection>
                                <ExpandSection title="Out-of-Pocket Max">
                                  <BenefitLine label="Individual" value={`$${(plan.oop_max_individual || 0).toLocaleString()}`} />
                                  <BenefitLine label="Family" value={`$${(plan.oop_max_family || 0).toLocaleString()}`} />
                                </ExpandSection>
                                <ExpandSection title="Coinsurance">
                                  <BenefitLine label="You pay" value={`${plan.coinsurance_rate || 0}%`} />
                                  <BenefitLine label="Plan pays" value={`${100 - (plan.coinsurance_rate || 0)}%`} />
                                </ExpandSection>
                                <ExpandSection title="Doctor Visits">
                                  <BenefitLine label="Primary Care" value={`$${plan.copay_primary || 0}`} />
                                  <BenefitLine label="Specialist" value={`$${plan.copay_specialist || 0}`} />
                                  <BenefitLine label="Emergency" value={`$${plan.copay_er || 0}`} />
                                </ExpandSection>
                                <ExpandSection title="Prescriptions">
                                  <BenefitLine label="Generic" value={`$${plan.copay_generic_rx || 0}`} />
                                  <BenefitLine label="Brand" value={`$${plan.copay_brand_rx || 0}`} />
                                </ExpandSection>
                                <ExpandSection title="All Tiers">
                                  {Object.entries(TIER_LABELS).map(([k, l]) => (
                                    <BenefitLine key={k} label={l} value={`$${(plan.employee_cost?.[k] || 0).toFixed(0)}/mo`} highlight={k === selectedTier} />
                                  ))}
                                </ExpandSection>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="rounded-2xl border-2 border-dashed p-12 text-center" style={{ borderColor: C.border }}>
                <Shield className="w-10 h-10 mx-auto mb-3" style={{ color: '#D1D5DB' }} />
                <h3 className="text-base font-semibold" style={{ color: C.text }}>No Plans Available</h3>
                <p className="text-sm mt-1" style={{ color: C.muted }}>Your employer hasn't configured plans yet.</p>
              </div>
            )}

            {/* Add-ons */}
            {data?.addon_plans?.length > 0 && (
              <>
                <h3 className="text-xs font-bold uppercase tracking-[0.15em] mt-3" style={{ color: C.muted, fontFamily: "'Manrope', sans-serif" }}>
                  Add-On Benefits
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {data.addon_plans.map(plan => {
                    const isAdded = selectedAddOns.includes(plan.id);
                    const eeCost = plan.employee_cost?.self_only || 0;
                    return (
                      <div
                        key={plan.id}
                        onClick={() => toggleAddOn(plan.id)}
                        className="rounded-2xl border-2 cursor-pointer p-4 flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5"
                        style={{
                          background: isAdded ? '#FAFDF9' : C.surface,
                          borderColor: isAdded ? C.primary : C.border,
                        }}
                        data-testid={`addon-${plan.id}`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-5 h-5 rounded border-2 flex items-center justify-center"
                            style={{ borderColor: isAdded ? C.primary : C.border, background: isAdded ? C.primary : 'transparent' }}>
                            {isAdded && <CheckCircle2 className="w-3 h-3 text-white" />}
                          </div>
                          <div>
                            <p className="text-sm font-semibold" style={{ color: C.text }}>{plan.plan_name}</p>
                            <p className="text-[10px] capitalize" style={{ color: C.muted }}>{plan.category} · {plan.carrier_name}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-base font-bold tabular-nums" style={{ color: C.primary }}>${eeCost.toFixed(0)}</p>
                          <p className="text-[10px]" style={{ color: C.muted }}>/month</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {/* Enroll Button */}
            <div className="pt-3">
              <button
                onClick={handleEnroll}
                disabled={!selectedPlan || submitting || !canEnroll}
                className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl text-base font-semibold transition-all duration-200 hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: canEnroll ? C.primary : C.muted, color: '#fff' }}
                data-testid="enroll-btn"
              >
                {!canEnroll ? <><Lock className="w-5 h-5" /> Enrollment Closed</> :
                  submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 className="w-5 h-5" />}
                {canEnroll && (selectedPlan ? `Enroll in ${selectedPlan.plan_name}` : 'Select a Plan to Enroll')}
                {canEnroll && selectedPlan && <span className="ml-1 tabular-nums">${(selectedPlan.employee_cost?.[selectedTier] || 0).toFixed(0)}/mo</span>}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Decline Dialog */}
      <Dialog open={showDecline} onOpenChange={setShowDecline}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "'Manrope', sans-serif", color: C.text }}>Decline Coverage</DialogTitle>
            <DialogDescription className="text-xs" style={{ color: C.muted }}>
              Please tell us why you're declining. This is required for ACA compliance.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Select value={declineReason} onValueChange={setDeclineReason}>
              <SelectTrigger className="h-10 text-sm rounded-xl" data-testid="decline-reason-select">
                <SelectValue placeholder="Select a reason" />
              </SelectTrigger>
              <SelectContent>
                {data?.decline_reasons?.map(r => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {declineReason === 'other' && (
              <Textarea
                value={declineDetail} onChange={e => setDeclineDetail(e.target.value)}
                placeholder="Please explain..." className="text-sm min-h-[80px] rounded-xl"
                data-testid="decline-detail-input"
              />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDecline(false)} className="h-10 text-sm rounded-xl">Cancel</Button>
            <button
              onClick={handleDecline} disabled={!declineReason || submitting}
              className="h-10 px-6 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
              style={{ background: C.dangerTx, color: '#fff' }}
              data-testid="confirm-decline-btn"
            >
              Decline Coverage
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ── Sub-components ── */

function StatCard({ icon: Icon, label, value, accent, sub }) {
  return (
    <div className="rounded-2xl border p-5 shadow-sm" style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" style={{ color: accent }} />
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: '#4B5563' }}>{label}</span>
      </div>
      <p className="text-2xl font-bold tabular-nums" style={{ color: accent, fontFamily: "'Manrope', sans-serif" }}>{value}</p>
      {sub && <p className="text-[11px] mt-0.5" style={{ color: '#4B5563' }}>{sub}</p>}
    </div>
  );
}

function ProfileRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <Icon className="w-4 h-4 flex-shrink-0" style={{ color: '#9CA3AF' }} />
      <span style={{ color: '#4B5563' }}>{label}</span>
      <span className="ml-auto font-medium capitalize" style={{ color: '#111827' }}>{value}</span>
    </div>
  );
}

function BentoStat({ label, sub, value }) {
  return (
    <div className="rounded-xl p-3.5 text-center" style={{ background: '#F9F9F8' }}>
      <p className="text-lg font-bold tabular-nums" style={{ color: '#111827', fontFamily: "'Manrope', sans-serif" }}>{value}</p>
      <p className="text-[10px] font-medium" style={{ color: '#4B5563' }}>{label}</p>
      {sub && <p className="text-[9px]" style={{ color: '#9CA3AF' }}>{sub}</p>}
    </div>
  );
}

function BenefitLine({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-xs">
      <span style={{ color: highlight ? '#1C3B35' : '#4B5563', fontWeight: highlight ? 600 : 400 }}>{label}</span>
      <span className="tabular-nums font-medium" style={{ color: highlight ? '#1C3B35' : '#111827' }}>{value}</span>
    </div>
  );
}

function ExpandSection({ title, children }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-2" style={{ color: '#4B5563' }}>{title}</p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}
