import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Users, Plus, Search, Zap, ChevronRight, RefreshCw,
  ShieldCheck, AlertTriangle, Building2, CalendarDays,
  Briefcase, DollarSign, Clock, UserCheck
} from 'lucide-react';

const DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations', 'Support', 'Executive'];

const MEASUREMENT_PERIODS = [
  { value: 'current_year', label: 'Current Year' },
  { value: '2025', label: '2025' },
  { value: '2024', label: '2024' },
  { value: 'last_3_months', label: 'Last 3 Months' },
  { value: 'last_6_months', label: 'Last 6 Months' },
  { value: 'last_9_months', label: 'Last 9 Months' },
  { value: 'last_12_months', label: 'Last 12 Months' },
];

const fmtDate = (d) => {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return d; }
};

const fmtSalary = (s) => {
  if (!s) return '-';
  return `$${Number(s).toLocaleString()}`;
};

export default function EmployeesPage() {
  const { selectedEmployer, token, API } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState('');
  const [filterDept, setFilterDept] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [measurementPeriod, setMeasurementPeriod] = useState('current_year');
  const [aleStatus, setAleStatus] = useState(null);
  const [aleLoading, setAleLoading] = useState(false);
  const navigate = useNavigate();
  const headers = { Authorization: `Bearer ${token}` };

  const [form, setForm] = useState({
    name: '', email: '', phone: '', ssn_last4: '', address: '',
    hire_date: '', job_title: '', department: 'Engineering',
    weekly_hours: '40', annual_salary: '50000', hourly_rate: '24',
    w2_wages: '50000', employee_monthly_premium: '125',
  });

  useEffect(() => {
    if (selectedEmployer) loadEmployees();
  }, [selectedEmployer]);

  useEffect(() => {
    if (selectedEmployer) loadAleStatus();
  }, [selectedEmployer, measurementPeriod]);

  const loadAleStatus = async () => {
    setAleLoading(true);
    try {
      const res = await axios.get(`${API}/employee-profiles/${selectedEmployer.id}/ale-status?period=${measurementPeriod}`, { headers });
      setAleStatus(res.data);
    } catch (err) { console.error(err); }
    setAleLoading(false);
  };

  const loadEmployees = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/employee-profiles/${selectedEmployer.id}`, { headers });
      setEmployees(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const generateProfiles = async () => {
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/employee-profiles/generate/${selectedEmployer.id}`, {}, { headers });
      setEmployees(res.data.employees || []);
      toast.success(`${res.data.count} employee profiles generated`);
    } catch (err) { toast.error('Failed to generate'); }
    setGenerating(false);
  };

  const handleAdd = async () => {
    if (!form.name) { toast.error('Name is required'); return; }
    try {
      await axios.post(`${API}/employee-profiles`, {
        employer_id: selectedEmployer.id,
        ...form,
        weekly_hours: parseFloat(form.weekly_hours) || 0,
        annual_salary: parseFloat(form.annual_salary) || 0,
        hourly_rate: parseFloat(form.hourly_rate) || 0,
        w2_wages: parseFloat(form.w2_wages) || 0,
        employee_monthly_premium: parseFloat(form.employee_monthly_premium) || 0,
      }, { headers });
      toast.success('Employee added');
      setShowAdd(false);
      loadEmployees();
    } catch (err) { toast.error('Failed to add employee'); }
  };

  const filtered = employees.filter(e => {
    if (search && !e.name.toLowerCase().includes(search.toLowerCase()) && !e.employee_id?.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterDept !== 'all' && e.department !== filterDept) return false;
    if (filterType !== 'all' && e.employment_type !== filterType) return false;
    return true;
  });

  const stats = {
    total: employees.length,
    fullTime: employees.filter(e => e.is_full_time).length,
    partTime: employees.filter(e => !e.is_full_time).length,
    eligible: employees.filter(e => e.eligibility_status === 'eligible').length,
  };

  if (!selectedEmployer) return <div className="p-6 text-center text-muted-foreground">Please select an employer first</div>;

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="employees-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Employee Profiles</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage workforce data and ACA eligibility</p>
        </div>
        <div className="flex gap-2">
          {employees.length === 0 && (
            <Button variant="outline" onClick={generateProfiles} disabled={generating} className="h-9 text-sm" data-testid="generate-employees-btn">
              <Zap className="w-3.5 h-3.5 mr-1.5" /> {generating ? 'Generating...' : 'Generate Sample Data'}
            </Button>
          )}
          <Dialog open={showAdd} onOpenChange={setShowAdd}>
            <DialogTrigger asChild>
              <Button className="h-9 text-sm" data-testid="add-employee-btn">
                <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Employee
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
              <DialogHeader><DialogTitle>Add Employee</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="text-xs">Full Name *</Label><Input data-testid="emp-name" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} className="h-8 text-sm mt-1" /></div>
                  <div><Label className="text-xs">Email</Label><Input data-testid="emp-email" value={form.email} onChange={e => setForm(p => ({...p, email: e.target.value}))} className="h-8 text-sm mt-1" /></div>
                  <div><Label className="text-xs">Hire Date</Label><Input data-testid="emp-hire" type="date" value={form.hire_date} onChange={e => setForm(p => ({...p, hire_date: e.target.value}))} className="h-8 text-sm mt-1" /></div>
                  <div>
                    <Label className="text-xs">Department</Label>
                    <Select value={form.department} onValueChange={v => setForm(p => ({...p, department: v}))}>
                      <SelectTrigger className="h-8 text-sm mt-1"><SelectValue /></SelectTrigger>
                      <SelectContent>{DEPARTMENTS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div><Label className="text-xs">Weekly Hours *</Label><Input data-testid="emp-hours" type="number" value={form.weekly_hours} onChange={e => setForm(p => ({...p, weekly_hours: e.target.value}))} className="h-8 text-sm mt-1 tabular-nums" /></div>
                  <div><Label className="text-xs">Annual Salary</Label><Input data-testid="emp-salary" type="number" value={form.annual_salary} onChange={e => setForm(p => ({...p, annual_salary: e.target.value}))} className="h-8 text-sm mt-1 tabular-nums" /></div>
                </div>
                <Button onClick={handleAdd} className="w-full h-8 text-sm" data-testid="submit-employee">Add Employee</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stat Cards - Colorful */}
      <div className="grid grid-cols-4 gap-4 mb-5">
        <Card className="border-0 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Total</p>
                <p className="text-3xl font-bold tabular-nums text-slate-900 mt-1">{stats.total}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-slate-200/70 flex items-center justify-center">
                <Users className="w-5 h-5 text-slate-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 bg-gradient-to-br from-indigo-50 to-indigo-100/80 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-indigo-500 uppercase tracking-wider font-semibold">Full-Time</p>
                <p className="text-3xl font-bold tabular-nums text-indigo-900 mt-1">{stats.fullTime}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-200/70 flex items-center justify-center">
                <Briefcase className="w-5 h-5 text-indigo-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 bg-gradient-to-br from-sky-50 to-sky-100/80 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-sky-500 uppercase tracking-wider font-semibold">Part-Time</p>
                <p className="text-3xl font-bold tabular-nums text-sky-900 mt-1">{stats.partTime}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-sky-200/70 flex items-center justify-center">
                <Clock className="w-5 h-5 text-sky-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 bg-gradient-to-br from-emerald-50 to-emerald-100/80 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-emerald-500 uppercase tracking-wider font-semibold">Eligible</p>
                <p className="text-3xl font-bold tabular-nums text-emerald-900 mt-1">{stats.eligible}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-200/70 flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ALE Measurement Period */}
      <Card className="border-0 shadow-sm mb-5 overflow-hidden" data-testid="ale-measurement-section">
        <div className="h-1 bg-gradient-to-r from-indigo-500 via-violet-500 to-purple-500" />
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Building2 className="w-4 h-4 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-foreground">ALE Status Determination</h2>
                <p className="text-[10px] text-muted-foreground">Applicable Large Employer threshold analysis</p>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-muted/40 rounded-lg px-2 py-1">
              <CalendarDays className="w-3.5 h-3.5 text-muted-foreground" />
              <Select value={measurementPeriod} onValueChange={setMeasurementPeriod}>
                <SelectTrigger className="h-7 text-xs w-40 border-0 bg-transparent shadow-none focus:ring-0" data-testid="measurement-period-select">
                  <SelectValue placeholder="Select Period" />
                </SelectTrigger>
                <SelectContent>
                  {MEASUREMENT_PERIODS.map(p => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {aleLoading ? (
            <div className="flex items-center justify-center py-6"><RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" /></div>
          ) : aleStatus ? (
            <div className="space-y-4">
              <div className="grid grid-cols-5 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Active Employees</p>
                  <p className="text-2xl font-bold tabular-nums text-slate-800 mt-1" data-testid="ale-total-employees">{aleStatus.total_employees}</p>
                </div>
                <div className="p-3 rounded-xl bg-indigo-50/80 border border-indigo-200/60">
                  <p className="text-[10px] text-indigo-500 uppercase tracking-wider font-semibold">Full-Time</p>
                  <p className="text-2xl font-bold tabular-nums text-indigo-800 mt-1" data-testid="ale-ft-count">{aleStatus.full_time_count}</p>
                </div>
                <div className="p-3 rounded-xl bg-violet-50/80 border border-violet-200/60">
                  <p className="text-[10px] text-violet-500 uppercase tracking-wider font-semibold">Part-Time FTE</p>
                  <p className="text-2xl font-bold tabular-nums text-violet-800 mt-1" data-testid="ale-fte">{aleStatus.fte_from_part_time}</p>
                </div>
                <div className="p-3 rounded-xl bg-purple-50/80 border border-purple-200/60">
                  <p className="text-[10px] text-purple-500 uppercase tracking-wider font-semibold">Total FTE</p>
                  <p className="text-2xl font-bold tabular-nums text-purple-800 mt-1" data-testid="ale-total-fte">{aleStatus.total_fte}</p>
                </div>
                <div className={`p-3 rounded-xl border-2 ${aleStatus.is_ale ? 'bg-rose-50 border-rose-300' : 'bg-emerald-50 border-emerald-300'}`}>
                  <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: aleStatus.is_ale ? '#9f1239' : '#065f46' }}>ALE Status</p>
                  <div className="flex items-center gap-1.5 mt-1">
                    {aleStatus.is_ale
                      ? <><AlertTriangle className="w-5 h-5 text-rose-600" /><span className="text-lg font-black text-rose-700" data-testid="ale-status-badge">ALE</span></>
                      : <><ShieldCheck className="w-5 h-5 text-emerald-600" /><span className="text-lg font-black text-emerald-700" data-testid="ale-status-badge">Not ALE</span></>
                    }
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between px-1">
                <p className="text-[11px] text-muted-foreground">
                  <span className="font-semibold text-foreground">{aleStatus.period_label}</span> — {aleStatus.full_time_count} FT + {aleStatus.fte_from_part_time} FTE = <span className="font-bold text-foreground">{aleStatus.total_fte}</span> total (threshold: 50)
                </p>
                {aleStatus.is_ale && aleStatus.potential_penalty > 0 && (
                  <Badge className="bg-rose-100 text-rose-800 border-rose-300 text-[11px] font-bold px-3 py-1" data-testid="ale-penalty-badge">
                    Potential Penalty: ${aleStatus.potential_penalty?.toLocaleString()}
                  </Badge>
                )}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Filters */}
      <Card className="border-0 shadow-sm mb-4">
        <CardContent className="p-3 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input data-testid="employee-search" placeholder="Search by name or ID..." value={search} onChange={e => setSearch(e.target.value)} className="h-8 text-sm pl-9 border-slate-200" />
          </div>
          <Select value={filterDept} onValueChange={setFilterDept}>
            <SelectTrigger className="h-8 text-sm w-40 border-slate-200" data-testid="filter-dept"><SelectValue placeholder="Department" /></SelectTrigger>
            <SelectContent><SelectItem value="all">All Departments</SelectItem>{DEPARTMENTS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="h-8 text-sm w-36 border-slate-200" data-testid="filter-type"><SelectValue placeholder="Type" /></SelectTrigger>
            <SelectContent><SelectItem value="all">All Types</SelectItem><SelectItem value="full_time">Full-Time</SelectItem><SelectItem value="part_time">Part-Time</SelectItem></SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="border-0 shadow-sm overflow-hidden">
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10">
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Employee</th>
                  <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Department</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Type</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Hrs/Wk</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Hire Date</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Salary</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Eligibility</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((emp, idx) => (
                  <tr key={emp.id} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors cursor-pointer ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`} onClick={() => navigate(`/employees/${emp.id}`)} data-testid={`employee-row-${emp.id}`}>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${emp.is_full_time ? 'bg-indigo-500' : 'bg-sky-500'}`}>
                          {emp.name?.charAt(0)?.toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-800">{emp.name}</p>
                          <p className="text-[10px] text-slate-400">{emp.job_title || emp.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">{emp.department}</span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <Badge variant="outline" className={`text-[10px] font-semibold ${emp.is_full_time ? 'border-indigo-200 text-indigo-700 bg-indigo-50' : 'border-sky-200 text-sky-700 bg-sky-50'}`}>
                        {emp.is_full_time ? 'Full-Time' : 'Part-Time'}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="tabular-nums text-xs font-semibold text-slate-700">{emp.weekly_hours}<span className="text-slate-400 font-normal ml-0.5">h</span></span>
                    </td>
                    <td className="px-4 py-2.5 text-center text-xs text-slate-500 tabular-nums">{fmtDate(emp.hire_date)}</td>
                    <td className="px-4 py-2.5 text-right text-xs tabular-nums font-semibold text-slate-700">{fmtSalary(emp.annual_salary)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <Badge className={`text-[10px] font-semibold border-0 ${
                        emp.eligibility_status === 'eligible' ? 'bg-emerald-100 text-emerald-800' :
                        emp.eligibility_status === 'waiting_period' ? 'bg-amber-100 text-amber-800' :
                        'bg-slate-100 text-slate-500'}`}>
                        {emp.eligibility_status === 'eligible' ? 'Eligible' : emp.eligibility_status === 'waiting_period' ? 'Waiting' : 'Not Eligible'}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-right"><ChevronRight className="w-3.5 h-3.5 text-slate-300" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && !loading && (
            <div className="py-12 text-center">
              <Users className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No employees found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
