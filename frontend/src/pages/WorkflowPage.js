import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Building2, Users, Calculator, ShieldCheck, FileBarChart, DollarSign,
  Award, CheckCircle2, XCircle, AlertTriangle, Clock, ArrowRight,
  PlayCircle, RotateCcw, ChevronDown, ChevronUp, GitBranch, FileText,
  Flag, Loader2, ArrowDown, Zap
} from 'lucide-react';

const STEP_META = {
  onboarding: { icon: Building2, color: 'blue', nav: null },
  employee_profiles: { icon: Users, color: 'indigo', nav: '/employees' },
  fte_calculation: { icon: Calculator, color: 'violet', nav: '/ale' },
  ale_status: { icon: Calculator, color: 'amber', nav: '/ale', decision: true },
  eligibility: { icon: Users, color: 'cyan', nav: '/employees' },
  mec_validation: { icon: ShieldCheck, color: 'emerald', nav: '/mec', decision: true },
  mv_calculation: { icon: FileBarChart, color: 'orange', nav: '/mv', decision: true },
  actuarial_certification: { icon: Award, color: 'purple', nav: '/marketplace', conditional: true },
  affordability: { icon: DollarSign, color: 'rose', nav: '/affordability', decision: true },
  subsidy_check: { icon: AlertTriangle, color: 'yellow', nav: null },
  plan_approval: { icon: CheckCircle2, color: 'emerald', nav: '/plans' },
  irs_reporting: { icon: FileText, color: 'slate', nav: '/irs-forms' },
  compliance_complete: { icon: Flag, color: 'emerald', nav: null },
};

function StepStatusIcon({ status }) {
  if (status === 'complete') return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
  if (status === 'incomplete') return <XCircle className="w-5 h-5 text-gray-300" />;
  if (status === 'in_progress') return <Clock className="w-5 h-5 text-amber-500" />;
  return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
}

