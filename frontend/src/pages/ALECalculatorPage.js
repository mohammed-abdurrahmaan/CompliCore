import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Users, CheckCircle2, AlertTriangle, XCircle, RefreshCw, Zap,
  Building2, Clock, UserCheck, UserX, TrendingUp,
  Link2, Unlink, CloudDownload, Loader2, ExternalLink
} from 'lucide-react';

export default function ALECalculatorPage() {
  const { selectedEmployer, token, API } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [adpStatus, setAdpStatus] = useState(null);
  const [adpSyncing, setAdpSyncing] = useState(false);
  const [adpConnecting, setAdpConnecting] = useState(false);
  const headers = { Authorization: `Bearer ${token}` };

  const loadSummary = useCallback(async () => {
    if (!selectedEmployer) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/payroll/summary/${selectedEmployer.id}`, { headers });
      setSummary(res.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }, [selectedEmployer, API, token]);

  const loadAdpStatus = useCallback(async () => {
    if (!selectedEmployer) return;
    try {
      const res = await axios.get(`${API}/adp/status/${selectedEmployer.id}`, { headers });
      setAdpStatus(res.data);
    } catch (err) {
      console.error('ADP status check failed:', err);
    }
  }, [selectedEmployer, API, token]);

  useEffect(() => {
    if (selectedEmployer) {
      loadSummary();
      loadAdpStatus();
    }
  }, [selectedEmployer, loadSummary, loadAdpStatus]);

  const generatePayroll = async () => {
    setGenerating(true);
    try {
      await axios.post(`${API}/payroll/generate/${selectedEmployer.id}`, {}, { headers });
      toast.success('Mock payroll generated');
      loadSummary();
    } catch (err) {
      toast.error('Failed to generate payroll');
    }
    setGenerating(false);
  };

  const resetPayroll = async () => {
    try {
      await axios.delete(`${API}/payroll/${selectedEmployer.id}`, { headers });
      toast.success('Payroll reset');
      setSummary(null);
      loadSummary();
    } catch (err) {
      toast.error('Failed to reset');
    }
  };

  const connectADP = async () => {
    setAdpConnecting(true);
    try {
      const res = await axios.get(`${API}/adp/auth-url/${selectedEmployer.id}`, { headers });
      window.open(res.data.auth_url, '_blank', 'width=600,height=700');
      toast.info('Complete ADP authorization in the popup window');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to initiate ADP connection';
      toast.error(msg);
    }
    setAdpConnecting(false);
  };

  const syncADP = async () => {
    setAdpSyncing(true);
    try {
      const res = await axios.post(`${API}/adp/sync/${selectedEmployer.id}`, {}, { headers });
      toast.success(`Synced ${res.data.count} employees from ADP`);
      loadSummary();
      loadAdpStatus();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to sync ADP data';
      toast.error(msg);
    }
    setAdpSyncing(false);
  };

  const disconnectADP = async () => {
    try {
      await axios.post(`${API}/adp/disconnect/${selectedEmployer.id}`, {}, { headers });
      toast.success('ADP disconnected');
      setAdpStatus(prev => ({ ...prev, connected: false, last_sync: null, worker_count: 0 }));
    } catch (err) {
      toast.error('Failed to disconnect ADP');
    }
  };

  if (!selectedEmployer) {
    return <div className="p-6 text-center text-muted-foreground">Please select an employer first</div>;
  }

  // No payroll data yet
  if (summary && !summary.has_payroll) {
    return (
      <div className="p-6 max-w-7xl mx-auto" data-testid="ale-calculator-page">
        <div className="mb-5">
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">ALE Calculator</h1>
          <p className="text-sm text-muted-foreground mt-1">Auto-calculate FTE status from employee payroll data</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-3xl mx-auto">
          {/* ADP Integration Card */}
          <Card className="border-0 shadow-sm overflow-hidden" data-testid="adp-connect-card">
            <div className="h-1 bg-gradient-to-r from-red-500 to-red-600" />
            <CardContent className="p-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
                <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none">
                  <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" fill="#D0271D" opacity="0.15"/>
                  <text x="50%" y="55%" dominantBaseline="middle" textAnchor="middle" fill="#D0271D" fontSize="8" fontWeight="bold" fontFamily="sans-serif">ADP</text>
                </svg>
              </div>
              <h2 className="text-lg font-bold font-[Manrope] mb-1">Connect ADP</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Import real payroll data from ADP Workforce Now via secure OAuth connection
              </p>
              {adpStatus?.configured ? (
                adpStatus?.connected ? (
                  <div className="space-y-2">
                    <Badge className="bg-emerald-100 text-emerald-700">Connected</Badge>
                    <Button onClick={syncADP} disabled={adpSyncing} className="w-full h-10 bg-red-600 hover:bg-red-700" data-testid="sync-adp-btn">
                      <CloudDownload className="w-4 h-4 mr-2" />
                      {adpSyncing ? 'Syncing...' : 'Sync Payroll Data'}
                    </Button>
                  </div>
                ) : (
                  <Button onClick={connectADP} disabled={adpConnecting} className="w-full h-10 bg-red-600 hover:bg-red-700" data-testid="connect-adp-btn">
                    <Link2 className="w-4 h-4 mr-2" />
                    {adpConnecting ? 'Connecting...' : 'Connect ADP Account'}
                  </Button>
                )
              ) : (
                <div>
                  <Badge variant="outline" className="text-slate-500 border-slate-300 mb-2">Not Configured</Badge>
                  <p className="text-xs text-muted-foreground">
                    Add <code className="bg-slate-100 px-1 rounded text-[10px]">ADP_CLIENT_ID</code> and <code className="bg-slate-100 px-1 rounded text-[10px]">ADP_CLIENT_SECRET</code> to enable
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Mock Payroll Card */}
          <Card className="border-0 shadow-sm overflow-hidden" data-testid="mock-payroll-card">
            <div className="h-1 bg-gradient-to-r from-slate-400 to-slate-500" />
            <CardContent className="p-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <Zap className="w-7 h-7 text-slate-500" />
              </div>
              <h2 className="text-lg font-bold font-[Manrope] mb-1">Demo Data</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Generate sample payroll with 40-70 mock employees for testing and demos
              </p>
              <Button variant="outline" onClick={generatePayroll} disabled={generating} className="w-full h-10" data-testid="generate-payroll-btn">
                <Zap className="w-4 h-4 mr-2" />
                {generating ? 'Generating...' : 'Generate Mock Payroll'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="ale-calculator-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">ALE Calculator</h1>
          <div className="text-sm text-muted-foreground mt-1 flex items-center gap-2">
            {summary?.source === 'adp' ? (
              <>
                <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0">ADP</Badge>
                Synced from ADP ({summary?.total_employees || 0} employees)
                {adpStatus?.last_sync && <span className="text-[10px]">· Last sync: {new Date(adpStatus.last_sync).toLocaleString()}</span>}
              </>
            ) : (
              <>
                <Badge variant="outline" className="text-slate-500 text-[10px] px-1.5 py-0">Demo</Badge>
                Mock payroll ({summary?.total_employees || 0} employees)
              </>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {summary?.source === 'adp' && adpStatus?.connected && (
            <>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={syncADP} disabled={adpSyncing} data-testid="resync-adp-btn">
                {adpSyncing ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <CloudDownload className="w-3 h-3 mr-1.5" />}
                Re-sync ADP
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs text-red-600 hover:text-red-700" onClick={disconnectADP} data-testid="disconnect-adp-btn">
                <Unlink className="w-3 h-3 mr-1.5" /> Disconnect
              </Button>
            </>
          )}
          {summary?.source !== 'adp' && (
            <>
              {adpStatus?.configured && !adpStatus?.connected && (
                <Button variant="outline" size="sm" className="h-8 text-xs bg-red-50 hover:bg-red-100 text-red-700 border-red-200" onClick={connectADP} disabled={adpConnecting} data-testid="connect-adp-header-btn">
                  <Link2 className="w-3 h-3 mr-1.5" /> Connect ADP
                </Button>
              )}
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={resetPayroll} data-testid="reset-payroll-btn">
                <RefreshCw className="w-3 h-3 mr-1.5" /> Reset Payroll
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-xs" onClick={generatePayroll} disabled={generating} data-testid="regenerate-payroll-btn">
                <Zap className="w-3 h-3 mr-1.5" /> Regenerate
              </Button>
            </>
          )}
        </div>
      </div>

      {summary && (
        <>
          {/* ALE Status Banner */}
          <Card className={`mb-4 ${summary.is_ale ? 'border-amber-200 bg-amber-50/50' : 'border-emerald-200 bg-emerald-50/50'}`} data-testid="ale-status-banner">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {summary.is_ale ? (
                    <AlertTriangle className="w-7 h-7 text-amber-600" />
                  ) : (
                    <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                  )}
                  <div>
                    <p className="text-lg font-bold font-[Manrope]">
                      {summary.is_ale ? 'Applicable Large Employer (ALE)' : 'Not an ALE'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {summary.full_time_count} full-time + {summary.fte_from_part_time} FTE = <span className="font-bold tabular-nums">{summary.total_fte}</span> (threshold: {summary.ale_threshold})
                    </p>
                  </div>
                </div>
                {summary.is_ale && summary.potential_a_penalty > 0 && (
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Potential 4980H(a) Penalty</p>
                    <p className="text-2xl font-bold tabular-nums text-amber-700">${summary.potential_a_penalty?.toLocaleString()}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total Employees</p>
                    <p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{summary.total_employees}</p>
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center">
                    <Users className="w-5 h-5 text-slate-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">Full-Time</p>
                    <p className="text-3xl font-bold tabular-nums text-emerald-900 mt-1">{summary.full_time_count}</p>
                    <p className="text-[10px] text-emerald-600/70">30+ hrs/week</p>
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-emerald-200/70 flex items-center justify-center">
                    <UserCheck className="w-5 h-5 text-emerald-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-0 bg-gradient-to-br from-blue-50 to-blue-100/80 shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] text-blue-500 uppercase tracking-wider font-semibold">Part-Time FTE</p>
                    <p className="text-3xl font-bold tabular-nums text-blue-900 mt-1">{summary.fte_from_part_time}</p>
                    <p className="text-[10px] text-blue-600/70">{summary.pt_total_monthly_hours} monthly hrs / 120</p>
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-blue-200/70 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className={`border-0 shadow-sm ${summary.mec_compliant ? 'bg-gradient-to-br from-emerald-50 to-emerald-100/80' : 'bg-gradient-to-br from-rose-50 to-rose-100/80'}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-[11px] uppercase tracking-wider font-semibold ${summary.mec_compliant ? 'text-emerald-500' : 'text-rose-500'}`}>MEC Coverage</p>
                    <p className={`text-3xl font-bold tabular-nums mt-1 ${summary.mec_compliant ? 'text-emerald-900' : 'text-rose-900'}`}>{summary.mec_coverage_pct}%</p>
                    <p className={`text-[10px] ${summary.mec_compliant ? 'text-emerald-600/70' : 'text-rose-600/70'}`}>{summary.mec_offered_count}/{summary.full_time_count} offered</p>
                  </div>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${summary.mec_compliant ? 'bg-emerald-200/70' : 'bg-rose-200/70'}`}>
                    {summary.mec_compliant ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-600" />
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Department Breakdown */}
          <Card className="border-0 shadow-sm mb-4 overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-indigo-400 to-violet-400" />
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-bold">Department Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Department</th>
                    <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Full-Time</th>
                    <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Part-Time</th>
                    <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Weekly Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.departments?.map((dept, i) => (
                    <tr key={i} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                      <td className="px-4 py-2 font-semibold text-slate-800">{dept.name}</td>
                      <td className="px-4 py-2 text-center tabular-nums font-semibold text-slate-700">{dept.full_time}</td>
                      <td className="px-4 py-2 text-center tabular-nums text-slate-600">{dept.part_time}</td>
                      <td className="px-4 py-2 text-center tabular-nums text-slate-600">{dept.total_hours}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Employee List */}
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-slate-300 to-slate-400" />
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-bold">Employee Roster (Mock Payroll)</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10">
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">ID</th>
                      <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Name</th>
                      <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Department</th>
                      <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Type</th>
                      <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Hrs/Wk</th>
                      <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Salary</th>
                      <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">MEC Offered</th>
                      <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Enrolled</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.employees?.map((emp, idx) => (
                      <tr key={emp.id} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                        <td className="px-4 py-1.5 text-xs text-slate-400 tabular-nums">{emp.employee_id}</td>
                        <td className="px-4 py-1.5 font-semibold text-slate-800">{emp.name}</td>
                        <td className="px-4 py-1.5 text-slate-500">{emp.department}</td>
                        <td className="px-4 py-1.5 text-center">
                          <Badge variant="outline" className={`text-[10px] ${emp.employment_type === 'full_time' ? 'border-emerald-200 text-emerald-700 bg-emerald-50' : 'border-blue-200 text-blue-700 bg-blue-50'}`}>
                            {emp.employment_type === 'full_time' ? 'FT' : 'PT'}
                          </Badge>
                        </td>
                        <td className="px-4 py-1.5 text-center tabular-nums">{emp.weekly_hours}</td>
                        <td className="px-4 py-1.5 text-center tabular-nums">${emp.annual_salary?.toLocaleString()}</td>
                        <td className="px-4 py-1.5 text-center">
                          {emp.offered_mec ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mx-auto" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5 text-rose-400 mx-auto" />
                          )}
                        </td>
                        <td className="px-4 py-1.5 text-center">
                          {emp.enrolled ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mx-auto" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5 text-muted-foreground/40 mx-auto" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* ALE Rules */}
          <Card className="border-0 shadow-sm mt-4 overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-amber-300 to-orange-300" />
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-bold">ALE Determination Rules</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 text-xs text-muted-foreground space-y-1.5">
              <p><span className="font-semibold text-foreground">Full-Time:</span> Employees averaging 30+ hours/week or 130+ hours/month</p>
              <p><span className="font-semibold text-foreground">FTE Calculation:</span> Total part-time monthly hours / 120 = Full-Time Equivalents</p>
              <p><span className="font-semibold text-foreground">ALE Threshold:</span> FT + FTE >= 50 = Applicable Large Employer</p>
              <p><span className="font-semibold text-foreground">2026 Penalties:</span> 4980H(a) = $3,340/employee (minus first 30) | 4980H(b) = $5,010/employee</p>
            </CardContent>
          </Card>
        </>
      )}

      {loading && !summary && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      )}
    </div>
  );
}
