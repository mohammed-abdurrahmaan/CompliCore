import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import axios from 'axios';
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle, RotateCcw, Info } from 'lucide-react';

export default function MECTrackingPage() {
  const { token, API } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const [form, setForm] = useState({
    plan_name: '',
    plan_type: 'Group',
    individual_deductible: '2000',
    family_deductible: '4000',
    oop_max_individual: '7500',
    oop_max_family: '15000',
    coinsurance_rate: '20',
    copay_primary: '25',
    copay_specialist: '50',
    copay_emergency: '250',
    copay_generic_rx: '10',
    copay_brand_rx: '40',
    essential_health_benefits: true,
    preventive_care_100: true,
    hsa_eligible: false,
    employee_monthly_contribution: '250',
    employer_monthly_contribution: '500',
    employee_annual_income: '50000',
    household_size: '1',
  });

  const update = (field, value) => setForm(p => ({ ...p, [field]: value }));

  const handleCheck = async () => {
    if (!form.plan_name) { toast.error('Plan name is required'); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/mec/check`, {
        plan_name: form.plan_name,
        plan_type: form.plan_type,
        individual_deductible: parseFloat(form.individual_deductible) || 0,
        family_deductible: parseFloat(form.family_deductible) || 0,
        oop_max_individual: parseFloat(form.oop_max_individual) || 0,
        oop_max_family: parseFloat(form.oop_max_family) || 0,
        coinsurance_rate: parseFloat(form.coinsurance_rate) || 0,
        copay_primary: parseFloat(form.copay_primary) || 0,
        copay_specialist: parseFloat(form.copay_specialist) || 0,
        copay_emergency: parseFloat(form.copay_emergency) || 0,
        copay_generic_rx: parseFloat(form.copay_generic_rx) || 0,
        copay_brand_rx: parseFloat(form.copay_brand_rx) || 0,
        essential_health_benefits: form.essential_health_benefits,
        preventive_care_100: form.preventive_care_100,
        hsa_eligible: form.hsa_eligible,
        employee_monthly_contribution: parseFloat(form.employee_monthly_contribution) || 0,
        employer_monthly_contribution: parseFloat(form.employer_monthly_contribution) || 0,
        employee_annual_income: parseFloat(form.employee_annual_income) || 0,
        household_size: parseInt(form.household_size) || 1,
      }, { headers });
      setResult(res.data);
      toast.success('Compliance check complete');
    } catch (err) {
      toast.error('Compliance check failed');
    }
    setLoading(false);
  };

  const handleReset = () => {
    setForm({
      plan_name: '', plan_type: 'Group',
      individual_deductible: '2000', family_deductible: '4000',
      oop_max_individual: '7500', oop_max_family: '15000',
      coinsurance_rate: '20', copay_primary: '25', copay_specialist: '50',
      copay_emergency: '250', copay_generic_rx: '10', copay_brand_rx: '40',
      essential_health_benefits: true, preventive_care_100: true, hsa_eligible: false,
      employee_monthly_contribution: '250', employer_monthly_contribution: '500',
      employee_annual_income: '50000', household_size: '1',
    });
    setResult(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="mec-checker-page">
      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">MEC Compliance Checker</h1>
        <p className="text-sm text-muted-foreground mt-1">Verify if your health plan meets Minimum Essential Coverage requirements</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Form */}
        <div className="lg:col-span-2">
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
            <CardHeader className="py-3 px-5">
              <CardTitle className="text-base font-bold font-[Manrope]">Plan Details</CardTitle>
              <p className="text-xs text-muted-foreground">Enter your health plan details for compliance analysis</p>
            </CardHeader>
            <CardContent className="px-5 pb-5 space-y-5">
              {/* Plan Name + Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-medium">Plan Name *</Label>
                  <Input data-testid="mec-plan-name" value={form.plan_name} onChange={e => update('plan_name', e.target.value)} placeholder="e.g., Gold PPO 2024" className="h-9 text-sm mt-1" />
                </div>
                <div>
                  <Label className="text-xs font-medium">Plan Type</Label>
                  <Select value={form.plan_type} onValueChange={v => update('plan_type', v)}>
                    <SelectTrigger className="h-9 text-sm mt-1" data-testid="mec-plan-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent position="popper" sideOffset={4}>
                      <SelectItem value="Group">Group</SelectItem>
                      <SelectItem value="Individual">Individual</SelectItem>
                      <SelectItem value="Self-Insured">Self-Insured</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              {/* Deductibles & OOP */}
              <div>
                <p className="text-sm font-semibold font-[Manrope] mb-3 flex items-center gap-1.5">
                  <span className="text-muted-foreground">$</span> Deductibles & Out-of-Pocket
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Annual Deductible (Individual)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-ded-ind" type="number" value={form.individual_deductible} onChange={e => update('individual_deductible', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Annual Deductible (Family)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-ded-fam" type="number" value={form.family_deductible} onChange={e => update('family_deductible', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">OOP Max (Individual) *</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-oop-ind" type="number" value={form.oop_max_individual} onChange={e => update('oop_max_individual', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">2025 limit: $9,200</p>
                  </div>
                  <div>
                    <Label className="text-xs">OOP Max (Family)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-oop-fam" type="number" value={form.oop_max_family} onChange={e => update('oop_max_family', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">2025 limit: $18,400</p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Cost Sharing */}
              <div>
                <p className="text-sm font-semibold font-[Manrope] mb-3">Cost Sharing</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-xs">Coinsurance Rate (%)</Label>
                    <Input data-testid="mec-coinsurance" type="number" value={form.coinsurance_rate} onChange={e => update('coinsurance_rate', e.target.value)} className="h-9 text-sm mt-1 tabular-nums" placeholder="20" />
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Primary Care</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-copay-primary" type="number" value={form.copay_primary} onChange={e => update('copay_primary', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Specialist</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-copay-specialist" type="number" value={form.copay_specialist} onChange={e => update('copay_specialist', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Emergency</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-copay-emergency" type="number" value={form.copay_emergency} onChange={e => update('copay_emergency', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Generic Rx</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-copay-generic" type="number" value={form.copay_generic_rx} onChange={e => update('copay_generic_rx', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Brand Rx</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-copay-brand" type="number" value={form.copay_brand_rx} onChange={e => update('copay_brand_rx', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Coverage Options */}
              <div>
                <p className="text-sm font-semibold font-[Manrope] mb-3">Coverage Options</p>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">Essential Health Benefits</p>
                      <p className="text-[11px] text-muted-foreground">Plan covers all 10 EHBs required by ACA</p>
                    </div>
                    <Switch data-testid="mec-ehb-toggle" checked={form.essential_health_benefits} onCheckedChange={v => update('essential_health_benefits', v)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">Preventive Care at 100%</p>
                      <p className="text-[11px] text-muted-foreground">No cost sharing for preventive services</p>
                    </div>
                    <Switch data-testid="mec-preventive-toggle" checked={form.preventive_care_100} onCheckedChange={v => update('preventive_care_100', v)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">HSA Eligible</p>
                      <p className="text-[11px] text-muted-foreground">High deductible health plan</p>
                    </div>
                    <Switch data-testid="mec-hsa-toggle" checked={form.hsa_eligible} onCheckedChange={v => update('hsa_eligible', v)} />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Affordability Test */}
              <div>
                <p className="text-sm font-semibold font-[Manrope] mb-3 flex items-center gap-1.5">
                  <span className="text-muted-foreground">%</span> Affordability Test
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Employee Monthly Contribution *</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-emp-contribution" type="number" value={form.employee_monthly_contribution} onChange={e => update('employee_monthly_contribution', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Employer Monthly Contribution</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-employer-contribution" type="number" value={form.employer_monthly_contribution} onChange={e => update('employer_monthly_contribution', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Employee Annual Income *</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mec-annual-income" type="number" value={form.employee_annual_income} onChange={e => update('employee_annual_income', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Household Size</Label>
                    <Select value={form.household_size} onValueChange={v => update('household_size', v)}>
                      <SelectTrigger className="h-9 text-sm mt-1" data-testid="mec-household-size">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent position="popper" sideOffset={4}>
                        {[1,2,3,4,5,6,7,8].map(n => (
                          <SelectItem key={n} value={n.toString()}>{n}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Actions */}
              <div className="flex gap-3">
                <Button onClick={handleCheck} disabled={loading} className="flex-1 h-10 text-sm font-medium" data-testid="check-mec-btn">
                  <ShieldCheck className="w-4 h-4 mr-2" />
                  {loading ? 'Checking...' : 'Check MEC Compliance'}
                </Button>
                <Button variant="outline" onClick={handleReset} className="h-10 text-sm px-4" data-testid="reset-mec-btn">
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Reset
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Results */}
        <div>
          <Card className="border-0 shadow-sm sticky top-6 overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-blue-400 to-indigo-400" />
            <CardHeader className="py-3 px-5">
              <CardTitle className="text-base font-bold font-[Manrope]">Compliance Results</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              {!result ? (
                <div className="py-10 text-center">
                  <Info className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">Enter plan details and run compliance check to see results</p>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in-up">
                  {/* Overall Status */}
                  <div className={`p-4 rounded-lg ${result.overall_compliant ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`} data-testid="mec-result-status">
                    <div className="flex items-center gap-2">
                      {result.overall_compliant ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-5 h-5 text-rose-600" />
                      )}
                      <span className={`text-sm font-bold ${result.overall_compliant ? 'text-emerald-800' : 'text-rose-800'}`}>
                        {result.overall_compliant ? 'MEC Compliant' : 'Not MEC Compliant'}
                      </span>
                    </div>
                    <p className="text-xs mt-1 ml-7 text-muted-foreground">
                      Score: {result.compliance_score}% ({result.passed_count}/{result.total_checks} checks passed)
                    </p>
                  </div>

                  {/* Individual Checks */}
                  <div className="space-y-2">
                    {result.checks?.map((check, i) => (
                      <div key={i} className={`p-2.5 rounded-md border text-xs ${check.passed ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'}`}>
                        <div className="flex items-center gap-1.5">
                          {check.passed ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />
                          )}
                          <span className="font-semibold">{check.name}</span>
                        </div>
                        <p className="text-muted-foreground mt-0.5 ml-5">{check.details}</p>
                      </div>
                    ))}
                  </div>

                  {/* Affordability */}
                  {result.affordability && (
                    <div className="border rounded-md p-3">
                      <p className="text-xs font-semibold mb-2">Affordability Details</p>
                      <div className="space-y-1 text-xs">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Annual employee cost</span>
                          <span className="tabular-nums font-medium">${result.affordability.employee_annual_cost?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">% of income</span>
                          <span className="tabular-nums font-medium">{result.affordability.income_percentage}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Threshold</span>
                          <span className="tabular-nums">{result.affordability.affordability_threshold}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">FPL Safe Harbor</span>
                          <Badge className={`text-[10px] ${result.affordability.fpl_safe_harbor_pass ? 'bg-emerald-50 text-emerald-700 border-transparent' : 'bg-rose-50 text-rose-700 border-transparent'}`}>
                            {result.affordability.fpl_safe_harbor_pass ? 'Pass' : 'Fail'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
