import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import axios from 'axios';
import {
  FileText, Download, Eye, ChevronDown, ChevronUp,
  Building2, Users, ShieldCheck, AlertTriangle,
  CheckCircle2, Loader2, Search, FileSpreadsheet, Printer
} from 'lucide-react';

// Backend host base (no /api suffix here — each call appends /api/... explicitly).
// Empty in local dev so calls are relative and hit the setupProxy.js forwarder.
const API = process.env.REACT_APP_BACKEND_URL || '';

function CodeBadge({ code, type }) {
  if (!code) return <span className="text-xs text-muted-foreground">-</span>;
  const colors = type === '14'
    ? { '1A': 'bg-emerald-50 text-emerald-700 border-emerald-200', '1B': 'bg-blue-50 text-blue-700 border-blue-200', '1E': 'bg-blue-50 text-blue-700 border-blue-200', '1H': 'bg-red-50 text-red-700 border-red-200', '1F': 'bg-amber-50 text-amber-700 border-amber-200' }
    : { '2C': 'bg-emerald-50 text-emerald-700 border-emerald-200', '2F': 'bg-sky-50 text-sky-700 border-sky-200', '2G': 'bg-sky-50 text-sky-700 border-sky-200', '2H': 'bg-sky-50 text-sky-700 border-sky-200' };
  const cls = colors[code] || 'bg-gray-50 text-gray-600 border-gray-200';
  return <span className={`text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded border ${cls}`}>{code}</span>;
}

