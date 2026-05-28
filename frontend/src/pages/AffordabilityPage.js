import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import axios from 'axios';
import { DollarSign, CheckCircle2, XCircle, RotateCcw, Info, ShieldCheck } from 'lucide-react';

export default function AffordabilityPage() {
  const { token, API } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const [form, setForm] = useState({
    employee_name: '',
    employee_monthly_premium: '125',
    w2_wages: '50000',
    hourly_rate: '24',
    household_size: '1',
  });

  const update = (f, v) => setForm(p => ({ ...p, [f]: v }));

  const handleCalculate = async () => {
    if (!form.employee_name) { toast.error('Employee name required'); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/affordability/calculate`, {
        employee_name: form.employee_name,
        employee_monthly_premium: parseFloat(form.employee_monthly_premium) || 0,
        w2_wages: parseFloat(form.w2_wages) || 0,
        hourly_rate: parseFloat(form.hourly_rate) || 0,
        household_size: parseInt(form.household_size) || 1,
      }, { headers });
      setResult(res.data);
      toast.success('Affordability calculated');
    } catch (err) { toast.error('Calculation failed'); }
    setLoading(false);
  };

  const reset = () => {
    setForm({ employee_name: '', employee_monthly_premium: '125', w2_wages: '50000', hourly_rate: '24', household_size: '1' });
    setResult(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="affordability-page">
      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Affordability Calculator</h1>
        <p className="text-sm text-muted-foreground mt-1">Test all three IRS safe harbor methods for employee premium affordability</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-rose-400 to-pink-400" />
            <CardHeader className="py-3 px-5">
              <CardTitle className="text-base font-bold font-[Manrope]">Employee & Premium Details</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs">Employee Name *</Label>
                  <Input data-testid="afford-name" value={form.employee_name} onChange={e => update('employee_name', e.target.value)} className="h-9 text-sm mt-1" placeholder="Employee name" />
                </div>
                <div>
                  <Label className="text-xs">Monthly Employee Premium ($) *</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                    <Input data-testid="afford-premium" type="number" value={form.employee_monthly_premium} onChange={e => update('employee_monthly_premium', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                  </div>
                </div>
              </div>

              <Separator />
              <p className="text-sm font-semibold font-[Manrope]">Safe Harbor Inputs</p>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-xs">W-2 Annual Wages ($)</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                    <Input data-testid="afford-w2" type="number" value={form.w2_wages} onChange={e => update('w2_wages', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-0.5">For W-2 Safe Harbor</p>
                </div>
                <div>
                  <Label className="text-xs">Hourly Rate ($)</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                    <Input data-testid="afford-hourly" type="number" value={form.hourly_rate} onChange={e => update('hourly_rate', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-0.5">For Rate of Pay Safe Harbor</p>
                </div>
                <div>
                  <Label className="text-xs">Household Size</Label>
                  <Select value={form.household_size} onValueChange={v => update('household_size', v)}>
                    <SelectTrigger className="h-9 text-sm mt-1" data-testid="afford-household"><SelectValue /></SelectTrigger>
                    <SelectContent position="popper" sideOffset={4}>{[1,2,3,4,5,6,7,8].map(n => <SelectItem key={n} value={n.toString()}>{n}</SelectItem>)}</SelectContent>
                  </Select>
                  <p className="text-[10px] text-muted-foreground mt-0.5">For FPL Safe Harbor</p>
                </div>
              </div>

              <Separator />
              <div className="flex gap-3">
                <Button onClick={handleCalculate} disabled={loading} className="flex-1 h-10 text-sm" data-testid="calc-affordability-btn">
                  <DollarSign className="w-4 h-4 mr-2" /> {loading ? 'Calculating...' : 'Calculate Affordability'}
                </Button>
                <Button variant="outline" onClick={reset} className="h-10 text-sm px-4" data-testid="reset-affordability">
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Reset
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div>
          <Card className="border-0 shadow-sm sticky top-6 overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-blue-400 to-indigo-400" />
            <CardHeader className="py-3 px-5">
              <CardTitle className="text-base font-bold font-[Manrope]">Affordability Results</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              {!result ? (
                <div className="py-10 text-center">
                  <Info className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">Enter details and calculate to see safe harbor results</p>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in-up">
                  <div className={`p-4 rounded-lg ${result.overall_affordable ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`} data-testid="affordability-result">
                    <div className="flex items-center gap-2">
                      {result.overall_affordable ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <XCircle className="w-5 h-5 text-rose-600" />}
                      <span className={`text-sm font-bold ${result.overall_affordable ? 'text-emerald-800' : 'text-rose-800'}`}>
                        {result.overall_affordable ? 'Coverage is Affordable' : 'Coverage Not Affordable'}
                      </span>
                    </div>
                    <p className="text-xs mt-1 ml-7 text-muted-foreground">
                      ${result.employee_monthly_premium}/mo (${result.annual_premium}/yr)
                    </p>
                    {result.best_safe_harbor && (
                      <p className="text-xs mt-0.5 ml-7 text-emerald-700">Best: {result.safe_harbors[result.best_safe_harbor]?.name}</p>
                    )}
                  </div>

                  {Object.entries(result.safe_harbors || {}).map(([key, sh]) => (
                    <div key={key} className={`p-3 rounded-md border ${sh.passed ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'}`}>
                      <div className="flex items-center gap-1.5 text-xs">
                        {sh.passed ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-rose-600" />}
                        <span className="font-semibold">{sh.name}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1 ml-5">{sh.details}</p>
                      <div className="flex justify-between mt-1.5 ml-5 text-[11px]">
                        <span className="text-muted-foreground">Threshold</span>
                        <span className="tabular-nums font-medium">${sh.monthly_threshold}/mo</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
