import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import { ClipboardList, Plus, Trash2, CheckCircle2, XCircle } from 'lucide-react';

const PLAN_TYPES = ['HMO', 'PPO', 'POS', 'HDHP', 'EPO'];

export default function PlansPage() {
  const { selectedEmployer, token, API } = useAuth();
  const [plans, setPlans] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    plan_name: '', plan_type: 'PPO',
    individual_deductible: '1500', family_deductible: '3000',
    coinsurance_rate: '0.20',
    office_visit_copay: '30', er_copay: '250',
    inpatient_copay: '500',
    rx_copay_generic: '15', rx_copay_brand: '45',
    oop_max_individual: '7500', oop_max_family: '15000',
    hsa_employer_contribution: '0', hra_employer_contribution: '0'
  });
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (selectedEmployer) loadPlans();
  }, [selectedEmployer]);

  const loadPlans = async () => {
    try {
      const res = await axios.get(`${API}/plans/${selectedEmployer.id}`, { headers });
      setPlans(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreate = async () => {
    if (!form.plan_name) { toast.error('Plan name is required'); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/plans`, {
        employer_id: selectedEmployer.id,
        plan_name: form.plan_name,
        plan_type: form.plan_type,
        individual_deductible: parseFloat(form.individual_deductible) || 0,
        family_deductible: parseFloat(form.family_deductible) || 0,
        coinsurance_rate: parseFloat(form.coinsurance_rate) || 0,
        office_visit_copay: parseFloat(form.office_visit_copay) || 0,
        er_copay: parseFloat(form.er_copay) || 0,
        inpatient_copay: parseFloat(form.inpatient_copay) || 0,
        rx_copay_generic: parseFloat(form.rx_copay_generic) || 0,
        rx_copay_brand: parseFloat(form.rx_copay_brand) || 0,
        oop_max_individual: parseFloat(form.oop_max_individual) || 0,
        oop_max_family: parseFloat(form.oop_max_family) || 0,
        hsa_employer_contribution: parseFloat(form.hsa_employer_contribution) || 0,
        hra_employer_contribution: parseFloat(form.hra_employer_contribution) || 0
      }, { headers });
      toast.success('Plan created');
      setShowCreate(false);
      loadPlans();
    } catch (err) {
      toast.error('Failed to create plan');
    }
    setLoading(false);
  };

  const deletePlan = async (planId) => {
    try {
      await axios.delete(`${API}/plans/detail/${planId}`, { headers });
      toast.success('Plan deleted');
      loadPlans();
    } catch (err) {
      toast.error('Failed to delete plan');
    }
  };

  const updateField = (field, value) => setForm(p => ({ ...p, [field]: value }));

  if (!selectedEmployer) {
    return <div className="p-6 text-center text-muted-foreground">Please select an employer first</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="plans-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Health Plans</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage plan designs for MV calculation and compliance tracking</p>
        </div>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button className="h-9 text-sm" data-testid="add-plan-btn">
              <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Plan
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create Health Plan</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Plan Name *</Label>
                  <Input data-testid="plan-name-input" value={form.plan_name} onChange={e => updateField('plan_name', e.target.value)} placeholder="e.g., Gold PPO" className="h-8 text-sm mt-1" />
                </div>
                <div>
                  <Label className="text-xs">Plan Type *</Label>
                  <Select value={form.plan_type} onValueChange={val => updateField('plan_type', val)}>
                    <SelectTrigger className="h-8 text-sm mt-1" data-testid="plan-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLAN_TYPES.map(t => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Deductibles</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Individual ($)</Label>
                    <Input data-testid="plan-ind-deductible" type="number" value={form.individual_deductible} onChange={e => updateField('individual_deductible', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Family ($)</Label>
                    <Input data-testid="plan-fam-deductible" type="number" value={form.family_deductible} onChange={e => updateField('family_deductible', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                </div>
              </div>

              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Coinsurance & Copays</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Coinsurance Rate (member share)</Label>
                    <Input data-testid="plan-coinsurance" type="number" step="0.01" min="0" max="1" value={form.coinsurance_rate} onChange={e => updateField('coinsurance_rate', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" placeholder="e.g., 0.20" />
                  </div>
                  <div>
                    <Label className="text-xs">Office Visit Copay ($)</Label>
                    <Input data-testid="plan-office-copay" type="number" value={form.office_visit_copay} onChange={e => updateField('office_visit_copay', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">ER Copay ($)</Label>
                    <Input data-testid="plan-er-copay" type="number" value={form.er_copay} onChange={e => updateField('er_copay', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Inpatient Copay ($)</Label>
                    <Input data-testid="plan-inpatient-copay" type="number" value={form.inpatient_copay} onChange={e => updateField('inpatient_copay', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Rx Generic Copay ($)</Label>
                    <Input data-testid="plan-rx-generic" type="number" value={form.rx_copay_generic} onChange={e => updateField('rx_copay_generic', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Rx Brand Copay ($)</Label>
                    <Input data-testid="plan-rx-brand" type="number" value={form.rx_copay_brand} onChange={e => updateField('rx_copay_brand', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                </div>
              </div>

              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Out-of-Pocket Maximums</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Individual ($)</Label>
                    <Input data-testid="plan-oop-ind" type="number" value={form.oop_max_individual} onChange={e => updateField('oop_max_individual', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">Family ($)</Label>
                    <Input data-testid="plan-oop-fam" type="number" value={form.oop_max_family} onChange={e => updateField('oop_max_family', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                </div>
              </div>

              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">HSA / HRA Contributions</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">HSA Employer ($)</Label>
                    <Input data-testid="plan-hsa" type="number" value={form.hsa_employer_contribution} onChange={e => updateField('hsa_employer_contribution', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                  <div>
                    <Label className="text-xs">HRA Employer ($)</Label>
                    <Input data-testid="plan-hra" type="number" value={form.hra_employer_contribution} onChange={e => updateField('hra_employer_contribution', e.target.value)} className="h-8 text-sm mt-1 tabular-nums" />
                  </div>
                </div>
              </div>

              <Button onClick={handleCreate} disabled={loading} className="w-full h-9 text-sm" data-testid="create-plan-submit">
                {loading ? 'Creating...' : 'Create Plan'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Plans Table */}
      <Card className="border-border/60">
        <CardContent className="p-0">
          {plans.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/60 bg-muted/30">
                  <th className="text-left px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">Plan Name</th>
                  <th className="text-center px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">Type</th>
                  <th className="text-center px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">Deductible</th>
                  <th className="text-center px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">Coinsurance</th>
                  <th className="text-center px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">OOP Max</th>
                  <th className="text-center px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">MV Status</th>
                  <th className="text-right px-4 py-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {plans.map(plan => (
                  <tr key={plan.id} className="border-b border-border/40 hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-2 font-medium">{plan.plan_name}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge variant="outline" className="text-xs">{plan.plan_type}</Badge>
                    </td>
                    <td className="px-4 py-2 text-center tabular-nums">${plan.individual_deductible?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-center tabular-nums">{(plan.coinsurance_rate * 100).toFixed(0)}%</td>
                    <td className="px-4 py-2 text-center tabular-nums">${plan.oop_max_individual?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-center">
                      {plan.mv_calculated ? (
                        plan.mv_meets_minimum ? (
                          <div className="flex items-center justify-center gap-1">
                            <Badge className="bg-emerald-50 text-emerald-700 border-transparent text-xs">
                              {plan.mv_percentage}% MV
                            </Badge>
                          </div>
                        ) : (
                          <Badge className="bg-rose-50 text-rose-700 border-transparent text-xs">
                            {plan.mv_percentage}% MV
                          </Badge>
                        )
                      ) : (
                        <span className="text-xs text-muted-foreground">Not calculated</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button variant="ghost" size="sm" className="h-6 text-xs px-2 text-destructive hover:text-destructive" onClick={() => deletePlan(plan.id)} data-testid={`delete-plan-${plan.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-4 py-8 text-center">
              <ClipboardList className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No health plans configured yet</p>
              <p className="text-xs text-muted-foreground mt-1">Add a plan to start MV calculations</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
