import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const { login, register, registerEmployee } = useAuth();
  const [tab, setTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [regData, setRegData] = useState({ email: '', password: '', name: '', role: 'employer', company_name: '', employer_code: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(loginData.email, loginData.password);
      toast.success('Welcome back');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regData.name || !regData.email || !regData.password) {
      toast.error('Please fill all required fields');
      return;
    }
    if (regData.role === 'employee' && !regData.employer_code) {
      toast.error('Employer code is required for employee registration');
      return;
    }
    setLoading(true);
    try {
      if (regData.role === 'employee') {
        await registerEmployee(regData);
      } else {
        await register(regData);
      }
      toast.success('Account created');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: `radial-gradient(circle at 1px 1px, #4338CA 1px, transparent 0)`,
        backgroundSize: '28px 28px'
      }} />

      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2.5 mb-3">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center shadow-md">
              <ShieldCheck className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold tracking-tight font-[Manrope]">CompliCore</span>
          </div>
          <p className="text-sm text-muted-foreground">ACA Compliance Management</p>
        </div>

        <Card className="shadow-lg border-0">
          <Tabs value={tab} onValueChange={setTab}>
            <CardHeader className="pb-3">
              <TabsList className="grid grid-cols-2 w-full">
                <TabsTrigger value="login" data-testid="login-tab">Sign In</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
              </TabsList>
            </CardHeader>
            <CardContent>
              <TabsContent value="login" className="mt-0">
                <form onSubmit={handleLogin} className="space-y-3">
                  <div>
                    <Label className="text-xs font-medium">Email</Label>
                    <Input data-testid="login-email" type="email" placeholder="you@company.com" value={loginData.email} onChange={e => setLoginData(p => ({...p, email: e.target.value}))} className="h-9 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs font-medium">Password</Label>
                    <Input data-testid="login-password" type="password" placeholder="Enter password" value={loginData.password} onChange={e => setLoginData(p => ({...p, password: e.target.value}))} className="h-9 text-sm mt-1" />
                  </div>
                  <Button data-testid="login-submit" type="submit" className="w-full h-9 text-sm font-medium" disabled={loading}>
                    {loading ? 'Signing in...' : 'Sign In'} {!loading && <ArrowRight className="w-3.5 h-3.5 ml-1" />}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register" className="mt-0">
                <form onSubmit={handleRegister} className="space-y-3">
                  <div>
                    <Label className="text-xs font-medium">Full Name *</Label>
                    <Input data-testid="register-name" placeholder="John Smith" value={regData.name} onChange={e => setRegData(p => ({...p, name: e.target.value}))} className="h-9 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs font-medium">Email *</Label>
                    <Input data-testid="register-email" type="email" placeholder="you@company.com" value={regData.email} onChange={e => setRegData(p => ({...p, email: e.target.value}))} className="h-9 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs font-medium">Password *</Label>
                    <Input data-testid="register-password" type="password" placeholder="Min 6 characters" value={regData.password} onChange={e => setRegData(p => ({...p, password: e.target.value}))} className="h-9 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs font-medium">Role *</Label>
                    <Select value={regData.role} onValueChange={val => setRegData(p => ({...p, role: val}))}>
                      <SelectTrigger className="h-9 text-sm mt-1" data-testid="register-role">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent position="popper" sideOffset={4}>
                        <SelectItem value="employer" data-testid="role-employer">Employer / HR Admin</SelectItem>
                        <SelectItem value="employee" data-testid="role-employee">Employee</SelectItem>
                        <SelectItem value="actuary" data-testid="role-actuary">Actuary</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {regData.role === 'employee' && (
                    <div>
                      <Label className="text-xs font-medium">Employer Code *</Label>
                      <Input data-testid="register-employer-code" placeholder="e.g., ABC123" value={regData.employer_code} onChange={e => setRegData(p => ({...p, employer_code: e.target.value.toUpperCase()}))} className="h-9 text-sm mt-1 font-mono tracking-widest" maxLength={6} />
                      <p className="text-[10px] text-muted-foreground mt-1">Get this code from your HR department</p>
                    </div>
                  )}
                  {regData.role === 'employer' && (
                    <div>
                      <Label className="text-xs font-medium">Company Name</Label>
                      <Input data-testid="register-company" placeholder="Acme Corp" value={regData.company_name} onChange={e => setRegData(p => ({...p, company_name: e.target.value}))} className="h-9 text-sm mt-1" />
                    </div>
                  )}
                  <Button data-testid="register-submit" type="submit" className="w-full h-9 text-sm font-medium" disabled={loading}>
                    {loading ? 'Creating account...' : 'Create Account'} {!loading && <ArrowRight className="w-3.5 h-3.5 ml-1" />}
                  </Button>
                </form>
              </TabsContent>
            </CardContent>
          </Tabs>
        </Card>
      </div>
    </div>
  );
}
