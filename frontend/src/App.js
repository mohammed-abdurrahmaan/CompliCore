import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ALECalculatorPage from "@/pages/ALECalculatorPage";
import MECTrackingPage from "@/pages/MECTrackingPage";
import MVCalculatorPage from "@/pages/MVCalculatorPage";
import CertificationPage from "@/pages/CertificationPage";
import EmployeesPage from "@/pages/EmployeesPage";
import EmployeeProfilePage from "@/pages/EmployeeProfilePage";
import AffordabilityPage from "@/pages/AffordabilityPage";
import ActuaryMarketplacePage from "@/pages/ActuaryMarketplacePage";
import WorkflowPage from "@/pages/WorkflowPage";
import IRSFormsPage from "@/pages/IRSFormsPage";
import PlanLibraryPage from "@/pages/PlanLibraryPage";
import EnrollmentReviewPage from "@/pages/EnrollmentReviewPage";
import EmployeePortalPage from "@/pages/EmployeePortalPage";
import CensusExportPage from "@/pages/CensusExportPage";
import DashboardLayout from "@/components/DashboardLayout";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (!user) return <Navigate to="/login" />;
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.role === 'employee' ? '/employee-portal' : '/'} /> : <LoginPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/:employeeId" element={<EmployeeProfilePage />} />
        <Route path="ale" element={<ALECalculatorPage />} />
        <Route path="mec" element={<MECTrackingPage />} />
        <Route path="mv" element={<MVCalculatorPage />} />
        <Route path="affordability" element={<AffordabilityPage />} />
        <Route path="certifications" element={<CertificationPage />} />
        <Route path="marketplace" element={<ActuaryMarketplacePage />} />
        <Route path="workflow" element={<WorkflowPage />} />
        <Route path="irs-forms" element={<IRSFormsPage />} />
        <Route path="plan-library" element={<PlanLibraryPage />} />
        <Route path="enrollment-review" element={<EnrollmentReviewPage />} />
        <Route path="employee-portal" element={<EmployeePortalPage />} />
        <Route path="census-export" element={<CensusExportPage />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
