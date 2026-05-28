import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Area, ComposedChart, BarChart, Bar, Cell, Legend
} from 'recharts';
import {
  Users, ShieldCheck, FileBarChart, Award, AlertTriangle, CheckCircle2,
  XCircle, ArrowRight, Building2, Plus, UserCheck, Clock, DollarSign, TrendingUp, Zap,
  Brain, Sparkles, Target, BarChart3, Play, Loader2, ChevronRight, Info, TrendingDown, RefreshCw
} from 'lucide-react';

export default function DashboardPage() {
  const { user, selectedEmployer, token, API, employers, createEmployer, setSelectedEmployer } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [actuaryDash, setActuaryDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNewEmployer, setShowNewEmployer] = useState(false);
  const [newEmployer, setNewEmployer] = useState({ name: '', ein: '', payroll_provider: '', hr_system: '', insurance_carrier: '' });
  const navigate = useNavigate();
  const headers = { Authorization: `Bearer ${token}` };

  // Predictive Intelligence state
  const [alerts, setAlerts] = useState(null);
  const [growth, setGrowth] = useState(null);
  const [exposure, setExposure] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [scenarioForm, setScenarioForm] = useState({ add_full_time: 0, add_part_time: 0, remove_full_time: 0, remove_part_time: 0, new_plan_mv_pct: null, change_contribution_pct: null, drop_mec_coverage: false });
  const [scenarioResult, setScenarioResult] = useState(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [piTab, setPiTab] = useState('alerts');

  const loadPredictive = useCallback(async () => {
    if (!selectedEmployer?.id) return;
    try {
      const [aRes, gRes, eRes] = await Promise.all([
        axios.get(`${API}/predictive/alerts/${selectedEmployer.id}`, { headers }),
        axios.get(`${API}/predictive/growth/${selectedEmployer.id}`, { headers }),
        axios.get(`${API}/predictive/exposure/${selectedEmployer.id}`, { headers }),
      ]);
      setAlerts(aRes.data);
      setGrowth(gRes.data);
      setExposure(eRes.data);
    } catch (e) { console.error('Predictive load error', e); }
  }, [API, token, selectedEmployer?.id]);

  useEffect(() => {
    if (user?.role === 'actuary') {
      axios.get(`${API}/dashboard/actuary/overview`, { headers })
        .then(res => { setActuaryDash(res.data); setLoading(false); })
        .catch(() => setLoading(false));
    } else if (selectedEmployer) {
      axios.get(`${API}/dashboard/enhanced/${selectedEmployer.id}`, { headers })
        .then(res => { setDashboard(res.data); setLoading(false); })
        .catch(err => {
          axios.get(`${API}/dashboard/${selectedEmployer.id}`, { headers })
            .then(res => { setDashboard(res.data); setLoading(false); })
            .catch(() => setLoading(false));
        });
      loadPredictive();
    } else {
      setLoading(false);
    }
  }, [selectedEmployer, user]);

  const handleCreateEmployer = async () => {
    if (!newEmployer.name) { toast.error('Company name required'); return; }
    try {
      const emp = await createEmployer(newEmployer);
      setSelectedEmployer(emp);
      toast.success('Employer created');
      setShowNewEmployer(false);
    } catch { toast.error('Failed to create'); }
  };

  const handleAiSummary = async () => {
    // Toggle: if same tab summary is showing, close it
    if (aiSummary?.generated && aiSummary.tab === piTab) {
      setAiSummary(null);
      return;
    }
    setAiLoading(true);
    try {
      const res = await axios.post(`${API}/predictive/ai-summary/${selectedEmployer.id}`, { tab: piTab }, { headers });
      setAiSummary(res.data);
      if (!res.data.generated) toast.error('AI summary unavailable');
    } catch (e) { toast.error('Failed to generate AI summary'); }
    setAiLoading(false);
  };

  const runScenario = async () => {
    setScenarioLoading(true);
    try {
      const res = await axios.post(`${API}/predictive/scenario/${selectedEmployer.id}`, scenarioForm, { headers });
      setScenarioResult(res.data);
    } catch (e) { toast.error('Scenario failed'); }
    setScenarioLoading(false);
  };

  const applyPreset = (preset) => {
    const presets = {
      hire10: { add_full_time: 10, add_part_time: 0, remove_full_time: 0, remove_part_time: 0, new_plan_mv_pct: null, change_contribution_pct: null, drop_mec_coverage: false },
      hire25: { add_full_time: 25, add_part_time: 0, remove_full_time: 0, remove_part_time: 0, new_plan_mv_pct: null, change_contribution_pct: null, drop_mec_coverage: false },
      dropMec: { add_full_time: 0, add_part_time: 0, remove_full_time: 0, remove_part_time: 0, new_plan_mv_pct: null, change_contribution_pct: null, drop_mec_coverage: true },
      lowMv: { add_full_time: 0, add_part_time: 0, remove_full_time: 0, remove_part_time: 0, new_plan_mv_pct: 45, change_contribution_pct: null, drop_mec_coverage: false },
      reduce10: { add_full_time: 0, add_part_time: 0, remove_full_time: 10, remove_part_time: 0, new_plan_mv_pct: null, change_contribution_pct: null, drop_mec_coverage: false },
    };
    setScenarioForm(presets[preset] || presets.hire10);
    setScenarioResult(null);
  };

  // Actuary Dashboard — Organic & Earthy Design System
  if (user?.role === 'actuary') {
    const AC = {
      bg: '#F9F9F8', surface: '#FFFFFF',
      primary: '#1C3B35', primaryH: '#162F2A',
      secondary: '#E3EBE6', secFg: '#1C3B35',
      text: '#111827', muted: '#4B5563', light: '#9CA3AF',
      border: '#E5E7EB',
      warnBg: '#FEF3C7', warnTx: '#92400E',
      blueBg: '#DBEAFE', blueTx: '#1E40AF',
      successBg: '#E8F0EB', successTx: '#1F4D36',
    };
    const totalActive = (actuaryDash?.stats?.pending_count || 0) + (actuaryDash?.stats?.in_review_count || 0);
    const totalAll = totalActive + (actuaryDash?.stats?.completed_count || 0);

    return (
      <div className="min-h-screen" style={{ background: AC.bg, fontFamily: "'Work Sans', sans-serif" }} data-testid="actuary-dashboard">
        {/* Hero Banner */}
        <div className="relative overflow-hidden" style={{ background: AC.primary }}>
          <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")' }} />
          <div className="max-w-6xl mx-auto px-6 md:px-8 py-8 relative">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.45)' }}>Actuary Portal</p>
                <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: "'Manrope', sans-serif" }}>
                  Welcome back, {user?.name?.split(' ')[0] || 'Actuary'}
                </h1>
                <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  Review and certify plan minimum value assessments
                </p>
              </div>
              <div className="flex gap-3">
                {[
                  { label: 'Pending', count: actuaryDash?.stats?.pending_count || 0 },
                  { label: 'In Progress', count: actuaryDash?.stats?.in_review_count || 0 },
                  { label: 'Completed', count: actuaryDash?.stats?.completed_count || 0 },
                ].map(s => (
                  <div key={s.label} className="px-4 py-2 rounded-xl" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.5)' }}>{s.label}</p>
                    <p className="text-xl font-bold text-white tabular-nums" style={{ fontFamily: "'Manrope', sans-serif" }}>{s.count}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-6 md:px-8 py-6 space-y-5">
          {/* Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl border p-5 flex items-center gap-4" style={{ background: AC.surface, borderColor: AC.border }} data-testid="stat-active-requests">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: AC.warnBg }}>
                <Clock className="w-5 h-5" style={{ color: AC.warnTx }} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.15em]" style={{ color: AC.muted }}>Active Requests</p>
                <p className="text-2xl font-bold tabular-nums" style={{ color: AC.text, fontFamily: "'Manrope', sans-serif" }}>{totalActive}</p>
              </div>
            </div>
            <div className="rounded-2xl border p-5 flex items-center gap-4" style={{ background: AC.surface, borderColor: AC.border }} data-testid="stat-completed-certs">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: AC.successBg }}>
                <CheckCircle2 className="w-5 h-5" style={{ color: AC.successTx }} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.15em]" style={{ color: AC.muted }}>Completed</p>
                <p className="text-2xl font-bold tabular-nums" style={{ color: AC.text, fontFamily: "'Manrope', sans-serif" }}>{actuaryDash?.stats?.completed_count || 0}</p>
              </div>
            </div>
            <div className="rounded-2xl border p-5 flex items-center gap-4" style={{ background: AC.surface, borderColor: AC.border }} data-testid="stat-total-certs">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: AC.secondary }}>
                <FileBarChart className="w-5 h-5" style={{ color: AC.primary }} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.15em]" style={{ color: AC.muted }}>Total Lifetime</p>
                <p className="text-2xl font-bold tabular-nums" style={{ color: AC.text, fontFamily: "'Manrope', sans-serif" }}>{totalAll}</p>
              </div>
            </div>
          </div>

          {/* Pending Requests */}
          <ActuaryCertSection
            title="Pending Requests"
            icon={AlertTriangle}
            iconBg={AC.warnBg}
            iconColor={AC.warnTx}
            certs={actuaryDash?.pending_certifications}
            emptyMsg="No pending certification requests"
            emptyIcon={Clock}
            navigate={navigate}
            statusBg={AC.warnBg}
            statusTx={AC.warnTx}
            actionLabel="Review"
            colors={AC}
          />

          {/* In Progress */}
          <ActuaryCertSection
            title="In Progress"
            icon={FileBarChart}
            iconBg={AC.blueBg}
            iconColor={AC.blueTx}
            certs={actuaryDash?.in_review_certifications}
            emptyMsg="No certifications in progress"
            emptyIcon={FileBarChart}
            navigate={navigate}
            statusBg={AC.blueBg}
            statusTx={AC.blueTx}
            actionLabel="Continue"
            colors={AC}
          />

          {/* Completed */}
          <ActuaryCertSection
            title="Completed"
            icon={CheckCircle2}
            iconBg={AC.successBg}
            iconColor={AC.successTx}
            certs={actuaryDash?.completed_certifications}
            emptyMsg="No completed certifications"
            emptyIcon={Award}
            navigate={navigate}
            statusBg={AC.successBg}
            statusTx={AC.successTx}
            actionLabel="View"
            colors={AC}
          />

          {/* Quick Action CTA */}
          <div className="rounded-2xl border-2 p-5 flex items-center justify-between" style={{ background: AC.secondary, borderColor: '#C5D2CA' }} data-testid="marketplace-cta">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: AC.primary }}>
                <Award className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold" style={{ color: AC.text, fontFamily: "'Manrope', sans-serif" }}>Certification Marketplace</h3>
                <p className="text-xs" style={{ color: AC.muted }}>View all requests, upload documents, and deliver certifications</p>
              </div>
            </div>
            <button onClick={() => navigate('/marketplace')}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:shadow-md"
              style={{ background: AC.primary, color: '#fff' }} data-testid="go-to-marketplace-btn">
              Open Marketplace <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // No employer
  if (!selectedEmployer && !loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[80vh]" data-testid="no-employer-view">
        <Card className="max-w-md w-full border-0 shadow-sm">
          <CardContent className="p-6 text-center">
            <Building2 className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <h2 className="text-lg font-bold font-[Manrope] mb-2">Set Up Your Organization</h2>
            <p className="text-sm text-muted-foreground mb-4">Create an employer profile to start ACA compliance tracking</p>
            <Dialog open={showNewEmployer} onOpenChange={setShowNewEmployer}>
              <DialogTrigger asChild><Button className="h-9 text-sm" data-testid="setup-employer-btn"><Plus className="w-4 h-4 mr-1.5" /> Add Employer</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Add Employer</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <div><Label className="text-xs">Company Name *</Label><Input data-testid="setup-employer-name" value={newEmployer.name} onChange={e => setNewEmployer(p => ({...p, name: e.target.value}))} className="h-8 text-sm" /></div>
                  <div><Label className="text-xs">EIN</Label><Input value={newEmployer.ein} onChange={e => setNewEmployer(p => ({...p, ein: e.target.value}))} placeholder="XX-XXXXXXX" className="h-8 text-sm" /></div>
                  <div><Label className="text-xs">Payroll Provider</Label>
                    <Select value={newEmployer.payroll_provider} onValueChange={v => setNewEmployer(p => ({...p, payroll_provider: v}))}>
                      <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Select" /></SelectTrigger>
                      <SelectContent><SelectItem value="ADP">ADP</SelectItem><SelectItem value="Gusto">Gusto</SelectItem><SelectItem value="Paychex">Paychex</SelectItem><SelectItem value="QuickBooks">QuickBooks</SelectItem><SelectItem value="Other">Other</SelectItem></SelectContent>
                    </Select>
                  </div>
                  <div><Label className="text-xs">Insurance Carrier</Label><Input value={newEmployer.insurance_carrier} onChange={e => setNewEmployer(p => ({...p, insurance_carrier: e.target.value}))} placeholder="e.g., Blue Cross" className="h-8 text-sm" /></div>
                  <Button data-testid="setup-employer-submit" onClick={handleCreateEmployer} className="w-full h-8 text-sm">Create Employer</Button>
                </div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </div>
    );
  }

  const wf = dashboard?.workforce || {};
  const comp = dashboard?.compliance || {};
  const elig = dashboard?.eligibility || {};
  const risk = dashboard?.risk_alerts || {};

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="employer-dashboard">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Compliance Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">{selectedEmployer?.name} - ACA compliance overview</p>
        </div>
        {wf.total === 0 && (
          <Button variant="outline" className="h-9 text-sm" onClick={() => navigate('/employees')} data-testid="import-employees-btn">
            <Zap className="w-3.5 h-3.5 mr-1.5" /> Import Employees
          </Button>
        )}
      </div>

      {/* Workforce Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
        <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm hover:-translate-y-0.5 transition-transform duration-200 cursor-pointer" onClick={() => navigate('/employees')} data-testid="stat-total-employees">
          <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total Employees</p><p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{wf.total || 0}</p></div><div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center"><Users className="w-5 h-5 text-slate-600" /></div></div></CardContent>
        </Card>
        <Card className="border-0 bg-gradient-to-br from-indigo-50 to-indigo-100/80 shadow-sm" data-testid="stat-full-time">
          <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-indigo-500 uppercase tracking-wider font-semibold">Full-Time</p><p className="text-3xl font-bold tabular-nums text-indigo-900 mt-1">{wf.full_time || 0}</p></div><div className="w-10 h-10 rounded-xl bg-indigo-200/70 flex items-center justify-center"><UserCheck className="w-5 h-5 text-indigo-600" /></div></div></CardContent>
        </Card>
        <Card className="border-0 bg-gradient-to-br from-violet-50 to-violet-100/80 shadow-sm" data-testid="stat-fte-count">
          <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-violet-500 uppercase tracking-wider font-semibold">FTE Count</p><p className="text-3xl font-bold tabular-nums text-violet-900 mt-1">{wf.total_fte || 0}</p></div><div className="w-10 h-10 rounded-xl bg-violet-200/70 flex items-center justify-center"><TrendingUp className="w-5 h-5 text-violet-600" /></div></div></CardContent>
        </Card>
        <Card className={`border-0 shadow-sm ${wf.is_ale ? 'bg-gradient-to-br from-amber-50 to-amber-100/80' : 'bg-gradient-to-br from-emerald-50 to-emerald-100/80'}`} data-testid="stat-ale-status">
          <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className={`text-[11px] uppercase tracking-wider font-semibold ${wf.is_ale ? 'text-amber-500' : 'text-emerald-500'}`}>ALE Status</p><Badge className={`mt-1.5 text-sm font-bold border-0 ${wf.is_ale ? 'bg-amber-200/70 text-amber-800' : 'bg-emerald-200/70 text-emerald-800'}`}>{wf.is_ale ? 'ALE' : wf.total > 0 ? 'Not ALE' : '-'}</Badge></div><div className={`w-10 h-10 rounded-xl flex items-center justify-center ${wf.is_ale ? 'bg-amber-200/70' : 'bg-emerald-200/70'}`}><Building2 className={`w-5 h-5 ${wf.is_ale ? 'text-amber-600' : 'text-emerald-600'}`} /></div></div></CardContent>
        </Card>
        <Card className={`border-0 shadow-sm ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'bg-gradient-to-br from-emerald-50 to-emerald-100/80' : 'bg-gradient-to-br from-rose-50 to-rose-100/80'}`} data-testid="stat-mec-coverage">
          <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className={`text-[11px] uppercase tracking-wider font-semibold ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>MEC</p><Badge className={`mt-1.5 text-sm font-bold border-0 ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'bg-emerald-200/70 text-emerald-800' : 'bg-rose-200/70 text-rose-800'}`}>{comp.mec_offered || 0}/{comp.mec_total_medical || 0} qualified</Badge></div><div className={`w-10 h-10 rounded-xl flex items-center justify-center ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'bg-emerald-200/70' : 'bg-rose-200/70'}`}><ShieldCheck className={`w-5 h-5 ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'text-emerald-600' : 'text-rose-600'}`} /></div></div></CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* Eligibility */}
        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold">Eligibility Status</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /><span className="text-sm">Eligible</span></div>
                <span className="text-sm font-bold tabular-nums">{elig.eligible || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><Clock className="w-3.5 h-3.5 text-amber-500" /><span className="text-sm">Waiting Period</span></div>
                <span className="text-sm font-bold tabular-nums">{elig.waiting_period || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><XCircle className="w-3.5 h-3.5 text-gray-400" /><span className="text-sm">Not Eligible</span></div>
                <span className="text-sm font-bold tabular-nums">{elig.not_eligible || 0}</span>
              </div>
            </div>
            {wf.total > 0 && (
              <div className="mt-3 pt-3 border-t">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Eligibility Rate</span>
                  <span className="font-semibold tabular-nums">{wf.total > 0 ? Math.round((elig.eligible || 0) / wf.total * 100) : 0}%</span>
                </div>
                <Progress value={wf.total > 0 ? (elig.eligible || 0) / wf.total * 100 : 0} className="h-1.5" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Compliance Status */}
        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-blue-400 to-indigo-400" />
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold">Compliance Checks</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-2.5">
            <div className={`p-2 rounded-md flex items-center justify-between ${comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? 'bg-emerald-50/50' : comp.mec_total_medical ? 'bg-rose-50/50' : 'bg-gray-50'}`}>
              <div className="flex items-center gap-1.5 text-xs">
                {comp.mec_offered === comp.mec_total_medical && comp.mec_total_medical > 0 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : comp.mec_total_medical ? <XCircle className="w-3.5 h-3.5 text-rose-600" /> : <AlertTriangle className="w-3.5 h-3.5 text-gray-400" />}
                <span className="font-medium">MEC</span>
              </div>
              <span className="text-xs tabular-nums font-semibold">{comp.mec_offered || 0}/{comp.mec_total_medical || 0} qualified</span>
            </div>
            <div className={`p-2 rounded-md flex items-center justify-between ${comp.mv_plans_passing > 0 && comp.mv_plans_failing === 0 ? 'bg-emerald-50/50' : comp.mv_plans_failing > 0 ? 'bg-amber-50/50' : 'bg-gray-50'}`}>
              <div className="flex items-center gap-1.5 text-xs">
                {comp.mv_plans_passing > 0 && comp.mv_plans_failing === 0 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : comp.mv_plans_failing > 0 ? <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> : <AlertTriangle className="w-3.5 h-3.5 text-gray-400" />}
                <span className="font-medium">Minimum Value</span>
              </div>
              <span className="text-xs tabular-nums font-semibold">{comp.mv_plans_passing || 0}/{comp.mv_plans_total || 0} pass</span>
            </div>
            <div className="p-2 rounded-md bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs">
                <DollarSign className="w-3.5 h-3.5 text-gray-500" />
                <span className="font-medium">Affordability</span>
              </div>
              <Button variant="ghost" size="sm" className="h-5 text-[10px] px-1.5" onClick={() => navigate('/affordability')}>Test <ArrowRight className="w-2.5 h-2.5 ml-0.5" /></Button>
            </div>
          </CardContent>
        </Card>

        {/* Risk Alerts */}
        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-rose-400 to-orange-400" />
          <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold">Risk Alerts</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-2.5">
            {(risk.potential_penalty > 0 || risk.penalty_a_amount > 0 || risk.penalty_b_amount > 0) && (
              <div className="p-2 rounded-md bg-rose-50/50 border border-rose-100">
                <div className="flex items-center gap-1.5 text-xs"><AlertTriangle className="w-3.5 h-3.5 text-rose-600" /><span className="font-semibold text-rose-800">Potential Penalty</span></div>
                <p className="text-lg font-bold tabular-nums text-rose-700 ml-5" data-testid="penalty-total-amount">${risk.potential_penalty?.toLocaleString()}</p>
                {risk.penalty_a_amount > 0 && (
                  <div className="ml-5 mt-1 text-[10px] text-rose-600" data-testid="penalty-a-detail">
                    <span className="font-semibold">${risk.penalty_a_amount?.toLocaleString()}</span> — {risk.penalty_a_reason}
                  </div>
                )}
                {risk.penalty_b_amount > 0 && (
                  <div className="ml-5 mt-0.5 text-[10px] text-rose-600" data-testid="penalty-b-detail">
                    <span className="font-semibold">${risk.penalty_b_amount?.toLocaleString()}</span> — {risk.penalty_b_reason}
                  </div>
                )}
              </div>
            )}
            {risk.potential_penalty === 0 && (
              <div className="p-2 rounded-md bg-emerald-50/50 border border-emerald-100" data-testid="no-penalty-alert">
                <div className="flex items-center gap-1.5 text-xs"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /><span className="font-medium text-emerald-800">No Penalties Projected</span></div>
                <p className="text-[10px] text-emerald-600 ml-5">$0 estimated exposure</p>
              </div>
            )}
            <div className="p-2 rounded-md border">
              <div className="flex items-center gap-1.5 text-xs"><Award className="w-3.5 h-3.5 text-muted-foreground" /><span className="font-medium">Pending Certifications</span></div>
              <p className="text-sm font-bold tabular-nums ml-5">{(risk.pending_certifications || 0) + (risk.in_review_certifications || 0)}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Predictive Intelligence Layer */}
      <Card className="border-0 shadow-sm overflow-hidden mb-4" data-testid="predictive-intelligence">
        <div className="h-1.5 bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-500" />
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div>
              <CardTitle className="text-sm font-bold">Predictive Intelligence</CardTitle>
              <p className="text-[10px] text-muted-foreground">AI-powered compliance forecasting & scenario modeling</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={loadPredictive} data-testid="refresh-pi"><RefreshCw className="w-3 h-3 mr-1" />Refresh</Button>
            <Button size="sm" className="h-7 text-[10px] bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700" onClick={handleAiSummary} disabled={aiLoading} data-testid="ai-summary-btn">
              {aiLoading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
              {piTab === 'alerts' ? 'Analyze Risks' : piTab === 'growth' ? 'Analyze Growth' : piTab === 'exposure' ? 'Analyze Costs' : 'Suggest Scenarios'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {/* AI Summary — shown within active tab */}
          {aiSummary?.generated && aiSummary.tab === piTab && (
            <div className="mb-4 rounded-xl border border-cyan-200/60 overflow-hidden shadow-md" data-testid="ai-summary-card">
              <div className="bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 px-5 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-white/15 backdrop-blur flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <span className="text-sm font-bold text-white tracking-wide">
                      {piTab === 'alerts' ? 'Risk Analysis' : piTab === 'growth' ? 'Growth Analysis' : piTab === 'exposure' ? 'Financial Analysis' : 'Scenario Advisor'}
                    </span>
                    <p className="text-[10px] text-cyan-200/80">Powered by CompliCore Intelligence</p>
                  </div>
                </div>
                <button onClick={() => setAiSummary(null)} className="w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/80 hover:text-white transition-all" data-testid="close-ai-summary">
                  <ChevronRight className="w-4 h-4 rotate-90" />
                </button>
              </div>
              <div className="bg-gradient-to-b from-slate-50/80 to-white px-5 py-4">
                <AiSummaryFormatted text={aiSummary.summary} />
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <p className="text-[10px] text-slate-400">
                    Generated {new Date(aiSummary.generated_at).toLocaleString()}
                  </p>
                  <button onClick={() => setAiSummary(null)} className="text-[10px] text-slate-400 hover:text-slate-600 transition-colors">
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* PI Tabs */}
          <div className="flex gap-1 mb-3 bg-slate-100/80 p-0.5 rounded-lg w-fit" data-testid="pi-tabs">
            {[
              { id: 'alerts', label: 'Alerts', icon: AlertTriangle, count: alerts?.total },
              { id: 'growth', label: 'Growth', icon: TrendingUp },
              { id: 'exposure', label: 'Exposure', icon: DollarSign },
              { id: 'scenario', label: 'Scenario', icon: Target },
            ].map(t => (
              <button key={t.id} onClick={() => setPiTab(t.id)}
                className={`px-3 py-1.5 rounded-md text-[10px] font-semibold transition-all flex items-center gap-1 ${piTab === t.id ? 'bg-white shadow-sm text-blue-700' : 'text-slate-500 hover:text-slate-700'}`}
                data-testid={`pi-tab-${t.id}`}>
                <t.icon className="w-3 h-3" /> {t.label}
                {t.count > 0 && <span className="ml-0.5 w-4 h-4 text-[9px] font-bold rounded-full bg-blue-600 text-white flex items-center justify-center">{t.count}</span>}
              </button>
            ))}
          </div>

          {/* ALERTS TAB */}
          {piTab === 'alerts' && alerts && (
            <div className="space-y-2" data-testid="pi-alerts-panel">
              {alerts.alerts.length === 0 ? (
                <div className="flex items-center gap-2 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <p className="text-xs text-emerald-800 font-medium">All clear! No compliance risks detected.</p>
                </div>
              ) : (
                alerts.alerts.map(a => (
                  <div key={a.id} className={`p-3 rounded-lg border ${
                    a.severity === 'critical' ? 'bg-rose-50/80 border-rose-200' :
                    a.severity === 'warning' ? 'bg-amber-50/80 border-amber-200' :
                    a.severity === 'info' ? 'bg-blue-50/80 border-blue-200' : 'bg-slate-50 border-slate-200'
                  }`} data-testid={`alert-${a.id}`}>
                    <div className="flex items-start gap-2">
                      {a.severity === 'critical' ? <XCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" /> :
                       a.severity === 'warning' ? <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" /> :
                       <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-bold text-slate-800">{a.title}</p>
                          <Badge className={`text-[8px] border-0 px-1.5 py-0 ${
                            a.severity === 'critical' ? 'bg-rose-200 text-rose-800' :
                            a.severity === 'warning' ? 'bg-amber-200 text-amber-800' : 'bg-blue-200 text-blue-800'
                          }`}>{a.category}</Badge>
                        </div>
                        <p className="text-[10px] text-slate-600 mt-0.5">{a.detail}</p>
                        <p className="text-[10px] text-blue-700 font-medium mt-1 flex items-center gap-1"><ChevronRight className="w-3 h-3" />{a.action}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* GROWTH TAB */}
          {piTab === 'growth' && growth && (
            <div className="space-y-3" data-testid="pi-growth-panel">
              <div className="grid grid-cols-4 gap-2">
                <div className="p-2.5 rounded-lg bg-slate-50 border text-center">
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">Current</p>
                  <p className="text-lg font-bold tabular-nums">{growth.current.total}</p>
                  <p className="text-[9px] text-slate-400">employees</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border text-center">
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">FTE</p>
                  <p className="text-lg font-bold tabular-nums">{growth.current.total_fte}</p>
                  <p className="text-[9px] text-slate-400">{growth.current.is_ale ? 'ALE' : 'Not ALE'}</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border text-center">
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">Avg Hires/Mo</p>
                  <p className="text-lg font-bold tabular-nums">{growth.avg_monthly_hires}</p>
                  <p className="text-[9px] text-slate-400">{growth.ft_hire_ratio}% FT</p>
                </div>
                <div className={`p-2.5 rounded-lg border text-center ${growth.ale_trigger_month ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">ALE Trigger</p>
                  <p className="text-lg font-bold tabular-nums">{growth.ale_trigger_month || '—'}</p>
                  <p className="text-[9px] text-slate-400">{growth.ale_trigger_month ? 'projected' : 'safe'}</p>
                </div>
              </div>

              {/* Actual vs Projected FTE Line Chart */}
              <GrowthTrendChart growth={growth} />
            </div>
          )}

          {/* EXPOSURE TAB */}
          {piTab === 'exposure' && exposure && (
            <div className="space-y-3" data-testid="pi-exposure-panel">
              <div className="grid grid-cols-3 gap-2">
                <div className={`p-3 rounded-lg border ${exposure.current_exposure.total_penalty_exposure > 0 ? 'bg-rose-50 border-rose-200' : 'bg-emerald-50 border-emerald-200'}`}>
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">Current Exposure</p>
                  <p className={`text-xl font-bold tabular-nums mt-1 ${exposure.current_exposure.total_penalty_exposure > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                    ${exposure.current_exposure.total_penalty_exposure.toLocaleString()}
                  </p>
                  <p className="text-[9px] text-slate-400 mt-0.5">annual penalty risk</p>
                </div>
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">Employer Cost</p>
                  <p className="text-xl font-bold tabular-nums text-blue-700 mt-1">${exposure.premium_costs.annual_employer_cost.toLocaleString()}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5">annual premiums</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border">
                  <p className="text-[9px] text-slate-500 font-semibold uppercase">Worst Case</p>
                  <p className="text-xl font-bold tabular-nums text-slate-700 mt-1">${exposure.worst_case.total_worst_case.toLocaleString()}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5">maximum penalties</p>
                </div>
              </div>

              {/* Penalty Trend Chart */}
              <ExposureTrendChart exposure={exposure} growth={growth} />

              {/* Penalty breakdown */}
              <div className="p-3 rounded-lg bg-slate-50 border">
                <p className="text-[10px] font-bold text-slate-600 mb-2">Penalty Breakdown</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${exposure.current_exposure.penalty_a > 0 ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                      <span className="text-[10px] text-slate-600">4980H(a) — MEC Offer Penalty</span>
                    </div>
                    <span className="text-[10px] font-bold tabular-nums">${exposure.current_exposure.penalty_a.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${exposure.current_exposure.penalty_b > 0 ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                      <span className="text-[10px] text-slate-600">4980H(b) — MV/Subsidy Penalty</span>
                    </div>
                    <span className="text-[10px] font-bold tabular-nums">${exposure.current_exposure.penalty_b.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${exposure.current_exposure.affordability_exposure > 0 ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                      <span className="text-[10px] text-slate-600">Affordability Risk ({exposure.current_exposure.afford_at_risk_count} employees)</span>
                    </div>
                    <span className="text-[10px] font-bold tabular-nums">${exposure.current_exposure.affordability_exposure.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border">
                <p className="text-[10px] font-bold text-slate-600 mb-1">Penalty Rates (2026)</p>
                <div className="flex gap-4 text-[10px] text-slate-500">
                  <span>4980H(a): <span className="font-bold text-slate-700">${exposure.rates.penalty_a_rate.toLocaleString()}</span>/FT/yr</span>
                  <span>4980H(b): <span className="font-bold text-slate-700">${exposure.rates.penalty_b_rate.toLocaleString()}</span>/ee/yr</span>
                  <span>Afford: <span className="font-bold text-slate-700">{exposure.rates.affordability_threshold}%</span> of income</span>
                </div>
              </div>
            </div>
          )}

          {/* SCENARIO TAB */}
          {piTab === 'scenario' && (
            <div className="space-y-3" data-testid="pi-scenario-panel">
              {/* Presets */}
              <div className="flex flex-wrap gap-1.5">
                <span className="text-[10px] text-slate-500 font-semibold mr-1 self-center">Presets:</span>
                {[
                  { id: 'hire10', label: 'Hire 10 FT' },
                  { id: 'hire25', label: 'Hire 25 FT' },
                  { id: 'reduce10', label: 'Reduce 10 FT' },
                  { id: 'dropMec', label: 'Drop MEC' },
                  { id: 'lowMv', label: 'Low MV Plan (45%)' },
                ].map(p => (
                  <Button key={p.id} variant="outline" size="sm" className="h-6 text-[10px] px-2"
                    onClick={() => applyPreset(p.id)} data-testid={`preset-${p.id}`}>{p.label}</Button>
                ))}
              </div>

              {/* Custom form */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                <div>
                  <Label className="text-[10px] text-slate-500">Add FT Employees</Label>
                  <Input type="number" min="0" className="h-7 text-xs" value={scenarioForm.add_full_time}
                    onChange={e => setScenarioForm(f => ({...f, add_full_time: parseInt(e.target.value) || 0}))} />
                </div>
                <div>
                  <Label className="text-[10px] text-slate-500">Add PT Employees</Label>
                  <Input type="number" min="0" className="h-7 text-xs" value={scenarioForm.add_part_time}
                    onChange={e => setScenarioForm(f => ({...f, add_part_time: parseInt(e.target.value) || 0}))} />
                </div>
                <div>
                  <Label className="text-[10px] text-slate-500">Remove FT Employees</Label>
                  <Input type="number" min="0" className="h-7 text-xs" value={scenarioForm.remove_full_time}
                    onChange={e => setScenarioForm(f => ({...f, remove_full_time: parseInt(e.target.value) || 0}))} />
                </div>
                <div>
                  <Label className="text-[10px] text-slate-500">New Plan MV %</Label>
                  <Input type="number" min="0" max="100" placeholder="—" className="h-7 text-xs" value={scenarioForm.new_plan_mv_pct ?? ''}
                    onChange={e => setScenarioForm(f => ({...f, new_plan_mv_pct: e.target.value ? parseFloat(e.target.value) : null}))} />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-[10px] text-slate-600 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-300" checked={scenarioForm.drop_mec_coverage}
                    onChange={e => setScenarioForm(f => ({...f, drop_mec_coverage: e.target.checked}))} />
                  Drop MEC coverage
                </label>
                <Button size="sm" className="h-7 text-[10px] bg-blue-600 hover:bg-blue-700" onClick={runScenario} disabled={scenarioLoading} data-testid="run-scenario-btn">
                  {scenarioLoading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Play className="w-3 h-3 mr-1" />}
                  Run Scenario
                </Button>
              </div>

              {/* Scenario Result */}
              {scenarioResult && (
                <div className="space-y-3" data-testid="scenario-result">
                  {/* Visual Chart Comparison */}
                  <ScenarioComparisonChart result={scenarioResult} />

                  <div className="p-3 rounded-lg border bg-slate-50">
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div>
                        <p className="text-[9px] text-slate-500 font-semibold uppercase mb-1.5">Current State</p>
                        <div className="space-y-1 text-[10px]">
                          <div className="flex justify-between"><span className="text-slate-500">FTE</span><span className="font-bold">{scenarioResult.current.total_fte}</span></div>
                          <div className="flex justify-between"><span className="text-slate-500">ALE</span><Badge className={`text-[8px] border-0 px-1 py-0 ${scenarioResult.current.is_ale ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{scenarioResult.current.is_ale ? 'Yes' : 'No'}</Badge></div>
                          <div className="flex justify-between"><span className="text-slate-500">MEC</span><span className="font-bold">{scenarioResult.current.mec_pct}%</span></div>
                          <div className="flex justify-between"><span className="text-slate-500">Penalty</span><span className="font-bold text-rose-600">${scenarioResult.current.total_penalty.toLocaleString()}</span></div>
                        </div>
                      </div>
                      <div>
                        <p className="text-[9px] text-slate-500 font-semibold uppercase mb-1.5">After Scenario</p>
                        <div className="space-y-1 text-[10px]">
                          <div className="flex justify-between"><span className="text-slate-500">FTE</span><span className="font-bold">{scenarioResult.scenario.total_fte}</span></div>
                          <div className="flex justify-between"><span className="text-slate-500">ALE</span><Badge className={`text-[8px] border-0 px-1 py-0 ${scenarioResult.scenario.is_ale ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{scenarioResult.scenario.is_ale ? 'Yes' : 'No'}</Badge></div>
                          <div className="flex justify-between"><span className="text-slate-500">MEC</span><span className="font-bold">{scenarioResult.scenario.mec_pct}%</span></div>
                          <div className="flex justify-between"><span className="text-slate-500">Penalty</span><span className="font-bold text-rose-600">${scenarioResult.scenario.total_penalty.toLocaleString()}</span></div>
                        </div>
                      </div>
                    </div>

                    {/* Delta summary */}
                    <div className={`p-2 rounded-md border ${scenarioResult.delta.penalty_change > 0 ? 'bg-rose-50 border-rose-200' : scenarioResult.delta.penalty_change < 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50'}`}>
                      <div className="flex items-center gap-2 text-[10px]">
                        {scenarioResult.delta.penalty_change > 0 ? <TrendingUp className="w-3.5 h-3.5 text-rose-600" /> :
                         scenarioResult.delta.penalty_change < 0 ? <TrendingDown className="w-3.5 h-3.5 text-emerald-600" /> :
                         <BarChart3 className="w-3.5 h-3.5 text-slate-500" />}
                        <span className="font-bold">
                          {scenarioResult.delta.penalty_change > 0 ? '+' : ''}{scenarioResult.delta.penalty_change < 0 ? '-' : ''}
                          ${Math.abs(scenarioResult.delta.penalty_change).toLocaleString()} penalty {scenarioResult.delta.penalty_change > 0 ? 'increase' : scenarioResult.delta.penalty_change < 0 ? 'decrease' : 'change'}
                        </span>
                        {scenarioResult.delta.ale_changed && (
                          <Badge className="text-[8px] bg-amber-200 text-amber-800 border-0 px-1.5 py-0">ALE status changed</Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Warnings */}
                  {scenarioResult.warnings.length > 0 && (
                    <div className="space-y-1">
                      {scenarioResult.warnings.map((w, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-[10px] text-amber-700">
                          <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Compliance Workflow CTA */}
      <Card className="border-primary/30 bg-primary/[0.03]">
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">Guided Compliance Workflow</h3>
              <p className="text-xs text-muted-foreground">Step-by-step ACA compliance check for your organization</p>
            </div>
          </div>
          <Button size="sm" className="h-8 text-xs" onClick={() => navigate('/workflow')} data-testid="start-workflow-btn">
            Start Workflow <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

/* ===================== CHART COMPONENTS ===================== */

const ChartTooltipContent = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white/95 backdrop-blur-sm border rounded-lg shadow-lg p-2 text-[10px]">
      <p className="font-bold text-slate-700 mb-1">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color || p.stroke }} />
          <span className="text-slate-500">{p.name}:</span>
          <span className="font-bold">{typeof p.value === 'number' ? (p.value > 999 ? `$${p.value.toLocaleString()}` : p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

function GrowthTrendChart({ growth }) {
  const data = useMemo(() => {
    if (!growth) return [];
    // Build cumulative FTE for history months
    const ftRatio = growth.ft_hire_ratio / 100;
    const baseFte = growth.current.total_fte;
    const baseTotal = growth.current.total;

    // Reverse-compute historical FTE from hires
    let cumulativeHires = 0;
    const historyReversed = [...growth.history].reverse();
    const historyData = historyReversed.map((h) => {
      cumulativeHires += h.hires;
      return { month: h.month, hires: h.hires, cumHires: cumulativeHires };
    }).reverse();

    const points = historyData.map((h) => ({
      month: h.month.slice(2), // "25-04"
      actual: Math.max(1, baseTotal - h.cumHires + h.hires),
      projected: null,
    }));

    // Last history point connects to first projection
    if (points.length > 0) {
      points[points.length - 1].projected = points[points.length - 1].actual;
    }

    // Projection points
    growth.projections.forEach((p) => {
      points.push({
        month: p.month.slice(2),
        actual: null,
        projected: p.projected_total,
        fte: p.projected_fte,
      });
    });

    return points;
  }, [growth]);

  return (
    <div className="p-3 rounded-lg bg-slate-50 border" data-testid="growth-trend-chart">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-bold text-slate-600">Workforce Trend — Actual vs Projected</p>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="flex items-center gap-1.5"><span className="w-5 h-[2.5px] bg-blue-500 inline-block rounded" /> Actual</span>
          <span className="flex items-center gap-1.5"><span className="inline-flex items-center w-5"><span className="w-1 h-[2.5px] bg-blue-500 inline-block rounded" /><span className="w-0.5" /><span className="w-1 h-[2.5px] bg-blue-500 inline-block rounded" /><span className="w-0.5" /><span className="w-1 h-[2.5px] bg-blue-500 inline-block rounded" /></span> Projected</span>
          <span className="flex items-center gap-1.5"><span className="inline-flex items-center w-5"><span className="w-1.5 h-[2px] bg-rose-400 inline-block rounded" /><span className="w-0.5" /><span className="w-1.5 h-[2px] bg-rose-400 inline-block rounded" /></span> ALE (50)</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
          <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltipContent />} />
          <ReferenceLine y={50} stroke="#f43f5e" strokeDasharray="6 3" strokeWidth={1.5} label={{ value: '50 FTE', position: 'right', fontSize: 9, fill: '#f43f5e', fontWeight: 700 }} />
          <Line type="monotone" dataKey="actual" name="Actual" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 3, fill: '#3b82f6', strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls={false} />
          <Line type="monotone" dataKey="projected" name="Projected" stroke="#3b82f6" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3, fill: '#fff', stroke: '#3b82f6', strokeWidth: 2 }} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function ExposureTrendChart({ exposure, growth }) {
  const data = useMemo(() => {
    if (!exposure || !growth) return [];
    const penaltyARate = exposure.rates.penalty_a_rate;
    const currentFt = exposure.workforce.ft_count;
    const mecCovered = exposure.workforce.mec_covered_ft || 0;

    const months = [
      { month: 'Now', ft: currentFt, ale: exposure.workforce.is_ale },
      ...growth.projections.map(p => ({ month: p.month.slice(2), ft: p.projected_ft, ale: p.is_ale }))
    ];

    let cumulative = 0;
    let cumulativeSaved = 0;

    return months.map(({ month, ft, ale }, i) => {
      const mecPct = ft > 0 ? (mecCovered / ft) * 100 : 100;
      const annualPenalty = (mecPct < 95 && ale) ? Math.max(0, ft - 30) * penaltyARate : 0;
      const monthlyPenalty = Math.round(annualPenalty / 12);

      // Cumulative: first point is just the monthly cost, then accumulates
      cumulative += monthlyPenalty;
      cumulativeSaved += monthlyPenalty;

      return {
        month,
        monthly: monthlyPenalty,
        cumulative,
        saved: cumulativeSaved,
      };
    });
  }, [exposure, growth]);

  const maxCum = data.length > 0 ? data[data.length - 1].cumulative : 0;

  return (
    <div className="p-3 rounded-lg bg-slate-50 border" data-testid="exposure-trend-chart">
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-bold text-slate-600">Cost of Non-Compliance Over Time</p>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-rose-400 inline-block" /> Monthly Penalty</span>
          <span className="flex items-center gap-1.5"><span className="w-4 h-[2.5px] bg-slate-700 inline-block rounded" /> Cumulative Loss</span>
        </div>
      </div>
      <p className="text-[9px] text-slate-400 mb-2">How penalties accumulate each month without corrective action</p>
      <ResponsiveContainer width="100%" height={190}>
        <ComposedChart data={data} margin={{ top: 8, right: 10, left: 5, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
          <YAxis yAxisId="bar" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false}
            tickFormatter={v => v >= 1000 ? `$${(v/1000).toFixed(0)}k` : `$${v}`} orientation="left" />
          <YAxis yAxisId="line" tick={{ fontSize: 9, fill: '#64748b' }} tickLine={false} axisLine={false}
            tickFormatter={v => v >= 1000 ? `$${(v/1000).toFixed(0)}k` : `$${v}`} orientation="right" />
          <Tooltip content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="bg-white/95 backdrop-blur-sm border rounded-lg shadow-lg p-2.5 text-[10px]">
                <p className="font-bold text-slate-700 mb-1">{label}</p>
                {payload.map((p, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color || p.stroke || p.fill }} />
                    <span className="text-slate-500">{p.name}:</span>
                    <span className="font-bold">${Number(p.value).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            );
          }} />
          <Bar yAxisId="bar" dataKey="monthly" name="Monthly Penalty" fill="#fb7185" radius={[4, 4, 0, 0]} barSize={32} />
          <Line yAxisId="line" type="monotone" dataKey="cumulative" name="Cumulative Loss" stroke="#1e293b" strokeWidth={2.5}
            dot={{ r: 4, fill: '#1e293b', strokeWidth: 0 }} activeDot={{ r: 6, fill: '#1e293b' }} />
        </ComposedChart>
      </ResponsiveContainer>
      {maxCum > 0 && (
        <div className="mt-2 flex items-center gap-2 p-2 rounded-md bg-rose-50 border border-rose-100">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
          <p className="text-[10px] text-rose-800">
            <span className="font-bold">${maxCum.toLocaleString()}</span> in penalties will accumulate over the next 7 months if MEC coverage stays at {exposure.workforce.mec_pct}%.
            Reaching 95% MEC eliminates this entirely.
          </p>
        </div>
      )}
    </div>
  );
}

function ScenarioComparisonChart({ result }) {
  const data = useMemo(() => {
    if (!result) return [];
    return [
      { metric: 'FTE Count', current: result.current.total_fte, scenario: result.scenario.total_fte },
      { metric: 'MEC %', current: result.current.mec_pct, scenario: result.scenario.mec_pct },
      { metric: 'FT Employees', current: result.current.ft, scenario: result.scenario.ft },
    ];
  }, [result]);

  const penaltyData = useMemo(() => {
    if (!result) return [];
    return [
      { metric: 'Penalty', current: result.current.total_penalty, scenario: result.scenario.total_penalty },
    ];
  }, [result]);

  const maxPenalty = Math.max(result.current.total_penalty, result.scenario.total_penalty, 1);

  return (
    <div className="p-3 rounded-lg bg-slate-50 border" data-testid="scenario-comparison-chart">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-bold text-slate-600">Visual Comparison</p>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> Current</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-500 inline-block" /> After Scenario</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, left: 15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="metric" tick={{ fontSize: 9, fill: '#64748b', fontWeight: 600 }} tickLine={false} axisLine={false} width={75} />
          <Tooltip content={<ChartTooltipContent />} />
          <Bar dataKey="current" name="Current" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={10} />
          <Bar dataKey="scenario" name="After Scenario" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={10} />
        </BarChart>
      </ResponsiveContainer>
      {/* Penalty bar separate to handle different scale */}
      {maxPenalty > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-200">
          <div className="flex items-center gap-2 text-[10px]">
            <span className="w-[75px] text-right text-slate-600 font-semibold shrink-0">Penalty</span>
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 rounded bg-blue-500 transition-all" style={{ width: `${(result.current.total_penalty / maxPenalty) * 100}%`, minWidth: result.current.total_penalty > 0 ? '4px' : '0' }} />
                <span className="text-[9px] font-bold text-blue-700 tabular-nums">${result.current.total_penalty.toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 rounded bg-violet-500 transition-all" style={{ width: `${(result.scenario.total_penalty / maxPenalty) * 100}%`, minWidth: result.scenario.total_penalty > 0 ? '4px' : '0' }} />
                <span className="text-[9px] font-bold text-violet-700 tabular-nums">${result.scenario.total_penalty.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}




function AiSummaryFormatted({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-1.5" />;

        // Top-level status headers ("COMPLIANCE RISK: HIGH", "COMPLIANCE STATUS: GOOD")
        if (/^COMPLIANCE (RISK|STATUS)/.test(trimmed)) {
          const isRisk = /HIGH|CRITICAL/.test(trimmed);
          return (
            <div key={i} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg mb-0.5 ${isRisk ? 'bg-rose-50 border border-rose-200' : 'bg-emerald-50 border border-emerald-200'}`}>
              {isRisk
                ? <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                : <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />}
              <span className={`text-xs font-extrabold tracking-wide ${isRisk ? 'text-rose-700' : 'text-emerald-700'}`}>
                {trimmed}
              </span>
            </div>
          );
        }

        // Section headers (ALL CAPS: "MEC COVERAGE", "HIRING TREND", "COST SUMMARY", etc.)
        if (/^[A-Z][A-Z\s\-—:()%$,.0-9]+$/.test(trimmed) && trimmed.length > 3) {
          return (
            <div key={i} className="mt-2.5 mb-0.5 flex items-center gap-1.5">
              <div className="w-0.5 h-3.5 rounded-full bg-blue-500" />
              <span className="text-[11px] font-bold text-slate-800 tracking-tight">{trimmed}</span>
            </div>
          );
        }

        // Numbered items ("1. FIX MEC COMPLIANCE", "  1. Extend MEC offers...")
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
        if (numberedMatch) {
          const isIndented = line.startsWith('  ');
          return (
            <div key={i} className={`flex items-start gap-2 ${isIndented ? 'ml-2.5 py-0.5' : 'mt-1.5 py-0.5'}`}>
              <span className={`${isIndented ? 'w-4 h-4 text-[9px]' : 'w-5 h-5 text-[10px]'} rounded-full font-bold flex items-center justify-center shrink-0 ${isIndented ? 'bg-blue-100 text-blue-700' : 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-sm'}`}>
                {numberedMatch[1]}
              </span>
              <span className={`${isIndented ? 'text-[11px] text-slate-600 leading-snug' : 'text-[11px] font-semibold text-slate-800 leading-snug'}`}>
                {numberedMatch[2]}
              </span>
            </div>
          );
        }

        // Bullet points ("- Something")
        if (trimmed.startsWith('- ')) {
          const content = trimmed.slice(2).replace(
            /(\$[\d,]+(?:\/\w+)?|[\d.]+%)/g,
            '<strong class="text-slate-800">$1</strong>'
          );
          return (
            <div key={i} className="flex items-start gap-2 ml-1.5 py-0.5">
              <span className="w-1 h-1 rounded-full bg-blue-400 mt-[6px] shrink-0" />
              <span className="text-[11px] text-slate-600 leading-relaxed" dangerouslySetInnerHTML={{ __html: content }} />
            </div>
          );
        }

        // Indented context lines ("   Try: ...", "   See: ...", "   Expected: ...")
        if (line.startsWith('   ')) {
          const labelMatch = trimmed.match(/^(Try|See|Expected|Formula|TO ELIMINATE):\s*(.+)/);
          if (labelMatch) {
            return (
              <div key={i} className="ml-8 flex items-start gap-1.5 py-0.5">
                <span className="text-[11px] text-blue-600 font-semibold shrink-0">{labelMatch[1]}:</span>
                <span className="text-[11px] text-slate-600">{labelMatch[2]}</span>
              </div>
            );
          }
          return <div key={i} className="ml-8 text-[11px] text-slate-500 py-0.5">{trimmed}</div>;
        }

        // Regular body text
        const bodyContent = trimmed.replace(
          /(\$[\d,]+(?:\/\w+)?)/g,
          '<strong class="text-slate-800">$1</strong>'
        );
        return <div key={i} className="text-[11px] text-slate-600 leading-relaxed" dangerouslySetInnerHTML={{ __html: bodyContent }} />;
      })}
    </div>
  );
}


function ClipboardList(props) { return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/></svg>; }

const STATUS_LABELS = {
  pending: 'Pending', accepted: 'Accepted', paid: 'Paid — Ready to Work',
  delivered: 'Delivered', validated: 'Validated', rejected: 'Rejected',
  resubmit_needed: 'Revision Requested',
};

function ActuaryCertSection({ title, icon: SectionIcon, iconBg, iconColor, certs, emptyMsg, emptyIcon: EmptyIcon, navigate, statusBg, statusTx, actionLabel, colors }) {
  const C = colors;
  return (
    <div className="rounded-2xl border overflow-hidden" style={{ background: C.surface, borderColor: C.border }} data-testid={`cert-section-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg }}>
            <SectionIcon className="w-4 h-4" style={{ color: iconColor }} />
          </div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{title}</h3>
            {certs && certs.length > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full text-white" style={{ background: C.primary }}>{certs.length}</span>
            )}
          </div>
        </div>
      </div>

      {(!certs || certs.length === 0) ? (
        <div className="py-10 px-5 text-center">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3" style={{ background: C.secondary }}>
            <EmptyIcon className="w-6 h-6" style={{ color: C.light }} />
          </div>
          <p className="text-sm" style={{ color: C.muted }}>{emptyMsg}</p>
        </div>
      ) : (
        <div className="p-4 space-y-2.5">
          {certs.map(cert => (
            <div key={cert.id}
              className="rounded-xl border p-4 flex items-center justify-between cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
              style={{ background: C.bg, borderColor: C.border }}
              onClick={() => navigate(`/marketplace?quote_id=${cert.id}`)}
              data-testid={`cert-card-${cert.id}`}>
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: C.secondary }}>
                  <FileBarChart className="w-5 h-5" style={{ color: C.primary }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h4 className="text-sm font-bold truncate" style={{ color: C.text, fontFamily: "'Manrope', sans-serif" }}>{cert.plan_name}</h4>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                      style={{ background: statusBg, color: statusTx }}>
                      {STATUS_LABELS[cert.status] || cert.status}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: C.muted }}>
                    {cert.employer_name || 'Unknown'} · {cert.created_at ? new Date(cert.created_at).toLocaleDateString() : '—'}
                  </p>
                </div>
              </div>
              <button
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 hover:shadow-md flex-shrink-0 ml-3"
                style={{ background: C.primary, color: '#fff' }}
                onClick={e => { e.stopPropagation(); navigate(`/marketplace?quote_id=${cert.id}`); }}
                data-testid={`cert-action-${cert.id}`}>
                {actionLabel} <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
