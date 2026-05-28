import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import {
  Plus, Upload, Shield, Trash2, Edit2, CheckCircle2, XCircle,
  DollarSign, Building2, Loader2, Download, ClipboardCheck, Users,
  Search, AlertTriangle, Check, X, Award, Ban
} from 'lucide-react';

const CATEGORIES = [
  { value: 'medical', label: 'Medical' },
  { value: 'dental', label: 'Dental' },
  { value: 'vision', label: 'Vision' },
];

const PLAN_TYPES = ['PPO', 'HMO', 'HDHP', 'EPO', 'POS'];

const EMPTY_FORM = {
  carrier_name: '', plan_name: '', plan_type: 'PPO', category: 'medical',
  premiums_self_only: '', premiums_employee_spouse: '', premiums_employee_children: '', premiums_family: '',
  employer_contribution_self_only: '', employer_contribution_employee_spouse: '',
  employer_contribution_employee_children: '', employer_contribution_family: '',
  individual_deductible: '', family_deductible: '', coinsurance_rate: '',
  oop_max_individual: '', oop_max_family: '',
  copay_primary: '', copay_specialist: '', copay_er: '',
  copay_generic_rx: '', copay_brand_rx: '',
  mv_percentage: '', mv_certified: false, mec_qualified: true,
  plan_year_start: '', plan_year_end: '', sbc_url: '',
};

