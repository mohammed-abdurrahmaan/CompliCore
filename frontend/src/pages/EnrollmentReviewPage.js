import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import {
  CheckCircle2, XCircle, Users, UserCheck, UserX, Clock, Loader2, Shield, DollarSign, FileBarChart, AlertTriangle, ThumbsUp, Copy, Key, Download, Send, FileSpreadsheet, RefreshCw,
  CalendarDays, CalendarPlus, Play, Square, Trash2, Timer, Lock, Unlock
} from 'lucide-react';

export default function EnrollmentReviewPage() {
  const { token, API, selectedEmployer } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [review, setReview] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [employerCode, setEmployerCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [runningEngine, setRunningEngine] = useState(false);
  const [tab, setTab] = useState('eligibility');
  const [payrollSummary, setPayrollSummary] = useState(null);
  const [payrollExporting, setPayrollExporting] = useState(false);
  const [payrollDone, setPayrollDone] = useState(false);
  const [carrierExporting, setCarrierExporting] = useState(false);
  const employerId = selectedEmployer?.id;

  // Enrollment Period state
  const [periods, setPeriods] = useState([]);
  const [exceptions, setExceptions] = useState([]);
  const [showNewPeriod, setShowNewPeriod] = useState(false);
  const [newPeriod, setNewPeriod] = useState({ period_name: 'Open Enrollment 2026', start_date: '', end_date: '' });

  const loadData = useCallback(async () => {
    if (!employerId) return;
    setLoading(true);
    try {
      const [eligRes, revRes] = await Promise.all([
        axios.get(`${API}/enrollment/eligibility/${employerId}`, { headers }),
        axios.get(`${API}/enrollment/review/${employerId}`, { headers }),
      ]);
      setEligibility(eligRes.data);
      setReview(revRes.data);
      try {
        const codeRes = await axios.get(`${API}/enrollment/employer-code/${employerId}`, { headers });
        setEmployerCode(codeRes.data.access_code);
      } catch (e) {}
      try {
        const psRes = await axios.get(`${API}/enrollment/payroll-summary/${employerId}`, { headers });
        setPayrollSummary(psRes.data);
      } catch (e) {}
      try {
        const [perRes, excRes] = await Promise.all([
          axios.get(`${API}/enrollment/periods/${employerId}`, { headers }),
          axios.get(`${API}/enrollment/exceptions/${employerId}`, { headers }),
        ]);
        setPeriods(perRes.data);
        setExceptions(excRes.data);
      } catch (e) {}
    } catch (err) { console.error(err); }
    setLoading(false);
  }, [API, token, employerId]);

  useEffect(() => { loadData(); }, [loadData]);

  const runEngine = async () => {
    setRunningEngine(true);
    try {
      const res = await axios.post(`${API}/enrollment/eligibility/run/${employerId}`, {}, { headers });
      toast.success(`Eligibility calculated: ${res.data.eligible} eligible, ${res.data.ineligible} ineligible`);
      setEligibility(res.data);
      loadData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Engine failed'); }
    setRunningEngine(false);
  };

  const approveAll = async () => {
    try {
      const res = await axios.post(`${API}/enrollment/review/${employerId}/approve-all`, {}, { headers });
      toast.success(`Approved ${res.data.approved_count} enrollments`);
      loadData();
    } catch (err) { toast.error('Approval failed'); }
  };

  const approveSingle = async (enrollmentId) => {
    try {
      await axios.put(`${API}/enrollment/review/${employerId}/approve/${enrollmentId}`, {}, { headers });
      toast.success('Approved');
      loadData();
    } catch (err) { toast.error('Approval failed'); }
  };

  const downloadFile = async (url, filename) => {
    try {
      const res = await fetch(`${API}${url}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Download failed'); }
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) { toast.error(err.message || 'Download failed'); }
  };

  const exportPayroll = async () => {
    setPayrollExporting(true);
    try {
      await downloadFile(`/enrollment/payroll-export/${employerId}`, `payroll_deductions.xlsx`);
      setPayrollDone(true);
      toast.success('Payroll deduction file ready!');
      setTimeout(() => setPayrollDone(false), 5000);
    } catch (err) { toast.error('Export failed'); }
    setPayrollExporting(false);
  };

  const exportCarrierCensus = async (carrier = '') => {
    setCarrierExporting(true);
    try {
      const query = carrier ? `?carrier=${encodeURIComponent(carrier)}` : '';
      await downloadFile(`/enrollment/carrier-export/${employerId}${query}`, `carrier_census.xlsx`);
      toast.success('Carrier census downloaded!');
    } catch (err) { toast.error('Export failed'); }
    setCarrierExporting(false);
  };

  if (!employerId) {
    return (
      <div className="p-6 max-w-7xl mx-auto" data-testid="enrollment-review-page">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Enrollment Review</h1>
        <Card className="border-0 shadow-sm mt-4"><CardContent className="p-10 text-center"><p className="text-sm text-muted-foreground">Select an employer first</p></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="enrollment-review-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Enrollment Review</h1>
          <p className="text-sm text-muted-foreground mt-1">Run eligibility engine and review employee enrollments</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={runEngine} disabled={runningEngine} variant="outline" className="h-9 text-sm" data-testid="run-engine-btn">
            {runningEngine ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileBarChart className="w-4 h-4 mr-2" />}
            Run Eligibility Engine
          </Button>
          {review?.pending_approval > 0 && (
            <Button onClick={approveAll} className="h-9 text-sm" data-testid="approve-all-btn">
              <ThumbsUp className="w-4 h-4 mr-2" /> Approve All ({review.pending_approval})
            </Button>
          )}
        </div>
      </div>

      {/* Employer Access Code */}
      {employerCode && (
        <Card className="border-0 shadow-sm mb-5 overflow-hidden" data-testid="employer-code-card">
          <div className="h-1 bg-gradient-to-r from-blue-500 to-cyan-500" />
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center"><Key className="w-4 h-4 text-blue-600" /></div>
              <div>
                <p className="text-xs font-bold">Employee Registration Code</p>
                <p className="text-[10px] text-muted-foreground">Share this code with employees for self-registration</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <code className="bg-slate-50 px-4 py-2 rounded-lg border border-slate-200 text-base font-mono font-bold tracking-[0.3em] text-slate-800" data-testid="employer-code-display">{employerCode}</code>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => { navigator.clipboard.writeText(employerCode); toast.success('Code copied'); }} data-testid="copy-code-btn"><Copy className="w-4 h-4" /></Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-slate-100/80 p-1 rounded-xl w-fit" data-testid="review-tabs">
        <button onClick={() => setTab('eligibility')} className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${tab === 'eligibility' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`} data-testid="tab-eligibility">
          <Shield className="w-3.5 h-3.5 inline mr-1.5" /> Eligibility
        </button>
        <button onClick={() => setTab('enrollments')} className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${tab === 'enrollments' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`} data-testid="tab-enrollments">
          <Users className="w-3.5 h-3.5 inline mr-1.5" /> Enrollments
          {review?.total_enrollments > 0 && <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full bg-indigo-600 text-white">{review.total_enrollments}</span>}
        </button>
        <button onClick={() => setTab('periods')} className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${tab === 'periods' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`} data-testid="tab-periods">
          <CalendarDays className="w-3.5 h-3.5 inline mr-1.5" /> Enrollment Periods
          {periods.filter(p => p.status === 'active').length > 0 && <span className="ml-1.5 inline-flex items-center justify-center w-2 h-2 rounded-full bg-emerald-500" />}
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          {tab === 'eligibility' && (
            <div className="space-y-5">
              {eligibility && eligibility.total > 0 && (
                <div className="grid grid-cols-3 gap-4">
                  <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
                    <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total Employees</p><p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{eligibility.total}</p></div><div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center"><Users className="w-5 h-5 text-slate-600" /></div></div></CardContent>
                  </Card>
                  <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm">
                    <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">Eligible</p><p className="text-3xl font-bold tabular-nums text-emerald-900 mt-1">{eligibility.eligible}</p></div><div className="w-10 h-10 rounded-xl bg-emerald-200/70 flex items-center justify-center"><UserCheck className="w-5 h-5 text-emerald-600" /></div></div></CardContent>
                  </Card>
                  <Card className="border-0 bg-gradient-to-br from-rose-50 to-rose-100/80 shadow-sm">
                    <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-rose-500 uppercase tracking-wider font-semibold">Ineligible</p><p className="text-3xl font-bold tabular-nums text-rose-900 mt-1">{eligibility.ineligible}</p></div><div className="w-10 h-10 rounded-xl bg-rose-200/70 flex items-center justify-center"><UserX className="w-5 h-5 text-rose-600" /></div></div></CardContent>
                  </Card>
                </div>
              )}

              {eligibility?.results?.length > 0 ? (
                <Card className="border-0 shadow-sm overflow-hidden">
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 z-10">
                          <tr className="bg-slate-50 border-b border-slate-200">
                            <th className="text-left py-2.5 px-4 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Employee</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Hours/Wk</th>
                            <th className="text-right py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Salary</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Offer Code</th>
                          </tr>
                        </thead>
                        <tbody>
                          {eligibility.results.map((r, idx) => (
                            <tr key={r.employee_id} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                              <td className="py-2 px-4">
                                <div className="flex items-center gap-2.5">
                                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white ${r.eligible ? 'bg-emerald-500' : 'bg-slate-400'}`}>{r.employee_name?.charAt(0)}</div>
                                  <span className="font-semibold text-slate-800">{r.employee_name}</span>
                                </div>
                              </td>
                              <td className="py-2 px-3 text-center">
                                {r.eligible ? (
                                  <Badge className="bg-emerald-100 text-emerald-800 border-0 text-[10px] font-semibold"><CheckCircle2 className="w-3 h-3 mr-0.5" /> Eligible</Badge>
                                ) : (
                                  <Badge className="bg-slate-100 text-slate-500 border-0 text-[10px] font-semibold"><XCircle className="w-3 h-3 mr-0.5" /> Ineligible</Badge>
                                )}
                              </td>
                              <td className="py-2 px-3 text-center"><span className="tabular-nums font-semibold text-slate-700">{r.weekly_hours}<span className="text-slate-400 font-normal ml-0.5">h</span></span></td>
                              <td className="py-2 px-3 text-right tabular-nums font-semibold text-slate-700">${r.annual_salary?.toLocaleString()}</td>
                              <td className="py-2 px-3 text-center">
                                <Badge variant="outline" className={`text-[10px] tabular-nums font-bold ${r.offer_code === '1H' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'border-slate-200'}`}>{r.offer_code}</Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="border-0 shadow-sm border-dashed">
                  <CardContent className="p-12 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Shield className="w-7 h-7 text-indigo-500" /></div>
                    <h3 className="text-base font-bold font-[Manrope]">No Eligibility Data</h3>
                    <p className="text-sm text-muted-foreground mt-1">Click "Run Eligibility Engine" to calculate employee eligibility</p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {tab === 'enrollments' && (
            <div className="space-y-5">
              {review && review.total_enrollments > 0 ? (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total</p><p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{review.total_enrollments}</p></div><div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center"><Users className="w-5 h-5 text-slate-600" /></div></div></CardContent></Card>
                    <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">Enrolled</p><p className="text-3xl font-bold tabular-nums text-emerald-900 mt-1">{review.enrolled}</p></div><div className="w-10 h-10 rounded-xl bg-emerald-200/70 flex items-center justify-center"><UserCheck className="w-5 h-5 text-emerald-600" /></div></div></CardContent></Card>
                    <Card className="border-0 bg-gradient-to-br from-rose-50 to-rose-100/80 shadow-sm"><CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-rose-500 uppercase tracking-wider font-semibold">Declined</p><p className="text-3xl font-bold tabular-nums text-rose-900 mt-1">{review.declined}</p></div><div className="w-10 h-10 rounded-xl bg-rose-200/70 flex items-center justify-center"><XCircle className="w-5 h-5 text-rose-600" /></div></div></CardContent></Card>
                  </div>

                  {/* Action Bar: Send to Payroll + Export to Carrier + IRS Codes */}
                  <div className="grid grid-cols-3 gap-3">
                    {/* Step 1: Send to Payroll */}
                    <Card className="border-0 shadow-sm overflow-hidden" data-testid="payroll-action-card">
                      <div className="h-1 bg-gradient-to-r from-red-500 to-red-600" />
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center"><Send className="w-3.5 h-3.5 text-red-600" /></div>
                          <h4 className="text-xs font-bold">Send to Payroll</h4>
                        </div>
                        {payrollSummary?.enrolled_count > 0 ? (
                          <div className="space-y-2">
                            <div className="flex justify-between text-[10px]">
                              <span className="text-slate-500">Employee Deductions</span>
                              <span className="font-bold tabular-nums">${payrollSummary.total_ee_deductions?.toLocaleString()}/mo</span>
                            </div>
                            <div className="flex justify-between text-[10px]">
                              <span className="text-slate-500">Employer Contributions</span>
                              <span className="font-bold tabular-nums">${payrollSummary.total_er_contributions?.toLocaleString()}/mo</span>
                            </div>
                            {payrollDone ? (
                              <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-semibold py-1.5"><CheckCircle2 className="w-4 h-4" /> Payroll file ready!</div>
                            ) : (
                              <Button size="sm" className="w-full h-8 text-xs bg-red-600 hover:bg-red-700" onClick={exportPayroll} disabled={payrollExporting} data-testid="send-to-payroll-btn">
                                {payrollExporting ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <Send className="w-3 h-3 mr-1.5" />}
                                Send {payrollSummary.enrolled_count} Deductions → ADP
                              </Button>
                            )}
                          </div>
                        ) : (
                          <p className="text-[10px] text-muted-foreground">No enrolled employees yet</p>
                        )}
                      </CardContent>
                    </Card>

                    {/* Step 2: Export to Insurance Carrier */}
                    <Card className="border-0 shadow-sm overflow-hidden" data-testid="carrier-action-card">
                      <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500" />
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center"><FileSpreadsheet className="w-3.5 h-3.5 text-blue-600" /></div>
                          <h4 className="text-xs font-bold">Send to Insurance</h4>
                        </div>
                        {payrollSummary?.enrolled_count > 0 ? (
                          <div className="space-y-2">
                            <div className="flex justify-between text-[10px]">
                              <span className="text-slate-500">Enrolled Members</span>
                              <span className="font-bold tabular-nums">{payrollSummary.enrolled_count}</span>
                            </div>
                            {payrollSummary.carriers?.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {payrollSummary.carriers.map(c => (
                                  <Badge key={c} variant="outline" className="text-[9px] px-1.5 py-0">{c}</Badge>
                                ))}
                              </div>
                            )}
                            <Button size="sm" variant="outline" className="w-full h-8 text-xs" onClick={() => exportCarrierCensus()} disabled={carrierExporting} data-testid="export-carrier-btn">
                              {carrierExporting ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <Download className="w-3 h-3 mr-1.5" />}
                              Download Carrier Census
                            </Button>
                          </div>
                        ) : (
                          <p className="text-[10px] text-muted-foreground">No enrolled employees yet</p>
                        )}
                      </CardContent>
                    </Card>

                    {/* Step 3: IRS Code Status */}
                    <Card className="border-0 shadow-sm overflow-hidden" data-testid="irs-codes-card">
                      <div className="h-1 bg-gradient-to-r from-emerald-500 to-teal-500" />
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center"><Shield className="w-3.5 h-3.5 text-emerald-600" /></div>
                          <h4 className="text-xs font-bold">IRS Offer Codes</h4>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-[10px]">
                            <span className="text-slate-500">Auto-Updated</span>
                            <Badge className="bg-emerald-100 text-emerald-700 border-0 text-[10px]"><CheckCircle2 className="w-3 h-3 mr-0.5" /> Live</Badge>
                          </div>
                          <p className="text-[10px] text-muted-foreground">Offer codes (1A-1H) auto-update when employees accept or decline coverage. View in IRS Forms.</p>
                          <Button size="sm" variant="outline" className="w-full h-8 text-xs" onClick={() => { window.location.href = '/irs-forms'; }} data-testid="view-irs-btn">
                            <FileBarChart className="w-3 h-3 mr-1.5" /> View IRS Forms
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card className="border-0 shadow-sm overflow-hidden">
                    <CardContent className="p-0">
                      <div className="max-h-[500px] overflow-y-auto">
                        <table className="w-full text-xs">
                          <thead className="sticky top-0 z-10"><tr className="bg-slate-50 border-b border-slate-200">
                            <th className="text-left py-2.5 px-4 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Employee</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                            <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Plan / Reason</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tier</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Approved</th>
                            <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Actions</th>
                          </tr></thead>
                          <tbody>
                            {review.enrollments.filter(e => e.status === 'enrolled' || e.status === 'declined').map((e, idx) => (
                              <tr key={e.id} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                                <td className="py-2 px-4"><p className="font-semibold text-slate-800">{e.employee_name}</p><p className="text-[10px] text-slate-400">{e.employee_email}</p></td>
                                <td className="py-2 px-3 text-center">
                                  {e.status === 'enrolled' ? <Badge className="bg-emerald-100 text-emerald-800 border-0 text-[10px] font-semibold">Enrolled</Badge> : <Badge className="bg-rose-100 text-rose-800 border-0 text-[10px] font-semibold">Declined</Badge>}
                                </td>
                                <td className="py-2 px-3">
                                  {e.status === 'enrolled' ? (
                                    <span className="text-slate-700">{e.plan_name}</span>
                                  ) : (
                                    <span className="text-slate-500 italic text-[10px]">{(e.decline_reason || 'other').replace(/_/g, ' ')}{e.decline_reason_detail ? ` — ${e.decline_reason_detail}` : ''}</span>
                                  )}
                                </td>
                                <td className="py-2 px-3 text-center capitalize text-slate-600">{e.coverage_tier?.replace('_',' ') || '\u2014'}</td>
                                <td className="py-2 px-3 text-center">{e.approved ? <CheckCircle2 className="w-4 h-4 text-emerald-600 mx-auto" /> : <Clock className="w-4 h-4 text-amber-500 mx-auto" />}</td>
                                <td className="py-2 px-3 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    {!e.approved && <Button variant="outline" size="sm" className="h-6 text-[10px] border-indigo-200 text-indigo-700 hover:bg-indigo-50" onClick={() => approveSingle(e.id)} data-testid={`approve-${e.id}`}>Approve</Button>}
                                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0" title="Download proof" onClick={() => {
                                      const link = document.createElement('a');
                                      link.href = `${API}/enrollment/review/${selectedEmployer.id}/proof/${e.id}`;
                                      link.setAttribute('download', '');
                                      const authHeaders = new Headers();
                                      authHeaders.append('Authorization', `Bearer ${token}`);
                                      fetch(link.href, { headers: authHeaders })
                                        .then(r => r.blob())
                                        .then(blob => { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${e.employee_name.replace(/ /g, '_')}_${e.status}_proof.pdf`; a.click(); URL.revokeObjectURL(url); })
                                        .catch(() => toast.error('Failed to download'));
                                    }} data-testid={`download-proof-${e.id}`}>
                                      <Download className="w-3.5 h-3.5 text-slate-500" />
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card className="border-0 shadow-sm">
                  <CardContent className="p-12 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Users className="w-7 h-7 text-indigo-500" /></div>
                    <h3 className="text-base font-bold font-[Manrope]">No Enrollments Yet</h3>
                    <p className="text-sm text-muted-foreground mt-1">Employees will appear here once they make enrollment choices through the portal</p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          {tab === 'periods' && (
            <EnrollmentPeriodsTab
              periods={periods}
              exceptions={exceptions}
              API={API}
              headers={headers}
              employerId={employerId}
              onRefresh={loadData}
              showNewPeriod={showNewPeriod}
              setShowNewPeriod={setShowNewPeriod}
              newPeriod={newPeriod}
              setNewPeriod={setNewPeriod}
            />
          )}
        </>
      )}
    </div>
  );
}


/* ── Enrollment Periods Tab ─────────────────── */
function EnrollmentPeriodsTab({ periods, exceptions, API, headers, employerId, onRefresh, showNewPeriod, setShowNewPeriod, newPeriod, setNewPeriod }) {
  const activePeriod = periods.find(p => p.status === 'active');
  const pendingExc = exceptions.filter(e => e.status === 'pending');

  const createPeriod = async () => {
    if (!newPeriod.start_date || !newPeriod.end_date) { toast.error('Set start and end dates'); return; }
    if (newPeriod.end_date < newPeriod.start_date) { toast.error('End date must be after start date'); return; }
    try {
      await axios.post(`${API}/enrollment/periods`, { ...newPeriod, employer_id: employerId }, { headers });
      toast.success('Enrollment period created');
      setShowNewPeriod(false);
      setNewPeriod({ period_name: 'Open Enrollment 2026', start_date: '', end_date: '' });
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const updateStatus = async (periodId, status) => {
    try {
      await axios.put(`${API}/enrollment/periods/${periodId}`, { status }, { headers });
      toast.success(status === 'active' ? 'Enrollment period activated!' : 'Enrollment period closed');
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const deletePeriod = async (periodId) => {
    try {
      await axios.delete(`${API}/enrollment/periods/${periodId}`, { headers });
      toast.success('Period deleted');
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const reviewException = async (excId, status) => {
    try {
      await axios.put(`${API}/enrollment/exceptions/${excId}`, { status }, { headers });
      toast.success(`Exception ${status}`);
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const daysRemaining = (endDate) => {
    const end = new Date(endDate + 'T23:59:59');
    const now = new Date();
    const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <div className="space-y-5" data-testid="enrollment-periods-tab">
      {/* Active Period Banner */}
      {activePeriod && (
        <Card className="border-0 shadow-sm overflow-hidden" data-testid="active-period-banner">
          <div className="h-1.5 bg-gradient-to-r from-emerald-500 to-teal-500" />
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
                  <Unlock className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="text-base font-bold font-[Manrope]">{activePeriod.period_name}</h3>
                    <Badge className="bg-emerald-100 text-emerald-700 border-0 text-[10px] font-bold">ACTIVE</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {new Date(activePeriod.start_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} — {new Date(activePeriod.end_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-2xl font-bold tabular-nums font-[Manrope] text-emerald-700">{Math.max(0, daysRemaining(activePeriod.end_date))}</p>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Days Left</p>
                </div>
                <Button variant="outline" size="sm" className="h-8 text-xs border-red-200 text-red-600 hover:bg-red-50" onClick={() => updateStatus(activePeriod.id, 'closed')} data-testid="close-period-btn">
                  <Square className="w-3 h-3 mr-1" /> Close Now
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No Active Period */}
      {!activePeriod && (
        <Card className="border-0 shadow-sm overflow-hidden" data-testid="no-active-period">
          <div className="h-1.5 bg-gradient-to-r from-amber-400 to-orange-400" />
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
                  <Lock className="w-6 h-6 text-amber-600" />
                </div>
                <div>
                  <h3 className="text-base font-bold font-[Manrope]">Enrollment Closed</h3>
                  <p className="text-xs text-muted-foreground">No active enrollment window. Employees cannot enroll or change plans.</p>
                </div>
              </div>
              <Button className="h-9 text-sm bg-indigo-600 hover:bg-indigo-700" onClick={() => setShowNewPeriod(true)} data-testid="create-period-btn">
                <CalendarPlus className="w-4 h-4 mr-1.5" /> Create Enrollment Window
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Periods */}
      <Card className="border-0 shadow-sm" data-testid="periods-list">
        <CardHeader className="py-3 px-5 flex-row items-center justify-between">
          <CardTitle className="text-sm font-bold font-[Manrope]">All Enrollment Periods</CardTitle>
          {activePeriod && (
            <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => setShowNewPeriod(true)} data-testid="add-period-btn">
              <CalendarPlus className="w-3 h-3 mr-1" /> New Period
            </Button>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {periods.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-3"><CalendarDays className="w-6 h-6 text-slate-400" /></div>
              <p className="text-sm text-muted-foreground">No enrollment periods configured yet</p>
              <Button className="mt-3 h-8 text-xs bg-indigo-600 hover:bg-indigo-700" onClick={() => setShowNewPeriod(true)} data-testid="first-period-btn">
                <CalendarPlus className="w-3 h-3 mr-1" /> Create First Period
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-border/50">
              {periods.map(p => {
                const isActive = p.status === 'active';
                const isClosed = p.status === 'closed';
                const isDraft = p.status === 'draft';
                const days = isActive ? Math.max(0, daysRemaining(p.end_date)) : null;
                return (
                  <div key={p.id} className="px-5 py-3 flex items-center justify-between hover:bg-muted/30 transition" data-testid={`period-row-${p.id}`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? 'bg-emerald-100' : isClosed ? 'bg-slate-100' : 'bg-amber-100'}`}>
                        {isActive ? <Unlock className="w-4 h-4 text-emerald-600" /> : isClosed ? <Lock className="w-4 h-4 text-slate-500" /> : <Timer className="w-4 h-4 text-amber-600" />}
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{p.period_name}</p>
                        <p className="text-[10px] text-muted-foreground">
                          {new Date(p.start_date).toLocaleDateString()} — {new Date(p.end_date).toLocaleDateString()}
                          {days !== null && <span className="ml-2 text-emerald-600 font-bold">({days}d left)</span>}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`text-[10px] font-bold border-0 ${isActive ? 'bg-emerald-100 text-emerald-700' : isClosed ? 'bg-slate-100 text-slate-600' : 'bg-amber-100 text-amber-700'}`}>
                        {p.status.toUpperCase()}
                      </Badge>
                      {isDraft && (
                        <>
                          <Button variant="outline" size="sm" className="h-7 text-[10px] border-emerald-200 text-emerald-700 hover:bg-emerald-50" onClick={() => updateStatus(p.id, 'active')} data-testid={`activate-${p.id}`}>
                            <Play className="w-3 h-3 mr-1" /> Activate
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500 hover:bg-red-50" onClick={() => deletePeriod(p.id)} data-testid={`delete-${p.id}`}>
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </>
                      )}
                      {isActive && (
                        <Button variant="outline" size="sm" className="h-7 text-[10px] border-red-200 text-red-600 hover:bg-red-50" onClick={() => updateStatus(p.id, 'closed')} data-testid={`close-${p.id}`}>
                          <Square className="w-3 h-3 mr-1" /> Close
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exception Requests */}
      <Card className="border-0 shadow-sm" data-testid="exceptions-list">
        <CardHeader className="py-3 px-5">
          <CardTitle className="text-sm font-bold font-[Manrope] flex items-center gap-2">
            Exception Requests
            {pendingExc.length > 0 && <Badge className="bg-amber-100 text-amber-700 border-0 text-[10px] font-bold">{pendingExc.length} Pending</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {exceptions.length === 0 ? (
            <div className="px-5 py-8 text-center">
              <p className="text-sm text-muted-foreground">No exception requests from employees</p>
            </div>
          ) : (
            <div className="divide-y divide-border/50">
              {exceptions.map(e => (
                <div key={e.id} className="px-5 py-3 flex items-center justify-between" data-testid={`exception-row-${e.id}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${e.status === 'pending' ? 'bg-amber-100' : e.status === 'approved' ? 'bg-emerald-100' : 'bg-red-100'}`}>
                      {e.status === 'pending' ? <Clock className="w-4 h-4 text-amber-600" /> : e.status === 'approved' ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-red-600" />}
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{e.employee_name}</p>
                      <p className="text-[10px] text-muted-foreground">{e.reason || 'No reason provided'} · {new Date(e.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={`text-[10px] font-bold border-0 ${e.status === 'pending' ? 'bg-amber-100 text-amber-700' : e.status === 'approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {e.status.toUpperCase()}
                    </Badge>
                    {e.status === 'pending' && (
                      <>
                        <Button variant="outline" size="sm" className="h-7 text-[10px] border-emerald-200 text-emerald-700 hover:bg-emerald-50" onClick={() => reviewException(e.id, 'approved')} data-testid={`approve-exc-${e.id}`}>
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Approve
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 text-[10px] border-red-200 text-red-600 hover:bg-red-50" onClick={() => reviewException(e.id, 'rejected')} data-testid={`reject-exc-${e.id}`}>
                          <XCircle className="w-3 h-3 mr-1" /> Reject
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* New Period Dialog */}
      <Dialog open={showNewPeriod} onOpenChange={setShowNewPeriod}>
        <DialogContent className="max-w-md" data-testid="new-period-dialog">
          <DialogHeader>
            <DialogTitle className="font-[Manrope]">Create Enrollment Period</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Period Name</label>
              <Input value={newPeriod.period_name} onChange={e => setNewPeriod(p => ({ ...p, period_name: e.target.value }))} placeholder="Open Enrollment 2026" data-testid="period-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">Start Date</label>
                <Input type="date" value={newPeriod.start_date} onChange={e => setNewPeriod(p => ({ ...p, start_date: e.target.value }))} data-testid="period-start-input" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">End Date</label>
                <Input type="date" value={newPeriod.end_date} onChange={e => setNewPeriod(p => ({ ...p, end_date: e.target.value }))} data-testid="period-end-input" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewPeriod(false)}>Cancel</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={createPeriod} data-testid="save-period-btn">Create Period</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
