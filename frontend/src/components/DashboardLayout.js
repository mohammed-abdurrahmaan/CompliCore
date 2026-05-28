import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import {
  LayoutDashboard, Calculator, ShieldCheck, FileBarChart, Award, ClipboardList,
  LogOut, ChevronLeft, ChevronRight, Plus, Building2, Users, DollarSign, Store, Workflow, FileText,
  Library, UserCheck, FileSpreadsheet, Contact
} from 'lucide-react';
import NotificationBell from '@/components/NotificationBell';

const employerNavItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/workflow', icon: Workflow, label: 'Compliance Workflow' },
  { to: '/employees', icon: Users, label: 'Employees' },
  { to: '/plan-library', icon: Library, label: 'Plan Library', group: 'enrollment' },
  { to: '/enrollment-review', icon: UserCheck, label: 'Enrollment Review', group: 'enrollment' },
  { to: '/census-export', icon: FileSpreadsheet, label: 'Census Export', group: 'enrollment' },
  { to: '/ale', icon: Calculator, label: 'ALE Calculator', group: 'tools' },
  { to: '/mec', icon: ShieldCheck, label: 'MEC Checker', group: 'tools' },
  { to: '/mv', icon: FileBarChart, label: 'MV Calculator', group: 'tools' },
  { to: '/affordability', icon: DollarSign, label: 'Affordability', group: 'tools' },
  { to: '/irs-forms', icon: FileText, label: 'IRS Forms' },
  { to: '/marketplace', icon: Store, label: 'Actuary Market' },
];

const actuaryNavItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/marketplace', icon: Store, label: 'Marketplace' },
];

const employeeNavItems = [
  { to: '/employee-portal', icon: Contact, label: 'My Benefits' },
];

export default function DashboardLayout() {
  const { user, logout, employers, selectedEmployer, setSelectedEmployer, createEmployer } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [showNewEmployer, setShowNewEmployer] = useState(false);
  const [newEmployer, setNewEmployer] = useState({ name: '', ein: '', address: '', contact_email: '' });
  const navigate = useNavigate();

  const navItems = user?.role === 'actuary' ? actuaryNavItems : user?.role === 'employee' ? employeeNavItems : employerNavItems;

  const handleCreateEmployer = async () => {
    if (!newEmployer.name) { toast.error('Company name is required'); return; }
    try {
      await createEmployer(newEmployer);
      toast.success('Employer created');
      setShowNewEmployer(false);
      setNewEmployer({ name: '', ein: '', address: '', contact_email: '' });
    } catch (err) {
      toast.error('Failed to create employer');
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className={`${collapsed ? 'w-16' : 'w-60'} flex-shrink-0 border-r border-slate-200/80 bg-white flex flex-col transition-all duration-200`}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-slate-200/80">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-bold text-lg tracking-tight font-[Manrope]">CompliCore</span>
            </div>
          )}
          {collapsed && (
            <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center mx-auto">
              <ShieldCheck className="w-4 h-4 text-primary-foreground" />
            </div>
          )}
        </div>

        {/* Employer Selector (employer role only) */}
        {user?.role === 'employer' && !collapsed && (
          <div className="px-3 py-3 border-b border-slate-200/80">
            <div className="flex items-center gap-1 mb-1.5">
              <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Organization</span>
            </div>
            {employers.length > 0 ? (
              <Select value={selectedEmployer?.id || ''} onValueChange={(val) => {
                const emp = employers.find(e => e.id === val);
                setSelectedEmployer(emp);
              }}>
                <SelectTrigger className="h-8 text-sm" data-testid="employer-selector">
                  <SelectValue placeholder="Select employer" />
                </SelectTrigger>
                <SelectContent>
                  {employers.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>{emp.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Dialog open={showNewEmployer} onOpenChange={setShowNewEmployer}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="w-full h-8 text-xs" data-testid="add-employer-btn">
                    <Plus className="w-3 h-3 mr-1" /> Add Employer
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Employer</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs">Company Name *</Label>
                      <Input data-testid="employer-name-input" value={newEmployer.name} onChange={e => setNewEmployer(p => ({...p, name: e.target.value}))} placeholder="Company name" className="h-8 text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs">EIN</Label>
                      <Input data-testid="employer-ein-input" value={newEmployer.ein} onChange={e => setNewEmployer(p => ({...p, ein: e.target.value}))} placeholder="XX-XXXXXXX" className="h-8 text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs">Address</Label>
                      <Input value={newEmployer.address} onChange={e => setNewEmployer(p => ({...p, address: e.target.value}))} placeholder="Address" className="h-8 text-sm" />
                    </div>
                    <Button data-testid="create-employer-submit" onClick={handleCreateEmployer} className="w-full h-8 text-sm">Create Employer</Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
            {employers.length > 0 && (
              <Dialog open={showNewEmployer} onOpenChange={setShowNewEmployer}>
                <DialogTrigger asChild>
                  <button className="text-xs text-muted-foreground hover:text-foreground mt-1.5 flex items-center gap-1 transition-colors" data-testid="add-another-employer-btn">
                    <Plus className="w-3 h-3" /> Add another
                  </button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Employer</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs">Company Name *</Label>
                      <Input data-testid="employer-name-input-2" value={newEmployer.name} onChange={e => setNewEmployer(p => ({...p, name: e.target.value}))} placeholder="Company name" className="h-8 text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs">EIN</Label>
                      <Input value={newEmployer.ein} onChange={e => setNewEmployer(p => ({...p, ein: e.target.value}))} placeholder="XX-XXXXXXX" className="h-8 text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs">Address</Label>
                      <Input value={newEmployer.address} onChange={e => setNewEmployer(p => ({...p, address: e.target.value}))} placeholder="Address" className="h-8 text-sm" />
                    </div>
                    <Button data-testid="create-employer-submit-2" onClick={handleCreateEmployer} className="w-full h-8 text-sm">Create Employer</Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 py-2 px-2 space-y-0.5 overflow-y-auto">
          {navItems.map((item, idx) => {
            const prevItem = navItems[idx - 1];
            const showEnrollLabel = !collapsed && item.group === 'enrollment' && prevItem?.group !== 'enrollment';
            const showToolsLabel = !collapsed && item.group === 'tools' && prevItem?.group !== 'tools';
            return (
              <div key={item.to}>
                {showEnrollLabel && <p className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider px-2.5 pt-3 pb-1">Enrollment</p>}
                {showToolsLabel && <p className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider px-2.5 pt-3 pb-1">Tools</p>}
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-all duration-150 ${
                      isActive
                        ? 'bg-primary text-primary-foreground font-medium shadow-sm'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }`
                  }
                  data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-slate-200/80 p-2">
          <button onClick={() => setCollapsed(!collapsed)} className="w-full flex items-center justify-center py-1.5 text-muted-foreground hover:text-foreground transition-colors" data-testid="toggle-sidebar">
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
          {!collapsed && (
            <div className="flex items-center gap-2 px-2 py-1.5 mt-1">
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                {user?.name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{user?.name}</p>
                <p className="text-[10px] text-muted-foreground capitalize">{user?.role}</p>
              </div>
              <NotificationBell />
              <button onClick={() => { logout(); navigate('/login'); }} className="text-muted-foreground hover:text-destructive transition-colors" data-testid="logout-btn">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          {collapsed && (
            <div className="flex flex-col items-center gap-2 mt-1">
              <NotificationBell />
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
