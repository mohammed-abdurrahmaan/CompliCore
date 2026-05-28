import { useState, useEffect } from 'react';
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
import { FileBarChart, CheckCircle2, XCircle, AlertTriangle, RotateCcw, Info, Upload, Download, ArrowRight, Store } from 'lucide-react';

export default function MVCalculatorPage() {
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
    hsa_employer_contribution: '0',
    hra_employer_contribution: '0',
  });

  const update = (field, value) => setForm(p => ({ ...p, [field]: value }));

  const handleCalculate = async () => {
    if (!form.plan_name) { toast.error('Plan name is required'); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/mv/calculate-form`, {
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
        hsa_employer_contribution: parseFloat(form.hsa_employer_contribution) || 0,
        hra_employer_contribution: parseFloat(form.hra_employer_contribution) || 0,
      }, { headers });
      setResult(res.data);
      toast.success('MV calculation complete');
    } catch (err) {
      toast.error('Calculation failed');
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
      hsa_employer_contribution: '0', hra_employer_contribution: '0',
    });
    setResult(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="mv-calculator-page">
      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">MV Calculator</h1>
        <p className="text-sm text-muted-foreground mt-1">Calculate actuarial value using HHS methodology (60% threshold)</p>
      </div>

      {/* Upload SBC Section */}
      <Card className="border-0 shadow-sm mb-4 bg-gradient-to-br from-blue-50 to-blue-100/50 overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <Upload className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold font-[Manrope]">Upload Summary of Benefits (SBC)</p>
              <p className="text-xs text-muted-foreground mt-0.5">Upload your SBC PDF to automatically extract plan details</p>
            </div>
          </div>
          <div className="mt-3 border-2 border-dashed border-blue-200 rounded-lg p-8 text-center bg-white/60 hover:bg-white/80 transition-colors cursor-pointer" data-testid="sbc-upload-area">
            <Upload className="w-6 h-6 text-muted-foreground/50 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Drag & drop your SBC PDF here, or click to browse</p>
            <p className="text-xs text-muted-foreground/60 mt-1">PDF files only</p>
          </div>
        </CardContent>
      </Card>

      {/* Sample SBC Banner */}
      <Card className="border-0 shadow-sm mb-5">
        <CardContent className="p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs font-semibold">Need a sample SBC to test?</p>
              <p className="text-[10px] text-muted-foreground">Download our sample PDF with non-standard features</p>
            </div>
          </div>
          <Button variant="default" size="sm" className="h-8 text-xs" data-testid="download-sample-sbc">
            <Download className="w-3 h-3 mr-1.5" /> Download Sample SBC
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Form */}
        <div className="lg:col-span-2">
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-orange-400 to-amber-400" />
            <CardHeader className="py-3 px-5">
              <CardTitle className="text-base font-bold font-[Manrope]">Plan Details</CardTitle>
              <p className="text-xs text-muted-foreground">Enter plan cost-sharing information for MV calculation</p>
            </CardHeader>
            <CardContent className="px-5 pb-5 space-y-5">
              {/* Plan Name + Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-medium">Plan Name *</Label>
                  <Input data-testid="mv-plan-name" value={form.plan_name} onChange={e => update('plan_name', e.target.value)} placeholder="e.g., Silver PPO 2024" className="h-9 text-sm mt-1" />
                </div>
                <div>
                  <Label className="text-xs font-medium">Plan Type</Label>
                  <Select value={form.plan_type} onValueChange={v => update('plan_type', v)}>
                    <SelectTrigger className="h-9 text-sm mt-1" data-testid="mv-plan-type">
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
                  <span className="text-muted-foreground">$</span> Deductibles & Out-of-Pocket Maximums
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Annual Deductible (Individual)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-ded-ind" type="number" value={form.individual_deductible} onChange={e => update('individual_deductible', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Annual Deductible (Family)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-ded-fam" type="number" value={form.family_deductible} onChange={e => update('family_deductible', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">OOP Max (Individual)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-oop-ind" type="number" value={form.oop_max_individual} onChange={e => update('oop_max_individual', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">OOP Max (Family)</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-oop-fam" type="number" value={form.oop_max_family} onChange={e => update('oop_max_family', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Cost Sharing */}
              <div>
                <p className="text-sm font-semibold font-[Manrope] mb-2">Cost Sharing Details</p>
                <p className="text-[11px] text-muted-foreground mb-3">Member's share after deductible</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-xs">Coinsurance Rate (%)</Label>
                    <Input data-testid="mv-coinsurance" type="number" value={form.coinsurance_rate} onChange={e => update('coinsurance_rate', e.target.value)} className="h-9 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Primary Care</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-copay-primary" type="number" value={form.copay_primary} onChange={e => update('copay_primary', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Specialist</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-copay-specialist" type="number" value={form.copay_specialist} onChange={e => update('copay_specialist', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Emergency</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-copay-emergency" type="number" value={form.copay_emergency} onChange={e => update('copay_emergency', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Generic Rx</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-copay-generic" type="number" value={form.copay_generic_rx} onChange={e => update('copay_generic_rx', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Copay - Brand Rx</Label>
                    <div className="relative mt-1">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                      <Input data-testid="mv-copay-brand" type="number" value={form.copay_brand_rx} onChange={e => update('copay_brand_rx', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
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
                      <p className="text-[11px] text-muted-foreground">Plan covers all 10 EHBs</p>
                    </div>
                    <Switch data-testid="mv-ehb-toggle" checked={form.essential_health_benefits} onCheckedChange={v => update('essential_health_benefits', v)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">Preventive Care at 100%</p>
                      <p className="text-[11px] text-muted-foreground">No cost sharing for preventive services</p>
                    </div>
                    <Switch data-testid="mv-preventive-toggle" checked={form.preventive_care_100} onCheckedChange={v => update('preventive_care_100', v)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">HSA Eligible (HDHP)</p>
                      <p className="text-[11px] text-muted-foreground">High deductible health plan</p>
                    </div>
                    <Switch data-testid="mv-hsa-toggle" checked={form.hsa_eligible} onCheckedChange={v => update('hsa_eligible', v)} />
                  </div>
                </div>
              </div>

              {form.hsa_eligible && (
                <>
                  <Separator />
                  <div>
                    <p className="text-sm font-semibold font-[Manrope] mb-3">HSA / HRA Employer Contributions</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs">HSA Employer ($)</Label>
                        <div className="relative mt-1">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                          <Input data-testid="mv-hsa-amt" type="number" value={form.hsa_employer_contribution} onChange={e => update('hsa_employer_contribution', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs">HRA Employer ($)</Label>
                        <div className="relative mt-1">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                          <Input data-testid="mv-hra-amt" type="number" value={form.hra_employer_contribution} onChange={e => update('hra_employer_contribution', e.target.value)} className="h-9 text-sm pl-7 tabular-nums" />
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Actions */}
              <div className="flex gap-3">
                <Button onClick={handleCalculate} disabled={loading} className="flex-1 h-10 text-sm font-medium" data-testid="calculate-mv-btn">
                  <FileBarChart className="w-4 h-4 mr-2" />
                  {loading ? 'Calculating...' : 'Calculate Minimum Value'}
                </Button>
                <Button variant="outline" onClick={handleReset} className="h-10 text-sm px-4" data-testid="reset-mv-btn">
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
              <CardTitle className="text-base font-bold font-[Manrope]">MV Results</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              {!result ? (
                <div className="py-10 text-center">
                  <Info className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">Enter plan details and calculate to see Minimum Value results</p>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in-up">
                  {/* MV Gauge */}
                  <div className={`p-4 rounded-lg text-center ${result.meets_minimum_value ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`} data-testid="mv-result-status">
                    <p className={`text-4xl font-bold tabular-nums ${result.meets_minimum_value ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {result.mv_percentage}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Actuarial Value</p>
                    <div className="mt-2">
                      {result.meets_minimum_value ? (
                        <Badge className="bg-emerald-100 text-emerald-800 border-transparent text-xs">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Meets Minimum Value (60%)
                        </Badge>
                      ) : (
                        <Badge className="bg-rose-100 text-rose-800 border-transparent text-xs">
                          <XCircle className="w-3 h-3 mr-1" /> Below Minimum Value (60%)
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Breakdown */}
                  <div className="border rounded-md p-3">
                    <p className="text-xs font-semibold mb-2">Cost Breakdown</p>
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total allowed cost</span>
                        <span className="tabular-nums font-medium">${result.breakdown?.total_allowed_cost?.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Deductible cost</span>
                        <span className="tabular-nums">${result.breakdown?.deductible_cost?.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Coinsurance cost</span>
                        <span className="tabular-nums">${result.breakdown?.coinsurance_cost?.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Copay costs</span>
                        <span className="tabular-nums">${result.breakdown?.copay_costs?.toLocaleString()}</span>
                      </div>
                      {result.breakdown?.oop_max_applied && (
                        <div className="flex justify-between text-amber-700">
                          <span>OOP max applied</span>
                          <CheckCircle2 className="w-3 h-3" />
                        </div>
                      )}
                      <Separator className="my-1" />
                      <div className="flex justify-between font-semibold">
                        <span>Plan pays</span>
                        <span className="tabular-nums text-emerald-700">${result.breakdown?.plan_pays?.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between font-semibold">
                        <span>Member pays</span>
                        <span className="tabular-nums text-rose-700">${result.breakdown?.total_member_cost?.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Notes */}
                  {result.notes?.length > 0 && (
                    <div className="space-y-1.5">
                      {result.notes.map((note, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 p-2 rounded">
                          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span>{note}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Actuarial Cert CTA */}
                  {result.needs_actuarial_certification && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
                      <p className="text-xs font-semibold text-amber-800">Actuarial Certification Recommended</p>
                      <p className="text-[11px] text-amber-700 mt-0.5">
                        The HHS calculator flagged this plan for actuarial review. Request a certified actuary from our marketplace.
                      </p>
                      <div className="flex gap-2 mt-2">
                        <Button variant="default" size="sm" className="h-7 text-xs" onClick={() => window.location.href = '/marketplace'} data-testid="mv-go-marketplace">
                          <Store className="w-3 h-3 mr-1" /> Actuary Marketplace <ArrowRight className="w-3 h-3 ml-1" />
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 text-xs border-amber-200 text-amber-800 hover:bg-amber-100" onClick={() => window.location.href = '/certifications'} data-testid="mv-go-cert">
                          View Certifications
                        </Button>
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