export default function PlanLibraryPage() {
  const { token, API, selectedEmployer } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);
  const employerId = selectedEmployer?.id;

  // Compliance check state
  const [compliancePlan, setCompliancePlan] = useState(null);
  const [complianceData, setComplianceData] = useState(null);
  const [complianceLoading, setComplianceLoading] = useState(false);

  // Assignment state
  const [assignPlan, setAssignPlan] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [assignedIds, setAssignedIds] = useState(new Set());
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignSearch, setAssignSearch] = useState('');
  const [assignmentCounts, setAssignmentCounts] = useState({});
  const [unaffordableMap, setUnaffordableMap] = useState({}); // { empId: { pct, maxAffordable, salary } }
  const navigate = useNavigate();

  const loadPlans = useCallback(async () => {
    if (!employerId) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/enrollment/plans/${employerId}`, { headers });
      setPlans(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  }, [API, token, employerId]);

  const loadAssignmentCounts = useCallback(async () => {
    if (!employerId) return;
    try {
      const res = await axios.get(`${API}/enrollment/assignments/${employerId}`, { headers });
      const counts = {};
      res.data.forEach(a => {
        counts[a.plan_id] = (counts[a.plan_id] || 0) + 1;
      });
      setAssignmentCounts(counts);
    } catch (err) { console.error(err); }
  }, [API, token, employerId]);

  useEffect(() => { loadPlans(); loadAssignmentCounts(); }, [loadPlans, loadAssignmentCounts]);

  const setField = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    if (!form.plan_name || !form.carrier_name) { toast.error('Plan name and carrier required'); return; }
    setSubmitting(true);
    try {
      const payload = { ...form, employer_id: employerId };
      Object.keys(payload).forEach(k => {
        if (typeof payload[k] === 'string' && !isNaN(payload[k]) && payload[k] !== '' && !['carrier_name','plan_name','plan_type','category','plan_year_start','plan_year_end','sbc_url'].includes(k)) {
          payload[k] = parseFloat(payload[k]);
        }
      });
      if (editingPlan) {
        await axios.put(`${API}/enrollment/plans/${editingPlan.id}`, payload, { headers });
        toast.success('Plan updated');
      } else {
        await axios.post(`${API}/enrollment/plans`, payload, { headers });
        toast.success('Plan created');
      }
      setShowForm(false);
      setEditingPlan(null);
      setForm(EMPTY_FORM);
      loadPlans();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save plan');
    }
    setSubmitting(false);
  };

  const handleEdit = (plan) => {
    setEditingPlan(plan);
    setForm({
      carrier_name: plan.carrier_name || '',
      plan_name: plan.plan_name || '',
      plan_type: plan.plan_type || 'PPO',
      category: plan.category || 'medical',
      premiums_self_only: plan.premiums?.self_only || '',
      premiums_employee_spouse: plan.premiums?.employee_spouse || '',
      premiums_employee_children: plan.premiums?.employee_children || '',
      premiums_family: plan.premiums?.family || '',
      employer_contribution_self_only: plan.employer_contribution?.self_only || '',
      employer_contribution_employee_spouse: plan.employer_contribution?.employee_spouse || '',
      employer_contribution_employee_children: plan.employer_contribution?.employee_children || '',
      employer_contribution_family: plan.employer_contribution?.family || '',
      individual_deductible: plan.individual_deductible || '',
      family_deductible: plan.family_deductible || '',
      coinsurance_rate: plan.coinsurance_rate || '',
      oop_max_individual: plan.oop_max_individual || '',
      oop_max_family: plan.oop_max_family || '',
      copay_primary: plan.copay_primary || '',
      copay_specialist: plan.copay_specialist || '',
      copay_er: plan.copay_er || '',
      copay_generic_rx: plan.copay_generic_rx || '',
      copay_brand_rx: plan.copay_brand_rx || '',
      mv_percentage: plan.mv_percentage || '',
      mv_certified: plan.mv_certified || false,
      mec_qualified: plan.mec_qualified ?? true,
      plan_year_start: plan.plan_year_start || '',
      plan_year_end: plan.plan_year_end || '',
      sbc_url: plan.sbc_url || '',
    });
    setShowForm(true);
  };

  const handleDelete = async (planId) => {
    try {
      await axios.delete(`${API}/enrollment/plans/${planId}`, { headers });
      toast.success('Plan deleted');
      loadPlans();
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const handleUploadCSV = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await axios.post(`${API}/enrollment/plans/upload/${employerId}`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Uploaded ${res.data.created} plans${res.data.errors.length ? `, ${res.data.errors.length} errors` : ''}`);
      loadPlans();
    } catch (err) {
      toast.error('Upload failed');
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleDownloadTemplate = () => {
    const csvHeaders = 'carrier_name,plan_name,plan_type,category,premiums_self_only,premiums_employee_spouse,premiums_employee_children,premiums_family,employer_contribution_self_only,employer_contribution_employee_spouse,employer_contribution_employee_children,employer_contribution_family,individual_deductible,family_deductible,coinsurance_rate,oop_max_individual,oop_max_family,copay_primary,copay_specialist,copay_er,copay_generic_rx,copay_brand_rx,mv_percentage,mv_certified,mec_qualified,plan_year_start,plan_year_end,sbc_url';
    const sample = 'Blue Cross,Silver PPO,PPO,medical,450,900,750,1200,350,700,550,900,2000,4000,20,7000,14000,30,50,300,10,40,62,true,true,2026-01-01,2026-12-31,';
    const blob = new Blob([csvHeaders + '\n' + sample], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'plan_library_template.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  // --- Compliance Check ---
  const handleComplianceCheck = async (plan) => {
    setCompliancePlan(plan);
    setComplianceData(null);
    setComplianceLoading(true);
    try {
      const res = await axios.post(`${API}/enrollment/plans/${plan.id}/compliance-check`, {}, { headers });
      setComplianceData(res.data);
    } catch (err) {
      toast.error('Compliance check failed');
      setCompliancePlan(null);
    }
    setComplianceLoading(false);
  };

  // --- Assign Employees ---
  const handleOpenAssign = async (plan) => {
    setAssignPlan(plan);
    setAssignSearch('');
    setAffordabilityError(null);
    setAssignLoading(true);
    try {
      const [empRes, assignRes] = await Promise.all([
        axios.get(`${API}/enrollment/employees-list/${employerId}`, { headers }),
        axios.get(`${API}/enrollment/plans/${plan.id}/assigned-employees`, { headers }),
      ]);
      const empList = empRes.data;
      setEmployees(empList);
      const currentlyAssigned = new Set(assignRes.data.map(a => a.employee_id));
      setAssignedIds(currentlyAssigned);

      // Calculate affordability per employee for medical plans
      // ACA 9.96% affordability threshold applies only to full-time employees
      const uMap = {};
      if (plan.category === 'medical') {
        const eeCost = plan.employee_cost?.self_only || 0;
        const annualEeCost = eeCost * 12;
        if (eeCost > 0) {
          empList.forEach(emp => {
            const isFullTime = emp.employment_type === 'full_time';
            if (!isFullTime) return; // ACA affordability only applies to FT employees
            const salary = emp.annual_salary || 0;
            if (salary > 0) {
              const threshold = salary * 0.0996;
              if (annualEeCost > threshold) {
                uMap[emp.id] = {
                  pct: ((annualEeCost / salary) * 100).toFixed(2),
                  maxAffordable: (threshold / 12).toFixed(2),
                  salary: salary,
                  eeCost: eeCost,
                };
              }
            }
          });
        }
      }
      setUnaffordableMap(uMap);

      // Pre-select currently assigned, but exclude unaffordable ones from new selection
      const initialSelected = new Set(
        [...currentlyAssigned].filter(id => !uMap[id])
      );
      setSelectedIds(initialSelected);
    } catch (err) {
      toast.error('Failed to load employees');
      setAssignPlan(null);
    }
    setAssignLoading(false);
  };

  const toggleEmployee = (empId) => {
    if (unaffordableMap[empId]) return; // Cannot select unaffordable employee
    if (assignedIds.has(empId)) return; // Already assigned — cannot reassign or unassign
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(empId)) next.delete(empId);
      else next.add(empId);
      return next;
    });
  };

  const toggleAll = () => {
    const filtered = filteredEmployees.filter(e => !unaffordableMap[e.id] && !assignedIds.has(e.id));
    const allSelected = filtered.length > 0 && filtered.every(e => selectedIds.has(e.id));
    setSelectedIds(prev => {
      const next = new Set(prev);
      filtered.forEach(e => {
        if (allSelected) next.delete(e.id);
        else next.add(e.id);
      });
      return next;
    });
  };

  const [affordabilityError, setAffordabilityError] = useState(null);

  const handleSaveAssignments = async () => {
    if (!assignPlan) return;
    const toAssign = [...selectedIds].filter(id => !assignedIds.has(id));
    if (toAssign.length === 0) {
      toast.info('No new employees to assign');
      return;
    }
    setAssignLoading(true);
    setAffordabilityError(null);
    try {
      await axios.post(`${API}/enrollment/plans/${assignPlan.id}/assign-employees`,
        { employee_ids: toAssign }, { headers });

      toast.success(`${assignPlan.plan_name}: ${toAssign.length} new employee(s) assigned`);
      setAssignPlan(null);
      loadAssignmentCounts();
    } catch (err) {
      const resp = err.response;
      if (resp?.status === 422 && resp.data?.detail?.unaffordable_employees) {
        setAffordabilityError(resp.data.detail);
      } else {
        toast.error(resp?.data?.detail?.message || resp?.data?.detail || 'Failed to save assignments');
      }
    }
    setAssignLoading(false);
  };

  const filteredEmployees = employees.filter(e => {
    if (!assignSearch) return true;
    const q = assignSearch.toLowerCase();
    return (e.name || '').toLowerCase().includes(q) ||
           (e.email || '').toLowerCase().includes(q) ||
           (e.department || '').toLowerCase().includes(q);
  });

  const medicalPlans = plans.filter(p => p.category === 'medical');
  const dentalPlans = plans.filter(p => p.category === 'dental');
  const visionPlans = plans.filter(p => p.category === 'vision');

  if (!employerId) {
    return (
      <div className="p-6 max-w-7xl mx-auto" data-testid="plan-library-page">
        <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Plan Library</h1>
        <Card className="border-0 shadow-sm mt-4"><CardContent className="p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Building2 className="w-7 h-7 text-indigo-500" /></div>
          <p className="text-sm text-muted-foreground">Select an employer first</p>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="plan-library-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Plan Library</h1>
          <p className="text-sm text-muted-foreground mt-1">Configure carrier plans, check compliance, and assign to employees</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={handleDownloadTemplate} data-testid="download-template-btn">
            <Download className="w-3 h-3 mr-1" /> CSV Template
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="upload-csv-btn">
            {uploading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Upload className="w-3 h-3 mr-1" />} Upload CSV
          </Button>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleUploadCSV} />
          <Button size="sm" className="h-8 text-xs" onClick={() => { setEditingPlan(null); setForm(EMPTY_FORM); setShowForm(true); }} data-testid="add-plan-btn">
            <Plus className="w-3 h-3 mr-1" /> Add Plan
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      {!loading && plans.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-5">
          <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
            <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total Plans</p><p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{plans.length}</p></div><div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center"><Shield className="w-5 h-5 text-slate-600" /></div></div></CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-blue-50 to-blue-100/80 shadow-sm">
            <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-blue-500 uppercase tracking-wider font-semibold">Medical</p><p className="text-3xl font-bold tabular-nums text-blue-900 mt-1">{medicalPlans.length}</p></div><div className="w-10 h-10 rounded-xl bg-blue-200/70 flex items-center justify-center"><Shield className="w-5 h-5 text-blue-600" /></div></div></CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm">
            <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">Dental</p><p className="text-3xl font-bold tabular-nums text-emerald-900 mt-1">{dentalPlans.length}</p></div><div className="w-10 h-10 rounded-xl bg-emerald-200/70 flex items-center justify-center"><Shield className="w-5 h-5 text-emerald-600" /></div></div></CardContent>
          </Card>
          <Card className="border-0 bg-gradient-to-br from-violet-50 to-violet-100/80 shadow-sm">
            <CardContent className="p-4"><div className="flex items-center justify-between"><div><p className="text-[11px] text-violet-500 uppercase tracking-wider font-semibold">Vision</p><p className="text-3xl font-bold tabular-nums text-violet-900 mt-1">{visionPlans.length}</p></div><div className="w-10 h-10 rounded-xl bg-violet-200/70 flex items-center justify-center"><Shield className="w-5 h-5 text-violet-600" /></div></div></CardContent>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : plans.length === 0 ? (
        <Card className="border-0 shadow-sm">
          <CardContent className="p-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4"><Shield className="w-7 h-7 text-indigo-500" /></div>
            <h3 className="text-base font-bold font-[Manrope]">No Plans Configured</h3>
            <p className="text-sm text-muted-foreground mt-1">Add carrier plans manually or upload a CSV file</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-5">
          {[{ title: 'Medical Plans', plans: medicalPlans, cat: 'medical', color: 'blue' },
            { title: 'Dental Plans', plans: dentalPlans, cat: 'dental', color: 'emerald' },
            { title: 'Vision Plans', plans: visionPlans, cat: 'vision', color: 'violet' }]
            .filter(g => g.plans.length > 0)
            .map(group => (
            <div key={group.cat}>
              <h3 className="text-sm font-semibold font-[Manrope] mb-2 text-muted-foreground uppercase tracking-wider">{group.title}</h3>
              <div className="space-y-2">
                {group.plans.map(plan => (
                  <Card key={plan.id} className="border-0 shadow-sm hover:shadow-md transition-shadow duration-200" data-testid={`plan-card-${plan.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <h4 className="text-sm font-bold font-[Manrope]">{plan.plan_name}</h4>
                            <Badge variant="outline" className="text-[10px]">{plan.plan_type}</Badge>
                            {plan.mec_qualified && <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">MEC</Badge>}
                            {!plan.mec_qualified && plan.category === 'medical' && <Badge className="bg-rose-50 text-rose-700 border-rose-200 text-[10px]" data-testid={`mec-fail-badge-${plan.id}`}>MEC Fail</Badge>}
                            {(() => {
                              const erContrib = plan.employer_contribution?.self_only || 0;
                              const totalPrem = plan.premiums?.self_only || 0;
                              const erPct = totalPrem > 0 ? (erContrib / totalPrem * 100) : 0;
                              const mvPasses = plan.mv_percentage >= 60 && erPct >= 60;
                              if (mvPasses) return <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-[10px]">MV {plan.mv_percentage}%</Badge>;
                              if (plan.category === 'medical' && plan.mv_percentage != null && plan.mv_percentage < 60) return <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]" data-testid={`mv-fail-badge-${plan.id}`}>MV {plan.mv_percentage}% (Fail)</Badge>;
                              if (plan.category === 'medical' && erPct < 60) return <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]" data-testid={`mv-fail-badge-${plan.id}`}>MV Fail (ER {Math.round(erPct)}%)</Badge>;
                              return null;
                            })()}
                            {plan.certification_source === 'actuary' && (
                              <Badge className={`text-[10px] ${
                                plan.certification_status === 'accepted'
                                  ? (plan.mv_percentage >= 60 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200')
                                  : plan.certification_status === 'rejected'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                              }`} data-testid={`actuary-cert-badge-${plan.id}`}>
                                <Award className="w-2.5 h-2.5 mr-0.5" />
                                {plan.certification_status === 'accepted'
                                  ? (plan.mv_percentage >= 60 ? 'Actuary Certified' : 'Actuary Certified (Fail)')
                                  : plan.certification_status === 'rejected'
                                    ? 'Cert. Rejected'
                                    : 'Actuary Reviewed'}
                              </Badge>
                            )}
                            {assignmentCounts[plan.id] > 0 && (
                              <Badge className="bg-violet-50 text-violet-700 border-violet-200 text-[10px]" data-testid={`assignment-count-${plan.id}`}>
                                <Users className="w-2.5 h-2.5 mr-0.5" /> {assignmentCounts[plan.id]} assigned
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">{plan.carrier_name}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs">
                            <span>Self: <strong className="tabular-nums">${plan.premiums?.self_only?.toLocaleString()}</strong></span>
                            {plan.premiums?.family > 0 && <span>Family: <strong className="tabular-nums">${plan.premiums?.family?.toLocaleString()}</strong></span>}
                            <span className="text-muted-foreground">EE cost: <strong className="tabular-nums">${plan.employee_cost?.self_only?.toLocaleString()}</strong>/mo</span>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1" onClick={() => handleComplianceCheck(plan)} data-testid={`compliance-check-${plan.id}`}>
                            <ClipboardCheck className="w-3.5 h-3.5" /> Check
                          </Button>
                          {(() => {
                            const erContrib = plan.employer_contribution?.self_only || 0;
                            const totalPrem = plan.premiums?.self_only || 0;
                            const erPct = totalPrem > 0 ? (erContrib / totalPrem * 100) : 0;
                            const mvFails = plan.category === 'medical' && (
                              (plan.mv_percentage != null && plan.mv_percentage < 60) || erPct < 60
                            );
                            const mecFails = plan.category === 'medical' && !plan.mec_qualified;
                            const complianceFails = mvFails || mecFails;
                            const hasCertification = plan.certification_source === 'actuary';
                            const disableReason = mecFails && mvFails
                              ? 'Plan fails both MEC and MV requirements — assignment blocked'
                              : mecFails
                                ? 'Plan does not meet Minimum Essential Coverage (MEC) — assignment blocked'
                                : mvFails
                                  ? 'Plan does not meet Minimum Value requirements — assignment blocked'
                                  : 'Assign employees to this plan';
                            return (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className={`h-7 px-2 text-xs gap-1 ${complianceFails ? 'opacity-50 cursor-not-allowed' : ''}`}
                                  onClick={() => !complianceFails && handleOpenAssign(plan)}
                                  disabled={complianceFails}
                                  data-testid={`assign-employees-${plan.id}`}
                                  title={disableReason}
                                >
                                  <Users className="w-3.5 h-3.5" /> Assign
                                </Button>
                                {mvFails && !hasCertification && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 text-xs gap-1 text-amber-700 hover:text-amber-800 hover:bg-amber-50"
                                    onClick={() => navigate(`/marketplace?plan_id=${plan.id}`)}
                                    data-testid={`get-quote-${plan.id}`}
                                  >
                                    <Award className="w-3.5 h-3.5" /> Get Actuarial Quote
                                  </Button>
                                )}
                              </>
                            );
                          })()}
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => handleEdit(plan)} data-testid={`edit-plan-${plan.id}`}>
                            <Edit2 className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-rose-600" onClick={() => handleDelete(plan.id)} data-testid={`delete-plan-${plan.id}`}>
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Plan Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto border-0 shadow-lg">
          <DialogHeader>
            <DialogTitle className="font-[Manrope]">{editingPlan ? 'Edit Plan' : 'Add Plan'}</DialogTitle>
            <DialogDescription className="text-xs">Configure plan details, premiums, and compliance status</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Carrier Name *</Label>
                <Input value={form.carrier_name} onChange={e => setField('carrier_name', e.target.value)} className="h-8 text-sm mt-1" placeholder="e.g., Blue Cross" data-testid="plan-carrier-input" />
              </div>
              <div>
                <Label className="text-xs">Plan Name *</Label>
                <Input value={form.plan_name} onChange={e => setField('plan_name', e.target.value)} className="h-8 text-sm mt-1" placeholder="e.g., Silver PPO" data-testid="plan-name-input" />
              </div>
              <div>
                <Label className="text-xs">Plan Type</Label>
                <Select value={form.plan_type} onValueChange={v => setField('plan_type', v)}>
                  <SelectTrigger className="h-8 text-sm mt-1" data-testid="plan-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{PLAN_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Category</Label>
                <Select value={form.category} onValueChange={v => setField('category', v)}>
                  <SelectTrigger className="h-8 text-sm mt-1" data-testid="plan-category-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-xs font-semibold mb-2">Total Premiums (Monthly)</p>
              <div className="grid grid-cols-4 gap-2">
                {[['premiums_self_only','Self-Only'],['premiums_employee_spouse','EE+Spouse'],['premiums_employee_children','EE+Children'],['premiums_family','Family']].map(([k,l]) => (
                  <div key={k}>
                    <Label className="text-[10px]">{l}</Label>
                    <Input type="number" value={form[k]} onChange={e => setField(k, e.target.value)} className="h-7 text-xs mt-0.5" placeholder="$0" data-testid={`plan-${k}`} />
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold mb-2">Employer Contribution (Monthly)</p>
              <div className="grid grid-cols-4 gap-2">
                {[['employer_contribution_self_only','Self-Only'],['employer_contribution_employee_spouse','EE+Spouse'],['employer_contribution_employee_children','EE+Children'],['employer_contribution_family','Family']].map(([k,l]) => (
                  <div key={k}>
                    <Label className="text-[10px]">{l}</Label>
                    <Input type="number" value={form[k]} onChange={e => setField(k, e.target.value)} className="h-7 text-xs mt-0.5" placeholder="$0" data-testid={`plan-${k}`} />
                  </div>
                ))}
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-xs font-semibold mb-2">Plan Design</p>
              <div className="grid grid-cols-4 gap-2">
                {[['individual_deductible','Deductible (Ind)'],['family_deductible','Deductible (Fam)'],['oop_max_individual','OOP Max (Ind)'],['oop_max_family','OOP Max (Fam)'],
                  ['coinsurance_rate','Coinsurance %'],['copay_primary','PCP Copay'],['copay_specialist','Specialist'],['copay_er','ER Copay'],
                  ['copay_generic_rx','Rx Generic'],['copay_brand_rx','Rx Brand']].map(([k,l]) => (
                  <div key={k}>
                    <Label className="text-[10px]">{l}</Label>
                    <Input type="number" value={form[k]} onChange={e => setField(k, e.target.value)} className="h-7 text-xs mt-0.5" placeholder="0" />
                  </div>
                ))}
              </div>
            </div>
            <Separator />
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">MV %</Label>
                <Input type="number" value={form.mv_percentage} onChange={e => setField('mv_percentage', e.target.value)} className="h-8 text-sm mt-1" placeholder="e.g., 62" />
              </div>
              <div>
                <Label className="text-xs">Plan Year Start</Label>
                <Input type="date" value={form.plan_year_start} onChange={e => setField('plan_year_start', e.target.value)} className="h-8 text-sm mt-1" />
              </div>
              <div>
                <Label className="text-xs">Plan Year End</Label>
                <Input type="date" value={form.plan_year_end} onChange={e => setField('plan_year_end', e.target.value)} className="h-8 text-sm mt-1" />
              </div>
            </div>
            <div className="flex gap-4">
              <label className={`flex items-center gap-2 text-xs ${editingPlan && !editingPlan.mec_qualified ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                title={editingPlan && !editingPlan.mec_qualified ? 'MEC qualification cannot be manually enabled after failing compliance check' : ''}>
                <input
                  type="checkbox"
                  checked={form.mec_qualified}
                  onChange={e => setField('mec_qualified', e.target.checked)}
                  className="rounded"
                  disabled={editingPlan && !editingPlan.mec_qualified}
                  data-testid="mec-qualified-checkbox"
                />
                MEC Qualified
                {editingPlan && !editingPlan.mec_qualified && (
                  <span className="text-[10px] text-rose-500 ml-1">(Failed — locked)</span>
                )}
              </label>
              <label className="flex items-center gap-2 text-xs cursor-pointer">
                <input type="checkbox" checked={form.mv_certified} onChange={e => setField('mv_certified', e.target.checked)} className="rounded" data-testid="mv-certified-checkbox" />
                MV Certified
              </label>
            </div>
            <div>
              <Label className="text-xs">SBC URL</Label>
              <Input value={form.sbc_url} onChange={e => setField('sbc_url', e.target.value)} className="h-8 text-sm mt-1" placeholder="https://..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)} className="h-9 text-sm">Cancel</Button>
            <Button onClick={handleSubmit} disabled={submitting} className="h-9 text-sm" data-testid="save-plan-btn">
              {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editingPlan ? 'Update Plan' : 'Create Plan'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Compliance Check Dialog */}
      <Dialog open={!!compliancePlan} onOpenChange={(open) => { if (!open) setCompliancePlan(null); }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto border-0 shadow-lg" data-testid="compliance-dialog">
          <DialogHeader>
            <DialogTitle className="font-[Manrope] flex items-center gap-2">
              <ClipboardCheck className="w-5 h-5" /> Compliance Check
            </DialogTitle>
            <DialogDescription className="text-xs">{compliancePlan?.plan_name} - {compliancePlan?.carrier_name}</DialogDescription>
          </DialogHeader>
          {complianceLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : complianceData ? (
            <div className="space-y-4">
              {/* Overall Status */}
              <div className={`p-3 rounded-lg border ${complianceData.overall_compliant ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
                <div className="flex items-center gap-2">
                  {complianceData.overall_compliant
                    ? <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    : <AlertTriangle className="w-5 h-5 text-amber-600" />}
                  <span className="text-sm font-semibold">
                    {complianceData.overall_compliant ? 'ACA Compliant' : 'Compliance Issues Found'}
                  </span>
                </div>
              </div>

              {/* MEC Check */}
              <div className="border rounded-lg p-3" data-testid="mec-check-result">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold font-[Manrope]">MEC (Minimum Essential Coverage)</h4>
                  <StatusBadge pass={complianceData.mec.pass} />
                </div>
                <div className="space-y-1">
                  {Object.entries(complianceData.mec.checks).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                      {val ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-rose-500" />}
                    </div>
                  ))}
                </div>
              </div>

              {/* MV Check — HHS Calculator */}
              <div className="border rounded-lg p-3" data-testid="mv-check-result">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold font-[Manrope]">MV (Minimum Value) — HHS Calculator</h4>
                  <StatusBadge pass={complianceData.mv.pass} />
                </div>
                <div className="space-y-1.5">
                  {/* Calculated MV */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Calculated MV %</span>
                    <span className={`font-bold tabular-nums text-sm ${complianceData.mv.actuarial_pass ? 'text-emerald-700' : 'text-rose-600'}`}>{complianceData.mv.mv_percentage}%</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Required Threshold</span>
                    <span className="font-semibold tabular-nums">60%</span>
                  </div>
                  <Progress value={Math.min(100, (complianceData.mv.mv_percentage / 60) * 100)} className="h-2 mt-0.5" />

                  {/* Plan Parameters Used */}
                  {complianceData.mv.plan_parameters && (
                    <>
                      <Separator className="my-1" />
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Plan Parameters</p>
                      <div className="grid grid-cols-3 gap-1">
                        <div className="bg-slate-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-muted-foreground">Deductible</p>
                          <p className="text-xs font-bold tabular-nums">${complianceData.mv.plan_parameters.deductible?.toLocaleString()}</p>
                        </div>
                        <div className="bg-slate-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-muted-foreground">Coinsurance</p>
                          <p className="text-xs font-bold tabular-nums">{complianceData.mv.plan_parameters.coinsurance}%</p>
                        </div>
                        <div className="bg-slate-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-muted-foreground">OOP Max</p>
                          <p className="text-xs font-bold tabular-nums">${complianceData.mv.plan_parameters.oop_max?.toLocaleString()}</p>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Cost Breakdown */}
                  {complianceData.mv.total_allowed_cost && (
                    <>
                      <Separator className="my-1" />
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Standard Population Cost Analysis</p>
                      <div className="grid grid-cols-3 gap-1">
                        <div className="bg-blue-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-blue-600">Total Allowed</p>
                          <p className="text-xs font-bold tabular-nums text-blue-700">${complianceData.mv.total_allowed_cost?.toLocaleString()}</p>
                        </div>
                        <div className="bg-emerald-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-emerald-600">Plan Pays</p>
                          <p className="text-xs font-bold tabular-nums text-emerald-700">${complianceData.mv.plan_pays?.toLocaleString()}</p>
                        </div>
                        <div className="bg-rose-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-rose-600">Member Pays</p>
                          <p className="text-xs font-bold tabular-nums text-rose-700">${complianceData.mv.member_pays?.toLocaleString()}</p>
                        </div>
                      </div>
                      {complianceData.mv.oop_max_applied && (
                        <p className="text-[10px] text-amber-600 font-medium">OOP Maximum was applied — capped member costs</p>
                      )}
                    </>
                  )}

                  {/* Category Breakdown Table */}
                  {complianceData.mv.category_breakdown && complianceData.mv.category_breakdown.length > 0 && (
                    <>
                      <Separator className="my-1" />
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Service Category Breakdown</p>
                      <div className="border rounded overflow-hidden">
                        <table className="w-full text-[10px]">
                          <thead>
                            <tr className="bg-slate-50">
                              <th className="px-2 py-1 text-left font-semibold text-muted-foreground">Category</th>
                              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">Cost</th>
                              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">Copays</th>
                              <th className="px-2 py-1 text-right font-semibold text-emerald-600">Plan</th>
                              <th className="px-2 py-1 text-right font-semibold text-rose-600">Member</th>
                            </tr>
                          </thead>
                          <tbody>
                            {complianceData.mv.category_breakdown.map((cat, i) => (
                              <tr key={i} className={i % 2 === 0 ? '' : 'bg-slate-50/50'}>
                                <td className="px-2 py-0.5 font-medium">{cat.category}</td>
                                <td className="px-2 py-0.5 text-right tabular-nums">${cat.total_cost?.toLocaleString()}</td>
                                <td className="px-2 py-0.5 text-right tabular-nums">${cat.copays}</td>
                                <td className="px-2 py-0.5 text-right tabular-nums text-emerald-700">${cat.plan_pays?.toLocaleString()}</td>
                                <td className="px-2 py-0.5 text-right tabular-nums text-rose-600">${cat.employee_cost?.toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}

                  {/* Premium / Contribution Analysis */}
                  {complianceData.mv.premium_analysis && (
                    <>
                      <Separator className="my-1" />
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Monthly Premium Analysis (Self-Only)</p>
                      <div className="grid grid-cols-3 gap-1">
                        <div className="bg-slate-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-muted-foreground">Total Premium</p>
                          <p className="text-xs font-bold tabular-nums">${complianceData.mv.premium_analysis.total_monthly_premium}</p>
                        </div>
                        <div className="bg-emerald-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-emerald-600">Employer Pays</p>
                          <p className="text-xs font-bold tabular-nums text-emerald-700">${complianceData.mv.premium_analysis.employer_contribution}</p>
                        </div>
                        <div className="bg-rose-50 rounded p-1.5 text-center">
                          <p className="text-[9px] text-rose-600">Employee Pays</p>
                          <p className="text-xs font-bold tabular-nums text-rose-700">${complianceData.mv.premium_analysis.employee_premium}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs mt-1">
                        <span className="text-muted-foreground">Employer Contribution %</span>
                        <span className="font-semibold tabular-nums">{complianceData.mv.premium_analysis.employer_pct}%</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Min. Required (60%)</span>
                        {complianceData.mv.employer_contribution_pass
                          ? <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">Pass</Badge>
                          : <Badge className="bg-rose-50 text-rose-700 border-rose-200 text-[10px]">Fail — Below 60%</Badge>}
                      </div>
                    </>
                  )}

                  {/* Calculation Notes */}
                  {complianceData.mv.calculation_notes && complianceData.mv.calculation_notes.length > 0 && (
                    <>
                      <Separator className="my-1" />
                      {complianceData.mv.calculation_notes.map((note, i) => (
                        <p key={i} className="text-[10px] text-amber-600 font-medium flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> {note}
                        </p>
                      ))}
                    </>
                  )}

                  <Separator className="my-1" />
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Method</span>
                    <span className="font-semibold">{complianceData.mv.method}</span>
                  </div>

                  {complianceData.mv.certified_by_actuary && (
                    <>
                      <Separator className="my-1.5" />
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Actuarial Certification</span>
                        {complianceData.mv.certified_by_actuary.pass
                          ? <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">Certified — Pass</Badge>
                          : <Badge className="bg-rose-50 text-rose-700 border-rose-200 text-[10px]">Certified — Fail</Badge>}
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Certified By</span>
                        <span className="font-semibold">{complianceData.mv.certified_by_actuary.actuary_name || '—'}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Actuary MV Result</span>
                        <span className="font-semibold tabular-nums">{complianceData.mv.certified_by_actuary.mv_percentage}%</span>
                      </div>
                    </>
                  )}

                  {!complianceData.mv.certified_by_actuary && complianceData.mv.has_active_quote && (
                    <>
                      <Separator className="my-1.5" />
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Certification Request</span>
                        <Badge variant="outline" className="text-[10px] capitalize">{complianceData.mv.active_quote_status}</Badge>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Affordability Check */}
              <div className="border rounded-lg p-3" data-testid="affordability-check-result">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold font-[Manrope]">Affordability (W-2 Safe Harbor)</h4>
                  <StatusBadge pass={complianceData.affordability.pass_rate >= 95} />
                </div>
                <div className="space-y-1.5">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-3 gap-1">
                    <div className="bg-slate-50 rounded p-1.5 text-center">
                      <p className="text-[9px] text-muted-foreground">Employee Cost</p>
                      <p className="text-xs font-bold tabular-nums">${complianceData.affordability.employee_monthly_cost}/mo</p>
                    </div>
                    <div className="bg-slate-50 rounded p-1.5 text-center">
                      <p className="text-[9px] text-muted-foreground">ACA Threshold</p>
                      <p className="text-xs font-bold tabular-nums">{complianceData.affordability.threshold_rate}% of W-2</p>
                    </div>
                    <div className="bg-slate-50 rounded p-1.5 text-center">
                      <p className="text-[9px] text-muted-foreground">Pass Rate</p>
                      <p className={`text-xs font-bold tabular-nums ${complianceData.affordability.pass_rate >= 95 ? 'text-emerald-700' : 'text-rose-600'}`}>{complianceData.affordability.pass_rate}%</p>
                    </div>
                  </div>
                  <Progress value={complianceData.affordability.pass_rate} className="h-2" />

                  {/* Affordable / Unaffordable counts */}
                  <div className="flex items-center gap-3 mt-1">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                      <span className="text-[10px] font-semibold text-emerald-700">{complianceData.affordability.affordable_for} Affordable</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                      <span className="text-[10px] font-semibold text-rose-600">{complianceData.affordability.unaffordable_for} Unaffordable</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground ml-auto">{complianceData.affordability.total_employees_checked} of {complianceData.affordability.total_ft_employees} FT checked</span>
                  </div>

                  {/* Per-Employee Breakdown */}
                  {complianceData.affordability.employees && complianceData.affordability.employees.length > 0 && (
                    <AffordabilityEmployeeList employees={complianceData.affordability.employees} eeCost={complianceData.affordability.employee_monthly_cost} />
                  )}

                  <p className="text-[10px] text-muted-foreground mt-1">Evaluated per ACA: FT (30+ hrs/wk) and FTE (130+ monthly hrs) only. Must pass for 95%+ of employees.</p>
                </div>
              </div>
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompliancePlan(null)} className="h-9 text-sm">Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Employees Dialog */}
      <Dialog open={!!assignPlan} onOpenChange={(open) => { if (!open) setAssignPlan(null); }}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col" data-testid="assign-dialog">
          <DialogHeader>
            <DialogTitle className="font-[Manrope] flex items-center gap-2">
              <Users className="w-5 h-5" /> Assign Employees
            </DialogTitle>
            <DialogDescription className="text-xs">
              Select employees to offer <strong>{assignPlan?.plan_name}</strong> ({assignPlan?.carrier_name})
            </DialogDescription>
          </DialogHeader>
          {assignLoading && !employees.length ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : (
            <>
              <div className="flex items-center gap-3 mb-1">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                  <Input
                    value={assignSearch}
                    onChange={e => setAssignSearch(e.target.value)}
                    className="h-8 text-sm pl-8"
                    placeholder="Search by name, email, or department..."
                    data-testid="assign-search-input"
                  />
                </div>
                <Button variant="outline" size="sm" className="h-8 text-xs whitespace-nowrap" onClick={toggleAll} data-testid="assign-toggle-all">
                  {filteredEmployees.filter(e => !unaffordableMap[e.id] && !assignedIds.has(e.id)).length > 0 && filteredEmployees.filter(e => !unaffordableMap[e.id] && !assignedIds.has(e.id)).every(e => selectedIds.has(e.id)) ? 'Deselect All' : 'Select All'}
                </Button>
              </div>
              {Object.keys(unaffordableMap).length > 0 && (
                <div className="flex items-center gap-2 mb-2 px-2 py-1.5 rounded-md bg-amber-50 border border-amber-200">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <p className="text-[11px] text-amber-800">
                    <strong>{Object.keys(unaffordableMap).length} employee(s)</strong> cannot be assigned — plan exceeds the ACA 9.96% affordability threshold based on their salary.
                  </p>
                </div>
              )}
              <div className="text-xs text-muted-foreground mb-2">
                {assignedIds.size > 0 && (
                  <span className="text-blue-600 font-medium">{assignedIds.size} already assigned</span>
                )}
                {assignedIds.size > 0 && selectedIds.size > assignedIds.size && <span> · </span>}
                {selectedIds.size > assignedIds.size && (
                  <span className="text-primary font-medium">{selectedIds.size - assignedIds.size} new to assign</span>
                )}
                {selectedIds.size === assignedIds.size && assignedIds.size === 0 && (
                  <span>0 selected</span>
                )}
              </div>
              <TooltipProvider delayDuration={200}>
              <div className="border rounded-lg overflow-y-auto flex-1 max-h-[400px]">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr>
                      <th className="w-10 py-2 px-3 text-left"></th>
                      <th className="py-2 px-3 text-left font-semibold">Employee</th>
                      <th className="py-2 px-3 text-left font-semibold">Department</th>
                      <th className="py-2 px-3 text-left font-semibold">Type</th>
                      <th className="py-2 px-3 text-right font-semibold">Salary</th>
                      <th className="py-2 px-3 text-right font-semibold">Hours/Week</th>
                      <th className="py-2 px-3 text-center font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map(emp => {
                      const isSelected = selectedIds.has(emp.id);
                      const isUnaffordable = !!unaffordableMap[emp.id];
                      const isAlreadyAssigned = assignedIds.has(emp.id);
                      const affordInfo = unaffordableMap[emp.id];
                      const rowContent = (
                        <tr
                          key={emp.id}
                          className={`border-t border-border/40 transition-colors ${
                            isAlreadyAssigned
                              ? 'bg-blue-50/40 cursor-default'
                              : isUnaffordable
                                ? 'bg-rose-50/40 cursor-not-allowed opacity-70'
                                : isSelected
                                  ? 'bg-primary/5 cursor-pointer'
                                  : 'hover:bg-muted/30 cursor-pointer'
                          }`}
                          onClick={() => toggleEmployee(emp.id)}
                          data-testid={`assign-row-${emp.id}`}
                        >
                          <td className="py-2 px-3">
                            {isAlreadyAssigned ? (
                              <div className="w-4 h-4 rounded border-2 border-emerald-500 bg-emerald-500 flex items-center justify-center">
                                <Check className="w-2.5 h-2.5 text-white" />
                              </div>
                            ) : isUnaffordable ? (
                              <div className="w-4 h-4 rounded border-2 border-rose-300 bg-rose-100 flex items-center justify-center">
                                <Ban className="w-2.5 h-2.5 text-rose-400" />
                              </div>
                            ) : (
                              <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/30'}`}>
                                {isSelected && <Check className="w-2.5 h-2.5 text-white" />}
                              </div>
                            )}
                          </td>
                          <td className="py-2 px-3">
                            <p className={`font-medium ${isUnaffordable ? 'text-muted-foreground' : ''}`}>{emp.name}</p>
                            <p className="text-muted-foreground">{emp.email || ''}</p>
                          </td>
                          <td className="py-2 px-3 text-muted-foreground">{emp.department || '-'}</td>
                          <td className="py-2 px-3">
                            <Badge variant="outline" className="text-[10px] capitalize">{emp.employment_type || 'N/A'}</Badge>
                          </td>
                          <td className="py-2 px-3 text-right tabular-nums">{emp.annual_salary ? `$${emp.annual_salary.toLocaleString()}` : '-'}</td>
                          <td className="py-2 px-3 text-right tabular-nums">{emp.weekly_hours || '-'}</td>
                          <td className="py-2 px-3 text-center">
                            {isAlreadyAssigned ? (
                              <Badge className="bg-blue-100 text-blue-700 border-blue-200 text-[9px]">
                                <Check className="w-2.5 h-2.5 mr-0.5" /> Assigned
                              </Badge>
                            ) : isUnaffordable ? (
                              <Badge className="bg-rose-100 text-rose-700 border-rose-200 text-[9px]">
                                <AlertTriangle className="w-2.5 h-2.5 mr-0.5" /> Unaffordable
                              </Badge>
                            ) : (
                              <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[9px]">Eligible</Badge>
                            )}
                          </td>
                        </tr>
                      );

                      if (isUnaffordable && affordInfo) {
                        return (
                          <Tooltip key={emp.id}>
                            <TooltipTrigger asChild>
                              {rowContent}
                            </TooltipTrigger>
                            <TooltipContent side="left" className="max-w-xs bg-rose-900 text-white border-rose-800">
                              <div className="space-y-1">
                                <p className="font-semibold">Plan Unaffordable for {emp.name}</p>
                                <p>EE cost: <strong>${affordInfo.eeCost}/mo</strong> exceeds 9.96% of ${affordInfo.salary.toLocaleString()} salary</p>
                                <p>Max affordable: <strong>${affordInfo.maxAffordable}/mo</strong> | Actual: <strong>{affordInfo.pct}%</strong> of income</p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        );
                      }
                      return rowContent;
                    })}
                    {filteredEmployees.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-muted-foreground">No employees found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              </TooltipProvider>
            </>
          )}
          {/* Affordability Error Block */}
          {affordabilityError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50/80 p-4 mt-2" data-testid="affordability-error-block">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-rose-100 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle className="w-5 h-5 text-rose-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-rose-800 font-[Manrope]">Assignment Blocked — Plan Unaffordable</p>
                  <p className="text-xs text-rose-700 mt-1">{affordabilityError.message}</p>
                  {affordabilityError.unaffordable_employees?.length > 0 && (
                    <div className="mt-3 border border-rose-200 rounded-md overflow-hidden">
                      <table className="w-full text-xs">
                        <thead className="bg-rose-100/70">
                          <tr>
                            <th className="py-1.5 px-3 text-left font-semibold text-rose-800">Employee</th>
                            <th className="py-1.5 px-3 text-right font-semibold text-rose-800">Salary</th>
                            <th className="py-1.5 px-3 text-right font-semibold text-rose-800">EE Cost/mo</th>
                            <th className="py-1.5 px-3 text-right font-semibold text-rose-800">Max Affordable</th>
                            <th className="py-1.5 px-3 text-right font-semibold text-rose-800">% of Income</th>
                          </tr>
                        </thead>
                        <tbody>
                          {affordabilityError.unaffordable_employees.map((emp, i) => (
                            <tr key={emp.employee_id} className={i % 2 === 0 ? 'bg-white' : 'bg-rose-50/50'} data-testid={`unaffordable-row-${emp.employee_id}`}>
                              <td className="py-1.5 px-3 font-medium text-rose-900">{emp.name}</td>
                              <td className="py-1.5 px-3 text-right tabular-nums text-rose-800">${emp.annual_salary?.toLocaleString()}</td>
                              <td className="py-1.5 px-3 text-right tabular-nums text-rose-800">${emp.employee_monthly_cost}</td>
                              <td className="py-1.5 px-3 text-right tabular-nums text-emerald-700 font-medium">${emp.max_affordable_monthly}</td>
                              <td className="py-1.5 px-3 text-right tabular-nums">
                                <span className="text-rose-700 font-semibold">{emp.pct_of_income}%</span>
                                <span className="text-rose-500 ml-1">(max {emp.threshold}%)</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <Button variant="outline" size="sm" className="mt-3 h-7 text-xs border-rose-300 text-rose-700 hover:bg-rose-100" onClick={() => setAffordabilityError(null)} data-testid="dismiss-affordability-error">
                    <X className="w-3 h-3 mr-1" /> Dismiss
                  </Button>
                </div>
              </div>
            </div>
          )}
          <DialogFooter className="mt-2">
            <Button variant="outline" onClick={() => setAssignPlan(null)} className="h-9 text-sm">Cancel</Button>
            <Button onClick={handleSaveAssignments} disabled={assignLoading || selectedIds.size === assignedIds.size} className="h-9 text-sm" data-testid="save-assignments-btn">
              {assignLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
              {selectedIds.size > assignedIds.size ? `Assign ${selectedIds.size - assignedIds.size} New` : 'No New Assignments'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatusBadge({ pass }) {
  return pass ? (
    <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]" data-testid="status-pass">
      <CheckCircle2 className="w-3 h-3 mr-0.5" /> Pass
    </Badge>
  ) : (
    <Badge className="bg-rose-50 text-rose-700 border-rose-200 text-[10px]" data-testid="status-fail">
      <XCircle className="w-3 h-3 mr-0.5" /> Fail
    </Badge>
  );
}


function AffordabilityEmployeeList({ employees, eeCost }) {
  const [expanded, setExpanded] = useState(false);
  const [filter, setFilter] = useState('all'); // 'all', 'affordable', 'unaffordable'

  const filtered = filter === 'all' ? employees
    : filter === 'affordable' ? employees.filter(e => e.affordable)
    : employees.filter(e => !e.affordable);

  const displayed = expanded ? filtered : filtered.slice(0, 5);
  const hasMore = filtered.length > 5;

  return (
    <div className="mt-1.5" data-testid="affordability-employee-list">
      <Separator className="mb-1.5" />
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Employee Breakdown</p>
        <div className="flex gap-0.5 bg-slate-100 rounded-md p-0.5">
          {[
            { key: 'all', label: 'All' },
            { key: 'affordable', label: 'Can Afford' },
            { key: 'unaffordable', label: 'Cannot' },
          ].map(f => (
            <button key={f.key} onClick={() => { setFilter(f.key); setExpanded(false); }}
              className={`px-2 py-0.5 rounded text-[9px] font-semibold transition-all ${filter === f.key ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              data-testid={`filter-${f.key}`}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="border rounded overflow-hidden">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="bg-slate-50">
              <th className="px-2 py-1 text-left font-semibold text-muted-foreground">Employee</th>
              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">Salary</th>
              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">Max Affordable</th>
              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">Plan Cost</th>
              <th className="px-2 py-1 text-right font-semibold text-muted-foreground">% of Income</th>
              <th className="px-2 py-1 text-center font-semibold text-muted-foreground">Status</th>
            </tr>
          </thead>
          <tbody>
            {displayed.map((emp, i) => (
              <tr key={emp.employee_id || i}
                className={`${i % 2 === 0 ? '' : 'bg-slate-50/50'} ${!emp.affordable ? 'bg-rose-50/40' : ''}`}
                data-testid={`emp-row-${emp.employee_id}`}>
                <td className="px-2 py-1 font-medium truncate max-w-[120px]">{emp.name}</td>
                <td className="px-2 py-1 text-right tabular-nums">${(emp.annual_salary / 1000).toFixed(0)}k</td>
                <td className="px-2 py-1 text-right tabular-nums text-muted-foreground">${emp.monthly_threshold?.toFixed(0)}/mo</td>
                <td className="px-2 py-1 text-right tabular-nums">${eeCost}/mo</td>
                <td className={`px-2 py-1 text-right tabular-nums font-semibold ${emp.pct_of_income > 9.96 ? 'text-rose-600' : 'text-emerald-700'}`}>
                  {emp.pct_of_income}%
                </td>
                <td className="px-2 py-1 text-center">
                  {emp.affordable
                    ? <span className="inline-flex items-center gap-0.5 text-emerald-700 font-bold"><CheckCircle2 className="w-3 h-3" /></span>
                    : <span className="inline-flex items-center gap-0.5 text-rose-600 font-bold"><XCircle className="w-3 h-3" /></span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasMore && (
        <button onClick={() => setExpanded(!expanded)}
          className="w-full text-center py-1 text-[10px] font-semibold text-indigo-600 hover:text-indigo-800 transition"
          data-testid="toggle-employee-list">
          {expanded ? 'Show less' : `Show all ${filtered.length} employees`}
        </button>
      )}
    </div>
  );
}
