import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import axios from 'axios';
import {
  ArrowLeft, User, Briefcase, Clock, ShieldCheck, FileBarChart,
  CheckCircle2, XCircle, AlertTriangle, DollarSign, Heart, Users
} from 'lucide-react';

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const { token, API } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadProfile();
  }, [employeeId]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/employee-compliance/${employeeId}`, { headers });
      setData(res.data);
    } catch (err) {
      toast.error('Failed to load employee');
    }
    setLoading(false);
  };

  if (loading) return <div className="p-6 flex justify-center"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (!data) return <div className="p-6 text-center text-muted-foreground">Employee not found</div>;

  const { employee: emp, plan, assigned_plans = [], has_assignments, eligibility_status, mec_offered, affordability, subsidy_eligible, subsidy_reason } = data;

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="employee-profile-page">
      <Button variant="ghost" size="sm" onClick={() => navigate('/employees')} className="mb-3 -ml-2 h-7 text-xs" data-testid="back-to-employees">
        <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Employees
      </Button>

      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-xl font-bold text-primary">
            {emp.name?.charAt(0)}
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">{emp.name}</h1>
            <p className="text-sm text-muted-foreground">{emp.job_title} - {emp.department}</p>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className={`text-xs ${emp.is_full_time ? 'border-emerald-200 text-emerald-700 bg-emerald-50' : 'border-blue-200 text-blue-700 bg-blue-50'}`}>
                {emp.is_full_time ? 'Full-Time' : 'Part-Time'}
              </Badge>
              <Badge className={`text-xs border-transparent ${
                eligibility_status === 'eligible' ? 'bg-emerald-50 text-emerald-700' :
                eligibility_status === 'waiting_period' ? 'bg-amber-50 text-amber-700' :
                'bg-gray-50 text-gray-600'}`}>
                {eligibility_status === 'eligible' ? 'Eligible' : eligibility_status === 'waiting_period' ? 'Waiting Period' : 'Not Eligible'}
              </Badge>
            </div>
          </div>
        </div>
        {/* Subsidy Indicator - Removed */}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Col 1: Personal & Employment */}
        <div className="space-y-4">
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-blue-400 to-indigo-400" />
            <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-blue-500" /> Personal Details</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Email</span><span className="text-xs font-semibold text-slate-800">{emp.email || '-'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Phone</span><span className="text-xs font-semibold text-slate-800">{emp.phone || '-'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">SSN (last 4)</span><span className="text-xs font-semibold text-slate-800">***-**-{emp.ssn_last4 || '****'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Address</span><span className="text-xs font-semibold text-slate-800 text-right max-w-[180px]">{emp.address || '-'}</span></div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-emerald-400 to-teal-400" />
            <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold flex items-center gap-1.5"><Briefcase className="w-3.5 h-3.5 text-emerald-500" /> Employment Data</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Hire Date</span><span className="text-xs font-semibold text-slate-800">{emp.hire_date || '-'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Job Title</span><span className="text-xs font-semibold text-slate-800">{emp.job_title || '-'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Department</span><span className="text-xs font-semibold text-slate-800">{emp.department || '-'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Weekly Hours</span><span className="text-xs font-semibold text-slate-800 tabular-nums">{emp.weekly_hours}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Monthly Hours</span><span className="text-xs font-semibold text-slate-800 tabular-nums">{emp.monthly_hours}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">Annual Salary</span><span className="text-xs font-semibold text-slate-800 tabular-nums">${emp.annual_salary?.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-500 text-xs">W-2 Wages</span><span className="text-xs font-semibold text-slate-800 tabular-nums">${emp.w2_wages?.toLocaleString()}</span></div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-violet-400 to-purple-400" />
            <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold flex items-center gap-1.5"><Users className="w-3.5 h-3.5 text-violet-500" /> Dependents</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4 text-sm">
              {emp.spouse_name && <div className="flex justify-between mb-1"><span className="text-muted-foreground text-xs">Spouse</span><span className="text-xs font-medium">{emp.spouse_name}</span></div>}
              <div className="flex justify-between mb-2"><span className="text-muted-foreground text-xs">Dependents</span><span className="text-xs font-medium">{emp.num_dependents}</span></div>
              {emp.dependents?.map((dep, i) => (
                <div key={i} className="flex justify-between text-xs pl-2 border-l-2 border-slate-200 ml-1 mb-1">
                  <span className="text-muted-foreground">{dep.name}</span>
                  <span>Age {dep.age}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Col 2: Coverage & Plan — only if plans assigned */}
        <div className="space-y-4">
          {has_assignments ? (
            <>
              {assigned_plans.map((ap, idx) => (
                <Card key={idx} className="border-0 shadow-sm overflow-hidden">
                  <div className="h-1 bg-gradient-to-r from-rose-400 to-pink-400" />
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                      <Heart className="w-3.5 h-3.5 text-rose-500" /> {ap.plan?.category === 'medical' ? 'Medical' : ap.plan?.category === 'dental' ? 'Dental' : 'Vision'} Plan
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4 space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-muted-foreground text-xs">Plan Name</span><span className="text-xs font-medium">{ap.plan?.plan_name}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground text-xs">Carrier</span><span className="text-xs font-medium">{ap.plan?.carrier || '-'}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground text-xs">Plan Type</span><span className="text-xs font-medium">{ap.plan?.plan_type || '-'}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground text-xs">Assigned On</span><span className="text-xs font-medium">{ap.assignment?.assigned_at ? new Date(ap.assignment.assigned_at).toLocaleDateString() : '-'}</span></div>
                    {ap.plan?.individual_deductible != null && (
                      <>
                        <Separator className="my-1" />
                        <div className="flex justify-between"><span className="text-muted-foreground text-xs">Deductible</span><span className="text-xs font-medium tabular-nums">${ap.plan.individual_deductible?.toLocaleString()}</span></div>
                        {ap.plan?.coinsurance_rate != null && <div className="flex justify-between"><span className="text-muted-foreground text-xs">Coinsurance</span><span className="text-xs font-medium tabular-nums">{ap.plan.coinsurance_rate <= 1 ? (ap.plan.coinsurance_rate * 100).toFixed(0) : ap.plan.coinsurance_rate}%</span></div>}
                        {ap.plan?.oop_max_individual != null && <div className="flex justify-between"><span className="text-muted-foreground text-xs">OOP Max</span><span className="text-xs font-medium tabular-nums">${ap.plan.oop_max_individual?.toLocaleString()}</span></div>}
                      </>
                    )}
                    {ap.plan?.mec_qualified != null && (
                      <>
                        <Separator className="my-1" />
                        <div className="flex items-center justify-between">
                          <div className="flex gap-2">
                            {ap.plan.mec_qualified && <Badge className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200">MEC</Badge>}
                            {ap.plan.mv_percentage != null && <Badge className={`text-[10px] ${ap.plan.mv_percentage >= 60 ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>MV {ap.plan.mv_percentage}%</Badge>}
                          </div>
                        </div>
                      </>
                    )}
                    <Separator className="my-1" />
                    {/* Offer Code */}
                    {(() => {
                      const isMec = ap.plan?.mec_qualified;
                      const mvPass = (ap.plan?.mv_percentage || 0) >= 60;
                      const isFt = emp.is_full_time;
                      const tier = emp.coverage_tier || 'individual';
                      let code = '1H', meaning = 'No offer / non-MEC';
                      if (!isMec) { code = '1H'; meaning = 'Non-MEC plan offered'; }
                      else if (!isFt) { code = '1G'; meaning = 'Offer to non-full-time employee'; }
                      else if (isMec && !mvPass) { code = '1F'; meaning = 'MEC offered, MV below 60%'; }
                      else if (isMec && mvPass && (tier === 'family' || tier === 'employee_spouse_dependents')) { code = '1E'; meaning = 'MEC + MV to employee, spouse & dependents'; }
                      else if (isMec && mvPass && tier === 'employee_spouse') { code = '1D'; meaning = 'MEC + MV to employee + spouse'; }
                      else if (isMec && mvPass && (tier === 'employee_children' || tier === 'employee_dependents')) { code = '1C'; meaning = 'MEC + MV to employee + dependents'; }
                      else if (isMec && mvPass) { code = '1B'; meaning = 'MEC + MV to employee only'; }
                      return (
                        <div className="flex justify-between items-start">
                          <span className="text-muted-foreground text-xs">Offer Code</span>
                          <div className="text-right">
                            <Badge variant="outline" className="text-[10px] font-bold tabular-nums">{code}</Badge>
                            <p className="text-[10px] text-muted-foreground mt-0.5">{meaning}</p>
                          </div>
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>
              ))}
            </>
          ) : (
            <Card className="border-0 shadow-sm overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-slate-300 to-slate-400" />
              <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold flex items-center gap-1.5"><Heart className="w-3.5 h-3.5 text-slate-400" /> Coverage Details</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="py-6 text-center">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-3"><Heart className="w-6 h-6 text-slate-400" /></div>
                  <p className="text-xs text-muted-foreground">No plans assigned yet</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Assign plans in the Plan Library</p>
                </div>
                <Separator className="my-2" />
                <div className="flex justify-between items-start">
                  <span className="text-muted-foreground text-xs">Offer Code</span>
                  <div className="text-right">
                    <Badge variant="outline" className="text-[10px] font-bold tabular-nums bg-rose-50 border-rose-200 text-rose-700">1H</Badge>
                    <p className="text-[10px] text-muted-foreground mt-0.5">No offer / no plan assigned</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Col 3: Compliance Status */}
        <div className="space-y-4">
          <Card className="border-0 shadow-sm overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-amber-400 to-orange-400" />
            <CardHeader className="py-3 px-4"><CardTitle className="text-sm font-bold flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5 text-amber-500" /> Compliance Status</CardTitle></CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              {/* Eligibility */}
              <div className={`p-2.5 rounded-md border ${eligibility_status === 'eligible' ? 'bg-emerald-50/50 border-emerald-100' : eligibility_status === 'waiting_period' ? 'bg-amber-50/50 border-amber-100' : 'bg-gray-50 border-gray-100'}`}>
                <div className="flex items-center gap-1.5 text-xs">
                  {eligibility_status === 'eligible' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : eligibility_status === 'waiting_period' ? <Clock className="w-3.5 h-3.5 text-amber-600" /> : <XCircle className="w-3.5 h-3.5 text-gray-500" />}
                  <span className="font-semibold">Eligibility Determination</span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5 ml-5">{emp.monthly_hours} hrs/mo {emp.monthly_hours >= 130 ? '>= 130 threshold' : '< 130 threshold'}</p>
              </div>

              {/* Coverage Status */}
              <div className={`p-2.5 rounded-md border ${has_assignments ? 'bg-emerald-50/50 border-emerald-100' : 'bg-gray-50 border-gray-100'}`}>
                <div className="flex items-center gap-1.5 text-xs">
                  {has_assignments ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-gray-400" />}
                  <span className="font-semibold">Coverage Status</span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5 ml-5">
                  {has_assignments ? `${assigned_plans.length} plan(s) assigned: ${assigned_plans.map(ap => ap.plan?.plan_name).join(', ')}` : 'No plans assigned'}
                </p>
              </div>

              {/* Employment Classification */}
              <div className={`p-2.5 rounded-md border ${emp.is_full_time ? 'bg-indigo-50/50 border-indigo-100' : 'bg-sky-50/50 border-sky-100'}`}>
                <div className="flex items-center gap-1.5 text-xs">
                  <Briefcase className={`w-3.5 h-3.5 ${emp.is_full_time ? 'text-indigo-600' : 'text-sky-600'}`} />
                  <span className="font-semibold">Employment Classification</span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5 ml-5">
                  {emp.is_full_time ? 'Full-Time' : 'Part-Time'} — {emp.weekly_hours} hrs/wk ({emp.monthly_hours} hrs/mo)
                </p>
              </div>

            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