function StepResultCard({ stepId, data }) {
  if (!data || Object.keys(data).length === 0) return null;

  const renderKV = (label, value, highlight) => (
    <div className="flex items-center justify-between py-1" key={label}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`text-xs font-semibold tabular-nums ${highlight || ''}`}>{value}</span>
    </div>
  );

  const entries = [];

  if (stepId === 'onboarding') {
    entries.push(renderKV('Company', data.employer_name || '-'));
    entries.push(renderKV('EIN', data.ein || '-'));
    entries.push(renderKV('Payroll', data.payroll_provider || 'Not connected'));
    entries.push(renderKV('Data Connected', data.data_connected ? 'Yes' : 'No', data.data_connected ? 'text-emerald-600' : 'text-amber-600'));
  } else if (stepId === 'employee_profiles') {
    entries.push(renderKV('Total Employees', data.total_employees));
    entries.push(renderKV('With Hours Data', data.with_hours));
    entries.push(renderKV('With Coverage', data.with_coverage));
  } else if (stepId === 'fte_calculation') {
    entries.push(renderKV('Full-Time', data.full_time_count));
    entries.push(renderKV('Part-Time', data.part_time_count));
    entries.push(renderKV('FTE Equivalent', data.fte_equivalent));
    entries.push(renderKV('Total FTE', data.total_fte, 'text-base'));
  } else if (stepId === 'ale_status') {
    entries.push(renderKV('Total FTE', data.total_fte));
    entries.push(renderKV('Threshold', data.threshold));
    entries.push(renderKV('ALE Status', data.is_ale ? 'YES - Applicable Large Employer' : 'NO - Not an ALE', data.is_ale ? 'text-amber-600' : 'text-emerald-600'));
    if (data.terminal) {
      entries.push(
        <div key="terminal" className="mt-2 p-2 rounded-md bg-blue-50 border border-blue-200">
          <p className="text-xs text-blue-800 font-medium">{data.terminal_message}</p>
        </div>
      );
    }
  } else if (stepId === 'eligibility') {
    entries.push(renderKV('Total Employees', data.total));
    entries.push(renderKV('Eligible', data.eligible, 'text-emerald-600'));
    entries.push(renderKV('Waiting Period', data.waiting_period, 'text-amber-600'));
    entries.push(renderKV('Not Eligible', data.not_eligible));
  } else if (stepId === 'mec_validation') {
    entries.push(renderKV('Full-Time Employees', data.full_time_count));
    entries.push(renderKV('Offered MEC', data.offered_mec));
    entries.push(renderKV('Coverage %', `${data.coverage_pct}%`, data.passed ? 'text-emerald-600' : 'text-rose-600'));
    entries.push(renderKV('Result', data.passed ? 'COMPLIANT' : 'NOT COMPLIANT', data.passed ? 'text-emerald-600' : 'text-rose-600'));
  } else if (stepId === 'mv_calculation') {
    entries.push(renderKV('Plan', data.plan_name || '-'));
    if (data.mv_percentage !== null && data.mv_percentage !== undefined) {
      entries.push(renderKV('MV Percentage', `${data.mv_percentage}%`, data.passed ? 'text-emerald-600' : 'text-rose-600'));
      entries.push(renderKV('Result', data.passed ? 'PASS (>= 60%)' : 'FAIL (< 60%)', data.passed ? 'text-emerald-600' : 'text-rose-600'));
    }
    if (data.needs_calculation) {
      entries.push(
        <div key="needs-calc" className="mt-2 p-2 rounded-md bg-amber-50 border border-amber-200">
          <p className="text-xs text-amber-800 font-medium">{data.message}</p>
        </div>
      );
    }
  } else if (stepId === 'actuarial_certification') {
    entries.push(renderKV('Total Requests', data.total_requests));
    entries.push(renderKV('Certified', data.certified, 'text-emerald-600'));
    entries.push(renderKV('Pending', data.pending, 'text-amber-600'));
    if (data.certification_result) entries.push(renderKV('Certified MV %', `${data.certification_result}%`));
  } else if (stepId === 'affordability') {
    entries.push(renderKV('Employees Tested', data.tested));
    entries.push(renderKV('Affordable', data.affordable, 'text-emerald-600'));
    entries.push(renderKV('Not Affordable', data.not_affordable, data.not_affordable > 0 ? 'text-rose-600' : ''));
    entries.push(renderKV('Result', data.passed ? 'PASS' : data.tested > 0 ? 'FAIL' : 'N/A', data.passed ? 'text-emerald-600' : data.tested > 0 ? 'text-rose-600' : ''));
  } else if (stepId === 'subsidy_check') {
    entries.push(renderKV('MEC Check', data.mec_pass ? 'Pass' : 'Fail', data.mec_pass ? 'text-emerald-600' : 'text-rose-600'));
    entries.push(renderKV('MV Check', data.mv_pass ? 'Pass' : 'Fail', data.mv_pass ? 'text-emerald-600' : 'text-rose-600'));
    entries.push(renderKV('Subsidy Risk', data.subsidy_eligible ? 'Employees may qualify' : 'No subsidy risk', data.subsidy_eligible ? 'text-amber-600' : 'text-emerald-600'));
  } else if (stepId === 'plan_approval') {
    entries.push(renderKV('Status', data.approved ? 'APPROVED' : 'Pending', data.approved ? 'text-emerald-600' : 'text-amber-600'));
  } else if (stepId === 'irs_reporting') {
    entries.push(renderKV('Form 1095-C Count', data.form_1095c_count));
    entries.push(renderKV('Form 1094-C', data.form_1094c ? 'Required' : '-'));
    entries.push(renderKV('Tax Year', data.tax_year));
  } else if (stepId === 'compliance_complete') {
    entries.push(
      <div key="complete" className="p-3 rounded-md bg-emerald-50 border border-emerald-200 text-center">
        <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-1" />
        <p className="text-sm font-semibold text-emerald-800">Full ACA Compliance Achieved</p>
        <p className="text-xs text-emerald-600 mt-1">{data.message}</p>
      </div>
    );
  } else {
    // Generic fallback
    if (data.message) entries.push(renderKV('Info', data.message));
  }

  return <div className="mt-2 divide-y divide-border/40">{entries}</div>;
}

