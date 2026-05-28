import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import axios from 'axios';
import { Award, Clock, CheckCircle2, XCircle, Eye, MessageSquare, Plus, FileText } from 'lucide-react';

const STATUS_CONFIG = {
  pending: { label: 'Pending', className: 'bg-amber-50 text-amber-700 border-transparent' },
  in_review: { label: 'In Review', className: 'bg-blue-50 text-blue-700 border-transparent' },
  certified: { label: 'Certified', className: 'bg-emerald-50 text-emerald-700 border-transparent' },
  rejected: { label: 'Rejected', className: 'bg-rose-50 text-rose-700 border-transparent' }
};

export default function CertificationPage() {
  const { user, selectedEmployer, token, API } = useAuth();
  const [certifications, setCertifications] = useState([]);
  const [plans, setPlans] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showReview, setShowReview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [createData, setCreateData] = useState({ plan_id: '', reason: '', notes: '' });
  const [reviewData, setReviewData] = useState({ status: '', actuary_notes: '', certification_result: '' });
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadCertifications();
    if (selectedEmployer && user?.role === 'employer') {
      loadPlans();
    }
  }, [selectedEmployer, user]);

  const loadCertifications = async () => {
    try {
      const res = await axios.get(`${API}/certifications`, { headers });
      setCertifications(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadPlans = async () => {
    try {
      const res = await axios.get(`${API}/plans/${selectedEmployer.id}`, { headers });
      setPlans(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreate = async () => {
    if (!createData.plan_id || !createData.reason) {
      toast.error('Please select a plan and provide a reason');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/certifications`, {
        employer_id: selectedEmployer.id,
        plan_id: createData.plan_id,
        reason: createData.reason,
        notes: createData.notes
      }, { headers });
      toast.success('Certification request submitted');
      setShowCreate(false);
      setCreateData({ plan_id: '', reason: '', notes: '' });
      loadCertifications();
    } catch (err) {
      toast.error('Failed to create certification request');
    }
    setLoading(false);
  };

  const handleReview = async (certId) => {
    if (!reviewData.status) {
      toast.error('Please select a status');
      return;
    }
    setLoading(true);
    try {
      await axios.put(`${API}/certifications/${certId}`, {
        status: reviewData.status,
        actuary_notes: reviewData.actuary_notes,
        certification_result: reviewData.certification_result ? parseFloat(reviewData.certification_result) : null
      }, { headers });
      toast.success('Certification updated');
      setShowReview(null);
      setReviewData({ status: '', actuary_notes: '', certification_result: '' });
      loadCertifications();
    } catch (err) {
      toast.error('Failed to update certification');
    }
    setLoading(false);
  };

  const openReview = (cert) => {
    setShowReview(cert);
    setReviewData({
      status: cert.status === 'pending' ? 'in_review' : cert.status,
      actuary_notes: cert.actuary_notes || '',
      certification_result: cert.certification_result?.toString() || ''
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="certification-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-[Manrope]">Actuarial Certifications</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {user?.role === 'employer' 
              ? 'Request and track actuarial certifications for plan MV determination' 
              : 'Review and certify plan minimum value assessments'}
          </p>
        </div>
        {user?.role === 'employer' && selectedEmployer && (
          <Dialog open={showCreate} onOpenChange={setShowCreate}>
            <DialogTrigger asChild>
              <Button className="h-9 text-sm" data-testid="new-cert-btn">
                <Plus className="w-3.5 h-3.5 mr-1.5" /> New Request
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Request Actuarial Certification</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs">Plan *</Label>
                  <Select value={createData.plan_id} onValueChange={val => setCreateData(p => ({...p, plan_id: val}))}>
                    <SelectTrigger className="h-9 text-sm mt-1" data-testid="cert-plan-select">
                      <SelectValue placeholder="Select plan" />
                    </SelectTrigger>
                    <SelectContent>
                      {plans.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.plan_name} ({p.plan_type})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Reason for Certification *</Label>
                  <Select value={createData.reason} onValueChange={val => setCreateData(p => ({...p, reason: val}))}>
                    <SelectTrigger className="h-9 text-sm mt-1" data-testid="cert-reason-select">
                      <SelectValue placeholder="Select reason" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="HHS calculation failed">HHS Calculator Failed</SelectItem>
                      <SelectItem value="Non-standard plan design">Non-Standard Plan Design</SelectItem>
                      <SelectItem value="Complex cost-sharing structure">Complex Cost-Sharing</SelectItem>
                      <SelectItem value="Wellness program adjustment">Wellness Program Adjustment</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Additional Notes</Label>
                  <Textarea
                    data-testid="cert-notes"
                    className="text-sm mt-1"
                    rows={3}
                    placeholder="Describe any special plan features or circumstances..."
                    value={createData.notes}
                    onChange={e => setCreateData(p => ({...p, notes: e.target.value}))}
                  />
                </div>
                <Button onClick={handleCreate} disabled={loading} className="w-full h-9 text-sm" data-testid="submit-cert-btn">
                  {loading ? 'Submitting...' : 'Submit Request'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Certifications List */}
      <Card className="border-0 shadow-sm overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-purple-400 to-violet-400" />
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-bold">
            {user?.role === 'actuary' ? 'All Certification Requests' : 'Your Certification Requests'}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {certifications.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Plan</th>
                  <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Reason</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-center px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">MV Result</th>
                  {user?.role === 'actuary' && (
                    <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Requested By</th>
                  )}
                  <th className="text-left px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Date</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody>
                {certifications.map((cert, idx) => {
                  const config = STATUS_CONFIG[cert.status] || STATUS_CONFIG.pending;
                  return (
                    <tr key={cert.id} className={`border-b border-slate-100 hover:bg-indigo-50/40 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                      <td className="px-4 py-2 font-semibold text-slate-800">{cert.plan_name}</td>
                      <td className="px-4 py-2 text-slate-500 text-xs">{cert.reason}</td>
                      <td className="px-4 py-2 text-center">
                        <Badge className={`${config.className} text-xs`}>{config.label}</Badge>
                      </td>
                      <td className="px-4 py-2 text-center tabular-nums font-semibold">
                        {cert.certification_result ? `${cert.certification_result}%` : '-'}
                      </td>
                      {user?.role === 'actuary' && (
                        <td className="px-4 py-2 text-muted-foreground text-xs">{cert.requested_by_name}</td>
                      )}
                      <td className="px-4 py-2 text-muted-foreground text-xs">{new Date(cert.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-2 text-right">
                        {user?.role === 'actuary' && (cert.status === 'pending' || cert.status === 'in_review') ? (
                          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => openReview(cert)} data-testid={`review-${cert.id}`}>
                            <Eye className="w-3 h-3 mr-1" /> Review
                          </Button>
                        ) : (
                          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => openReview(cert)} data-testid={`view-${cert.id}`}>
                            <FileText className="w-3 h-3 mr-1" /> Details
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="px-4 py-12 text-center">
              <div className="w-14 h-14 rounded-2xl bg-purple-100 flex items-center justify-center mx-auto mb-4"><Award className="w-7 h-7 text-purple-500" /></div>
              <p className="text-sm text-muted-foreground">
                {user?.role === 'employer' ? 'No certification requests yet' : 'No certifications to review'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Review Dialog */}
      <Dialog open={!!showReview} onOpenChange={(open) => { if (!open) setShowReview(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {user?.role === 'actuary' ? 'Review Certification' : 'Certification Details'}
            </DialogTitle>
          </DialogHeader>
          {showReview && (
            <div className="space-y-4">
              {/* Cert details */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Plan</p>
                  <p className="font-medium">{showReview.plan_name}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Status</p>
                  <Badge className={`${STATUS_CONFIG[showReview.status]?.className} text-xs mt-0.5`}>
                    {STATUS_CONFIG[showReview.status]?.label}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Reason</p>
                  <p className="font-medium">{showReview.reason}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Requested</p>
                  <p className="font-medium">{new Date(showReview.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {showReview.notes && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Employer Notes</p>
                  <div className="p-2 bg-muted/30 rounded text-sm">{showReview.notes}</div>
                </div>
              )}

              {showReview.actuary_notes && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Actuary Notes</p>
                  <div className="p-2 bg-muted/30 rounded text-sm">{showReview.actuary_notes}</div>
                </div>
              )}

              {/* Actuary actions */}
              {user?.role === 'actuary' && (showReview.status === 'pending' || showReview.status === 'in_review') && (
                <div className="border-t pt-4 space-y-3">
                  <div>
                    <Label className="text-xs">Update Status *</Label>
                    <Select value={reviewData.status} onValueChange={val => setReviewData(p => ({...p, status: val}))}>
                      <SelectTrigger className="h-9 text-sm mt-1" data-testid="review-status-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="in_review">In Review</SelectItem>
                        <SelectItem value="certified">Certified</SelectItem>
                        <SelectItem value="rejected">Rejected</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">MV Percentage (if certifying)</Label>
                    <Input
                      data-testid="review-mv-result"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      className="h-9 text-sm mt-1 tabular-nums"
                      placeholder="e.g., 65.50"
                      value={reviewData.certification_result}
                      onChange={e => setReviewData(p => ({...p, certification_result: e.target.value}))}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Actuary Notes</Label>
                    <Textarea
                      data-testid="review-notes"
                      className="text-sm mt-1"
                      rows={3}
                      placeholder="Add your review notes..."
                      value={reviewData.actuary_notes}
                      onChange={e => setReviewData(p => ({...p, actuary_notes: e.target.value}))}
                    />
                  </div>
                  <Button onClick={() => handleReview(showReview.id)} disabled={loading} className="w-full h-9 text-sm" data-testid="submit-review-btn">
                    {loading ? 'Updating...' : 'Submit Review'}
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
