import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Download, FileSpreadsheet, Loader2, Users, CheckCircle2,
  Clock, Building2, History, DollarSign
} from 'lucide-react';

export default function CensusExportPage() {
  const { token, API, selectedEmployer } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [generating, setGenerating] = useState(false);
  const [census, setCensus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const employerId = selectedEmployer?.id;

  const loadHistory = useCallback(async () => {
    if (!employerId) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/enrollment/census-history/${employerId}`, { headers });
      setHistory(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  }, [API, token, employerId]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const generateCensus = async () => {
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/enrollment/census/${employerId}`, {}, { headers });
      setCensus(res.data);
      toast.success(`Census generated: ${res.data.total_enrolled} employees`);
      loadHistory();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate census');
    }
    setGenerating(false);
  };

  const downloadExcel = async (censusId) => {
    try {
      const res = await axios.get(
        `${API}/enrollment/census/${employerId}/download/${censusId}`,
        { headers, responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `census_${new Date().toISOString().slice(0,10)}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Excel downloaded');
    } catch (err) {
      toast.error('Download failed');
    }
  };

  if (!employerId) {
    return (
      <div className="p-6 max-w-7xl mx-auto" data-testid="census-export-page">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Census Export</h1>
        <Card className="border-0 shadow-sm mt-4"><CardContent className="p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Building2 className="w-7 h-7 text-indigo-500" /></div>
          <p className="text-sm text-muted-foreground">Select an employer first</p>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="census-export-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Census Export</h1>
          <p className="text-sm text-muted-foreground mt-1">Step 5: Generate carrier enrollment census files</p>
        </div>
        <Button onClick={generateCensus} disabled={generating} className="h-9 text-sm" data-testid="generate-census-btn">
          {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
          Generate Census
        </Button>
      </div>

      {/* Latest Census */}
      {census && (
        <Card className="border-0 shadow-sm mb-5 overflow-hidden" data-testid="census-result-card">
          <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
          <CardHeader className="py-3 px-5">
            <CardTitle className="text-base font-bold font-[Manrope] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Census Generated
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1"><Users className="w-4 h-4 text-muted-foreground" /> {census.total_enrolled} employees</span>
                <span className="text-muted-foreground">{new Date(census.generated_at).toLocaleString()}</span>
              </div>
              <Button size="sm" className="h-8 text-xs" onClick={() => downloadExcel(census.id)} data-testid="download-census-btn">
                <Download className="w-3 h-3 mr-1" /> Download Excel
              </Button>
            </div>

            {/* Preview table */}
            <div className="border-0 rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">SSN</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Name</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Plan</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Carrier</th>
                    <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tier</th>
                    <th className="text-right py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">EE Premium</th>
                    <th className="text-right py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">ER Contrib</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Effective</th>
                    <th className="text-center py-2.5 px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Offer Code</th>
                  </tr>
                </thead>
                <tbody>
                  {census.rows?.slice(0, 15).map((r, i) => (
                    <tr key={i} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                      <td className="py-2 px-3 font-mono text-slate-400">***-**-{r.ssn_last4}</td>
                      <td className="py-2 px-3 font-semibold text-slate-800">{r.employee_name}</td>
                      <td className="py-2 px-3">{r.plan_name}</td>
                      <td className="py-2 px-3">{r.carrier}</td>
                      <td className="py-2 px-3 text-center">{r.coverage_tier}</td>
                      <td className="py-2 px-3 text-right tabular-nums">${r.employee_premium?.toFixed(2)}</td>
                      <td className="py-2 px-3 text-right tabular-nums">${r.employer_contribution?.toFixed(2)}</td>
                      <td className="py-2 px-3">{r.effective_date}</td>
                      <td className="py-2 px-3 text-center"><Badge variant="outline" className="text-[10px]">{r.offer_code}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {census.rows?.length > 15 && (
                <div className="p-2 bg-muted/20 text-center text-xs text-muted-foreground">
                  Showing 15 of {census.rows.length} rows
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export History */}
      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : history.length > 0 ? (
        <Card className="border-0 shadow-sm overflow-hidden" data-testid="census-history-card">
          <div className="h-1 bg-gradient-to-r from-slate-300 to-slate-400" />
          <CardHeader className="py-3 px-5">
            <CardTitle className="text-base font-bold font-[Manrope] flex items-center gap-2">
              <History className="w-4 h-4" /> Export History
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="space-y-2">
              {history.map(h => (
                <div key={h.id} className="flex items-center justify-between p-3 border-0 rounded-lg bg-slate-50/80 hover:bg-indigo-50/40 transition-colors" data-testid={`census-history-${h.id}`}>
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                    <div>
                      <p className="text-sm font-medium">{h.employer_name}</p>
                      <p className="text-[10px] text-muted-foreground">{new Date(h.generated_at).toLocaleString()} &middot; {h.total_enrolled} employees</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => downloadExcel(h.id)} data-testid={`download-history-${h.id}`}>
                    <Download className="w-3 h-3 mr-1" /> Download
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !census ? (
        <Card className="border-0 shadow-sm">
          <CardContent className="p-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><FileSpreadsheet className="w-7 h-7 text-indigo-500" /></div>
            <h3 className="text-base font-bold font-[Manrope]">No Census Files</h3>
            <p className="text-sm text-muted-foreground mt-1">Approve employee enrollments first, then generate a census file for carrier submission</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