export default function WorkflowPage() {
  const { selectedEmployer, token, API } = useAuth();
  const [workflow, setWorkflow] = useState(null);
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(null); // step_id being executed
  const [runningAll, setRunningAll] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});
  const navigate = useNavigate();
  const headers = { Authorization: `Bearer ${token}` };

  const fetchWorkflow = useCallback(async () => {
    if (!selectedEmployer) return;
    try {
      const res = await axios.get(`${API}/workflow/${selectedEmployer.id}`, { headers });
      setWorkflow(res.data);
      // Build ordered step list from WORKFLOW_STEPS definition
      const stepDefs = [
        { id: 'onboarding', name: 'Employer Onboarding', description: 'Register & connect to data sources' },
        { id: 'employee_profiles', name: 'Employee Profiles', description: 'Import and sync employee data' },
        { id: 'fte_calculation', name: 'FTE Calculation', description: 'Calculate full-time equivalents' },
        { id: 'ale_status', name: 'ALE Determination', description: 'Applicable Large Employer status', type: 'decision' },
        { id: 'eligibility', name: 'Eligibility Determination', description: 'Determine employee eligibility for coverage' },
        { id: 'mec_validation', name: 'MEC Validation', description: 'Validate Minimum Essential Coverage', type: 'decision' },
        { id: 'mv_calculation', name: 'Minimum Value Calculation', description: 'Run HHS MV Calculator', type: 'decision' },
        { id: 'actuarial_certification', name: 'Actuarial Certification', description: 'Request certification if needed', conditional: true },
        { id: 'affordability', name: 'Affordability Testing', description: 'Test safe harbor affordability methods', type: 'decision' },
        { id: 'subsidy_check', name: 'Subsidy Eligibility Check', description: 'Determine marketplace subsidy eligibility' },
        { id: 'plan_approval', name: 'Plan Approved', description: 'All compliance checks verified' },
        { id: 'irs_reporting', name: 'IRS Reporting', description: 'Generate 1095-C & 1094-C forms' },
        { id: 'compliance_complete', name: 'Compliance Complete', description: 'Full ACA compliance achieved' },
      ];
      const stepsData = res.data.steps || {};
      const merged = stepDefs.map(s => ({
        ...s,
        result: stepsData[s.id] || null,
        status: stepsData[s.id]?.status || 'pending',
      }));
      setSteps(merged);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedEmployer, API, token]);

  useEffect(() => { fetchWorkflow(); }, [fetchWorkflow]);

  const executeStep = async (stepId) => {
    setExecuting(stepId);
    try {
      const res = await axios.post(
        `${API}/workflow/${selectedEmployer.id}/execute/${stepId}`,
        {},
        { headers }
      );
      // Update steps in local state
      setSteps(prev => prev.map(s =>
        s.id === stepId ? { ...s, result: res.data, status: res.data.status } : s
      ));
      setExpandedSteps(prev => ({ ...prev, [stepId]: true }));
      toast.success(`${steps.find(s => s.id === stepId)?.name || stepId} completed`);
    } catch (err) {
      toast.error(`Failed to execute step: ${err.response?.data?.detail || err.message}`);
    } finally {
      setExecuting(null);
    }
  };

  const runAllSteps = async () => {
    setRunningAll(true);
    try {
      const res = await axios.post(
        `${API}/workflow/${selectedEmployer.id}/run-all`,
        {},
        { headers }
      );
      // Update all steps
      const stepsData = res.data.steps || {};
      setSteps(prev => prev.map(s => ({
        ...s,
        result: stepsData[s.id] || s.result,
        status: stepsData[s.id]?.status || s.status,
      })));
      // Expand all completed steps
      const expanded = {};
      Object.keys(stepsData).forEach(k => { expanded[k] = true; });
      setExpandedSteps(expanded);
      toast.success('Full compliance check completed');
    } catch (err) {
      toast.error(`Workflow error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setRunningAll(false);
    }
  };

  const resetWorkflow = async () => {
    try {
      // Re-fetch fresh workflow state
      await fetchWorkflow();
      setExpandedSteps({});
      toast.success('Workflow refreshed');
    } catch {
      toast.error('Failed to reset');
    }
  };

  const toggleExpand = (stepId) => {
    setExpandedSteps(prev => ({ ...prev, [stepId]: !prev[stepId] }));
  };

  // Calculate progress
  const completedCount = steps.filter(s => s.status === 'complete').length;
  const totalSteps = steps.length;
  const progressPct = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0;

  if (!selectedEmployer) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[80vh]" data-testid="workflow-no-employer">
        <Card className="max-w-md w-full border-0 shadow-sm">
          <CardContent className="p-6 text-center">
            <Building2 className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <h2 className="text-lg font-bold font-[Manrope] mb-2">No Organization Selected</h2>
            <p className="text-sm text-muted-foreground">Select or create an employer to start the compliance workflow</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto" data-testid="workflow-page">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Compliance Workflow</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Step-by-step ACA compliance for {selectedEmployer?.name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={resetWorkflow}
            data-testid="workflow-refresh-btn"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Refresh
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={runAllSteps}
            disabled={runningAll || !selectedEmployer}
            data-testid="workflow-run-all-btn"
          >
            {runningAll ? (
              <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Running...</>
            ) : (
              <><Zap className="w-3.5 h-3.5 mr-1.5" /> Run Full Check</>
            )}
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      <Card className="mb-6 border-0 shadow-sm overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-indigo-500 via-violet-500 to-purple-500" />
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Overall Progress</span>
            <span className="text-sm font-bold tabular-nums" data-testid="workflow-progress-text">{completedCount}/{totalSteps} steps</span>
          </div>
          <Progress value={progressPct} className="h-2" data-testid="workflow-progress-bar" />
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-emerald-500" /> Complete: {completedCount}</span>
              <span className="flex items-center gap-1"><Clock className="w-3 h-3 text-amber-500" /> In Progress: {steps.filter(s => s.status === 'in_progress').length}</span>
              <span className="flex items-center gap-1"><XCircle className="w-3 h-3 text-gray-300" /> Pending: {steps.filter(s => s.status === 'pending' || s.status === 'incomplete').length}</span>
            </div>
            <span className="text-xs font-semibold tabular-nums">{progressPct}%</span>
          </div>
        </CardContent>
      </Card>

      {/* Workflow Steps */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="relative" data-testid="workflow-steps-container">
          {/* Vertical line connector */}
          <div className="absolute left-[23px] top-6 bottom-6 w-0.5 bg-border/60" />

          <div className="space-y-1">
            {steps.map((step, idx) => {
              const meta = STEP_META[step.id] || { icon: CheckCircle2, color: 'gray' };
              const Icon = meta.icon;
              const isExpanded = expandedSteps[step.id];
              const isExecuting = executing === step.id;
              const hasResult = step.result && step.result.data && Object.keys(step.result.data).length > 0;
              const isDecision = step.type === 'decision';
              const isConditional = step.conditional;
              const isTerminal = step.result?.data?.terminal;
              const isLast = idx === steps.length - 1;

              return (
                <div key={step.id} className="relative" data-testid={`workflow-step-${step.id}`}>
                  <div
                    className={`ml-0 flex items-start gap-3 p-3 rounded-lg transition-all duration-200 ${
                      step.status === 'complete'
                        ? 'bg-emerald-50/40 border border-emerald-200/60'
                        : step.status === 'in_progress'
                        ? 'bg-amber-50/40 border border-amber-200/60'
                        : 'bg-white border border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {/* Step indicator */}
                    <div className="flex-shrink-0 relative z-10 mt-0.5">
                      <div className={`w-[46px] h-[46px] rounded-xl flex items-center justify-center ${
                        step.status === 'complete'
                          ? 'bg-emerald-100 text-emerald-600'
                          : step.status === 'in_progress'
                          ? 'bg-amber-100 text-amber-600'
                          : 'bg-gray-100 text-gray-400'
                      }`}>
                        {isExecuting ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <Icon className="w-5 h-5" />
                        )}
                      </div>
                      {isDecision && (
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-amber-400 flex items-center justify-center">
                          <GitBranch className="w-2.5 h-2.5 text-white" />
                        </div>
                      )}
                      {isConditional && (
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-purple-400 flex items-center justify-center">
                          <span className="text-[8px] font-bold text-white">?</span>
                        </div>
                      )}
                    </div>

                    {/* Step content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold">{step.name}</h3>
                          <Badge
                            variant="outline"
                            className={`text-[10px] h-5 ${
                              step.status === 'complete'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : step.status === 'in_progress'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : step.status === 'incomplete'
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : 'bg-gray-50 text-gray-500 border-gray-200'
                            }`}
                            data-testid={`step-status-${step.id}`}
                          >
                            {step.status === 'complete' ? 'Complete' : step.status === 'in_progress' ? 'In Progress' : step.status === 'incomplete' ? 'Needs Action' : 'Pending'}
                          </Badge>
                          {isDecision && (
                            <Badge variant="outline" className="text-[10px] h-5 bg-amber-50/50 text-amber-600 border-amber-200">
                              Decision
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {meta.nav && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-[10px] px-2 text-muted-foreground"
                              onClick={() => navigate(meta.nav)}
                              data-testid={`step-nav-${step.id}`}
                            >
                              Open Tool <ArrowRight className="w-3 h-3 ml-0.5" />
                            </Button>
                          )}
                          <Button
                            variant={step.status === 'complete' ? 'ghost' : 'default'}
                            size="sm"
                            className="h-7 text-xs px-3"
                            onClick={() => executeStep(step.id)}
                            disabled={isExecuting || runningAll}
                            data-testid={`step-execute-${step.id}`}
                          >
                            {isExecuting ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : step.status === 'complete' ? (
                              <><RotateCcw className="w-3 h-3 mr-1" /> Re-run</>
                            ) : (
                              <><PlayCircle className="w-3 h-3 mr-1" /> Run</>
                            )}
                          </Button>
                          {hasResult && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0"
                              onClick={() => toggleExpand(step.id)}
                              data-testid={`step-toggle-${step.id}`}
                            >
                              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            </Button>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>

                      {/* Expanded result data */}
                      {isExpanded && hasResult && (
                        <div className="mt-2 p-3 bg-white/80 rounded-md border border-border/40">
                          <StepResultCard stepId={step.id} data={step.result.data} />
                        </div>
                      )}

                      {/* Terminal message */}
                      {isTerminal && (
                        <div className="mt-2 p-2 rounded-md bg-blue-50 border border-blue-200">
                          <p className="text-xs text-blue-800 font-medium flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" /> {step.result.data.terminal_message}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Connector arrow between steps */}
                  {!isLast && (
                    <div className="flex justify-center py-0.5">
                      <ArrowDown className="w-3.5 h-3.5 text-border" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