export default function IRSFormsPage() {
  const { selectedEmployer, token } = useAuth();
  const [taxYear, setTaxYear] = useState(new Date().getFullYear());
  const [summary, setSummary] = useState(null);
  const [form1094c, setForm1094c] = useState(null);
  const [forms1095c, setForms1095c] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [search, setSearch] = useState('');
  const [expanded1095, setExpanded1095] = useState(null);
  const [downloadingPdf, setDownloadingPdf] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const fetchSummary = useCallback(async () => {
    if (!selectedEmployer) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/api/irs-forms/summary/${selectedEmployer.id}/${taxYear}`, { headers });
      setSummary(res.data);
    } catch (err) {
      toast.error('Failed to load IRS forms summary');
    } finally {
      setLoading(false);
    }
  }, [selectedEmployer, taxYear, token]);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  const generateForms = async () => {
    if (!selectedEmployer) return;
    setGenerating(true);
    try {
      const [res1094, res1095] = await Promise.all([
        axios.get(`${API}/api/irs-forms/1094c/${selectedEmployer.id}/${taxYear}`, { headers }),
        axios.get(`${API}/api/irs-forms/1095c/${selectedEmployer.id}/${taxYear}`, { headers }),
      ]);
      setForm1094c(res1094.data);
      setForms1095c(res1095.data.forms || []);
      setActiveTab('1094c');
      toast.success(`Forms generated: 1 Form 1094-C + ${res1095.data.count} Forms 1095-C`);
      fetchSummary();
    } catch (err) {
      toast.error('Failed to generate forms');
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = async (formType, employeeId = null, employeeName = null) => {
    const key = formType + (employeeId || '');
    setDownloadingPdf(key);
    try {
      let url = formType === '1094c'
        ? `${API}/api/irs-forms/1094c/${selectedEmployer.id}/${taxYear}/pdf`
        : `${API}/api/irs-forms/1095c/${selectedEmployer.id}/${taxYear}/${employeeId}/pdf`;
      const res = await axios.get(url, { headers, responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      const safeName = (employeeName || '').replace(/\s+/g, '_') || 'employee';
      link.download = formType === '1094c'
        ? `1094-C_${selectedEmployer.name}_${taxYear}.pdf`
        : `1095-C_${safeName}_${taxYear}.pdf`;
      link.click();
      URL.revokeObjectURL(link.href);
      toast.success('PDF downloaded');
    } catch (err) {
      toast.error('Failed to download PDF');
    } finally {
      setDownloadingPdf(null);
    }
  };

  const filtered1095 = forms1095c.filter(f =>
    f.part1?.employee_name?.toLowerCase().includes(search.toLowerCase())
  );

  if (!selectedEmployer) {
    return (
      <div className="p-6 flex items-center justify-center h-full" data-testid="irs-forms-no-employer">
        <Card className="max-w-md w-full border-0 shadow-sm">
          <CardContent className="pt-8 pb-6 text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Building2 className="w-7 h-7 text-indigo-500" /></div>
            <p className="font-bold font-[Manrope]">Select an employer first</p>
            <p className="text-sm text-muted-foreground mt-1">Choose an organization from the sidebar to generate IRS forms.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6" data-testid="irs-forms-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-primary" />
            IRS Forms
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generate and download Form 1094-C and 1095-C for ACA compliance filing
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Tax Year:</span>
            <Input
              data-testid="tax-year-input"
              type="number"
              value={taxYear}
              onChange={e => setTaxYear(parseInt(e.target.value) || new Date().getFullYear())}
              className="w-24 h-8 text-sm"
              min={2020}
              max={2030}
            />
          </div>
          <Button
            data-testid="generate-forms-btn"
            onClick={generateForms}
            disabled={generating}
            className="h-8 text-sm"
          >
            {generating ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5" />}
            {generating ? 'Generating...' : 'Generate All Forms'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="irs-summary-cards">
          <Card className="border-0 bg-gradient-to-br from-blue-50 to-blue-100/80 shadow-sm">
            <CardContent className="pt-4 pb-3 px-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-blue-500 uppercase tracking-wider font-semibold">FT Employees</span>
                <div className="w-8 h-8 rounded-xl bg-blue-200/70 flex items-center justify-center"><Users className="w-4 h-4 text-blue-600" /></div>
              </div>
              <p className="text-2xl font-bold tabular-nums text-blue-900">{summary.full_time_employees}</p>
              <p className="text-[10px] text-blue-600/70 mt-0.5">{summary.total_employees} total</p>
            </CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm">
            <CardContent className="pt-4 pb-3 px-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">ALE Status</span>
                <div className="w-8 h-8 rounded-xl bg-emerald-200/70 flex items-center justify-center"><ShieldCheck className="w-4 h-4 text-emerald-600" /></div>
              </div>
              <p className="text-2xl font-bold tabular-nums text-emerald-900">{summary.total_fte}</p>
              <p className="text-[10px] mt-0.5">
                {summary.is_ale
                  ? <span className="text-emerald-600 font-semibold">ALE (50+ FTE)</span>
                  : <span className="text-amber-600 font-semibold">Not ALE</span>}
              </p>
            </CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-indigo-50 to-indigo-100/80 shadow-sm">
            <CardContent className="pt-4 pb-3 px-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-indigo-500 uppercase tracking-wider font-semibold">1095-C Forms</span>
                <div className="w-8 h-8 rounded-xl bg-indigo-200/70 flex items-center justify-center"><FileText className="w-4 h-4 text-indigo-600" /></div>
              </div>
              <p className="text-2xl font-bold tabular-nums text-indigo-900">{forms1095c.length || summary.forms_1095c_count || 0}</p>
              <p className="text-[10px] text-indigo-600/70 mt-0.5">employees offered coverage</p>
            </CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
            <CardContent className="pt-4 pb-3 px-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Generated</span>
                <div className="w-8 h-8 rounded-xl bg-slate-200/70 flex items-center justify-center"><Printer className="w-4 h-4 text-slate-600" /></div>
              </div>
              <p className="text-2xl font-bold tabular-nums text-slate-900">
                {summary.form_1094c_generated ? '1' : '0'} + {summary.forms_1095c_count}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">1094-C + 1095-C</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 pb-0">
        {[
          { id: 'summary', label: 'Overview', icon: Eye },
          { id: '1094c', label: 'Form 1094-C', icon: FileText },
          { id: '1095c', label: 'Forms 1095-C', icon: FileSpreadsheet },
        ].map(tab => (
          <button
            key={tab.id}
            data-testid={`tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-[1px] ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-slate-300'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
            {tab.id === '1095c' && forms1095c.length > 0 && (
              <Badge variant="secondary" className="ml-1 text-[10px] px-1.5 py-0 h-4">{forms1095c.length}</Badge>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'summary' && (
        <div className="space-y-4" data-testid="tab-content-summary">
          {!summary?.is_ale && summary && (
            <Card className="border-amber-200 bg-amber-50/50">
              <CardContent className="pt-4 pb-3 px-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Not an Applicable Large Employer</p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    With {summary.total_fte} FTEs (below 50 threshold), IRS Form 1094-C/1095-C filing may not be required.
                    However, you can still generate forms for record-keeping.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-bold font-[Manrope]">Filing Readiness Checklist</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                { label: 'Employer profile complete', done: !!selectedEmployer?.ein, detail: selectedEmployer?.ein ? `EIN: ${selectedEmployer.ein}` : 'Missing EIN' },
                { label: 'Employee profiles entered', done: (summary?.full_time_employees || 0) > 0, detail: `${summary?.full_time_employees || 0} full-time employees` },
                { label: 'ALE determination', done: summary?.is_ale, detail: `${summary?.total_fte || 0} FTE` },
                { label: 'MEC coverage tracked', done: (summary?.mec_offered_count || 0) > 0, detail: `${summary?.mec_offered_count || 0} offered MEC` },
                { label: 'Health plans configured', done: (summary?.plans_count || 0) > 0, detail: `${summary?.plans_count || 0} plans` },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  {item.done
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    : <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <span className="text-sm">{item.label}</span>
                    <span className="text-xs text-muted-foreground ml-2">{item.detail}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="flex justify-center pt-2">
            <Button data-testid="generate-forms-cta" onClick={generateForms} disabled={generating} size="lg">
              {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
              {generating ? 'Generating All Forms...' : 'Generate All IRS Forms'}
            </Button>
          </div>
        </div>
      )}

      {activeTab === '1094c' && (
        <div className="space-y-4" data-testid="tab-content-1094c">
          {!form1094c ? (
            <Card className="border-0 shadow-sm">
              <CardContent className="pt-8 pb-6 text-center">
                <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><FileText className="w-7 h-7 text-indigo-500" /></div>
                <p className="font-bold font-[Manrope]">No Form 1094-C generated yet</p>
                <p className="text-sm text-muted-foreground mt-1">Click "Generate All Forms" to create the transmittal form.</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Form 1094-C &mdash; Transmittal</h2>
                <Button
                  data-testid="download-1094c-pdf"
                  variant="outline"
                  size="sm"
                  onClick={() => downloadPdf('1094c')}
                  disabled={downloadingPdf === '1094c'}
                >
                  {downloadingPdf === '1094c' ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1.5" />}
                  Download PDF
                </Button>
              </div>

              {/* Part I */}
              <Card className="border-0 shadow-sm overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-blue-400 to-indigo-400" />
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-bold text-slate-600">Part I &mdash; ALE Member Information</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                    {[
                      ['Employer Name', form1094c.part1?.employer_name],
                      ['EIN', form1094c.part1?.employer_ein || 'Not set'],
                      ['Address', form1094c.part1?.employer_address || 'Not set'],
                      ['Tax Year', form1094c.tax_year],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between py-1.5 border-b border-slate-100">
                        <span className="text-xs text-slate-500">{k}</span>
                        <span className="text-xs font-semibold text-slate-800">{v}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Part II */}
              <Card className="border-0 shadow-sm overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-bold text-slate-600">Part II &mdash; ALE Member Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                    {[
                      ['Total 1095-C Forms', form1094c.part2?.total_1095c_forms],
                      ['Is ALE Member', form1094c.part2?.is_ale_member ? 'Yes' : 'No'],
                      ['Total FTE', form1094c.part2?.total_fte],
                      ['MEC Offered %', `${form1094c.part2?.mec_offered_to_pct}%`],
                      ['Authoritative Transmittal', form1094c.part2?.is_authoritative_transmittal ? 'Yes' : 'No'],
                      ['Plan Start Month', `Month ${form1094c.part2?.plan_start_month}`],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between py-1.5 border-b border-slate-100">
                        <span className="text-xs text-slate-500">{k}</span>
                        <span className="text-xs font-semibold text-slate-800">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Part III Monthly */}
              <Card className="border-0 shadow-sm overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-violet-400 to-purple-400" />
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-bold text-slate-600">Part III &mdash; Monthly Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs" data-testid="1094c-monthly-table">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <th className="py-2 px-3 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Month</th>
                          <th className="py-2 px-3 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">FT Employees</th>
                          <th className="py-2 px-3 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Employees</th>
                          <th className="py-2 px-3 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">Aggregated Group</th>
                        </tr>
                      </thead>
                      <tbody>
                        {form1094c.part3?.monthly_data?.map((m, idx) => (
                          <tr key={m.month} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                            <td className="py-1.5 px-3 font-semibold text-slate-700">{m.month_name}</td>
                            <td className="py-1.5 px-3 text-center tabular-nums">{m.ft_employee_count}</td>
                            <td className="py-1.5 px-3 text-center tabular-nums">{m.total_employee_count}</td>
                            <td className="py-1.5 px-3 text-center">{m.aggregated_group ? 'Yes' : 'No'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      {activeTab === '1095c' && (
        <div className="space-y-4" data-testid="tab-content-1095c">
          {forms1095c.length === 0 ? (
            <Card className="border-0 shadow-sm">
              <CardContent className="pt-8 pb-6 text-center">
                <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><FileSpreadsheet className="w-7 h-7 text-indigo-500" /></div>
                <p className="font-bold font-[Manrope]">No Forms 1095-C generated yet</p>
                <p className="text-sm text-muted-foreground mt-1">Click "Generate All Forms" to create individual employee forms.</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{forms1095c.length} Forms 1095-C</h2>
                <div className="relative w-56">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                  <Input
                    data-testid="search-1095c"
                    placeholder="Search employees..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="h-8 text-sm pl-8"
                  />
                </div>
              </div>

              <div className="space-y-2">
                {filtered1095.map((form, idx) => {
                  const isExpanded = expanded1095 === idx;
                  const empId = form.employee_id;
                  return (
                    <Card key={idx} className="overflow-hidden border-0 shadow-sm">
                      <div
                        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-indigo-50/40 transition-colors"
                        onClick={() => setExpanded1095(isExpanded ? null : idx)}
                        data-testid={`1095c-row-${idx}`}
                      >
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary flex-shrink-0">
                          {form.part1?.employee_name?.charAt(0)?.toUpperCase() || '?'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{form.part1?.employee_name}</p>
                          <p className="text-[11px] text-muted-foreground">
                            SSN: XXX-XX-{form.part1?.employee_ssn_last4 || '****'} &middot; Line 14: <CodeBadge code={form.part2?.line14_all_year} type="14" /> &middot; Line 16: <CodeBadge code={form.part2?.line16_all_year} type="16" />
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            data-testid={`download-1095c-${idx}`}
                            onClick={e => { e.stopPropagation(); downloadPdf('1095c', empId, form.part1?.employee_name); }}
                            disabled={downloadingPdf === '1095c' + empId}
                          >
                            {downloadingPdf === '1095c' + empId ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                          </Button>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="border-t border-slate-100 px-4 py-3 bg-slate-50/50 space-y-3">
                          {/* Part II Monthly Table */}
                          <div>
                            <p className="text-xs font-bold text-slate-500 mb-2">Part II &mdash; Monthly Offer & Coverage</p>
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs" data-testid={`1095c-monthly-${idx}`}>
                                <thead>
                                  <tr className="border-b border-slate-200 bg-slate-100/50">
                                    <th className="py-1.5 px-2 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Month</th>
                                    <th className="py-1.5 px-2 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">Line 14 (Offer)</th>
                                    <th className="py-1.5 px-2 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">Line 15 (Premium)</th>
                                    <th className="py-1.5 px-2 text-center text-[11px] font-bold text-slate-500 uppercase tracking-wider">Line 16 (Safe Harbor)</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {form.part2?.monthly_data?.map((m, mIdx) => (
                                    <tr key={m.month} className={`border-b border-slate-100 ${mIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                                      <td className="py-1 px-2 font-semibold text-slate-700">{m.month_name}</td>
                                      <td className="py-1 px-2 text-center"><CodeBadge code={m.line14_code} type="14" /></td>
                                      <td className="py-1 px-2 text-center tabular-nums">${m.line15_premium?.toFixed(2)}</td>
                                      <td className="py-1 px-2 text-center"><CodeBadge code={m.line16_code} type="16" /></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Part III Covered Individuals */}
                          {form.part3?.covered_individuals?.length > 0 && (
                            <div>
                              <p className="text-xs font-bold text-slate-500 mb-2">Part III &mdash; Covered Individuals</p>
                              <div className="space-y-1">
                                {form.part3.covered_individuals.map((ci, ciIdx) => (
                                  <div key={ciIdx} className="flex items-center gap-3 text-xs py-1.5 border-b border-slate-100 last:border-0">
                                    <span className="font-semibold text-slate-800 w-32 truncate">{ci.name}</span>
                                    <Badge variant="outline" className="text-[10px]">{ci.relationship}</Badge>
                                    <span className="text-muted-foreground">{ci.all_12_months ? 'All 12 months' : 'Partial'}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
