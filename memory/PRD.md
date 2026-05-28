# CompliCore — ACA Compliance Management Platform
## Product Requirements Document (PRD)

---

## 1. Executive Summary

**CompliCore** is a full-stack web application that automates Affordable Care Act (ACA) compliance for employers, employees, and actuaries. It replaces manual spreadsheets and fragmented tools with a unified platform covering the entire ACA compliance lifecycle — from workforce classification and plan setup, through enrollment and IRS reporting, to penalty risk analysis.

**Target Users:**
- **Employers / HR Admins** — Manage employees, configure health plans, ensure ACA compliance, generate IRS forms
- **Employees** — Self-register, view eligible plans, enroll/decline coverage, download 1095-C forms
- **Actuaries** — Provide Minimum Value (MV) certification via a marketplace with quoting, chat, and payment workflows

**Tech Stack:**
- Frontend: React 19 + Tailwind CSS + Radix UI + Recharts
- Backend: FastAPI (Python) + Motor (async MongoDB driver)
- Database: MongoDB
- Auth: JWT with bcrypt password hashing
- PDF Generation: ReportLab (IRS forms)

---

## 2. User Roles & Authentication

### 2.1 Role-Based Access Control
| Role | Access Level | Key Actions |
|------|-------------|-------------|
| **Employer** | Full employer dashboard | Manage employees, plans, compliance, IRS forms, enrollment |
| **Employee** | Self-service portal only | View plans, enroll/decline, download 1095-C |
| **Actuary** | Marketplace + certifications | Accept quotes, deliver MV certifications, chat with employers |

### 2.2 Auth Flows
- **Registration**: Employer/Actuary self-register; Employees register with employer access code
- **Login**: Email + password → JWT token (7-day expiry)
- **Session**: Token stored in localStorage, validated via `/api/auth/me`
- **Multi-employer**: Employer users can manage multiple companies

### 2.3 Backlog
- Forgot password flow
- Password strength enforcement
- Email verification
- OAuth/SSO integration

---

## 3. Core Modules

### 3.1 Employer Management
**Collections:** `employers`

| Feature | Description | Status |
|---------|-------------|--------|
| Create employer | Name, EIN, address, contact email, employee count | ✅ Implemented |
| Employer selector | Dropdown to switch between employers | ✅ Implemented |
| Employer access code | Auto-generated 6-char code for employee self-registration | ✅ Implemented |
| Multi-employer support | One user account manages multiple companies | ✅ Implemented |

---

### 3.2 Employee Management
**Collections:** `employee_profiles`, `payroll_employees`
**Pages:** EmployeesPage, EmployeeProfilePage

| Feature | Description | Status |
|---------|-------------|--------|
| Employee profiles | Full profiles: name, SSN (last 4), address, email, phone, hire date, job title, department | ✅ Implemented |
| Employment classification | Full-time/Part-time auto-determination (≥130 monthly hours = FT) | ✅ Implemented |
| Salary & W-2 data | Annual salary, hourly rate, W-2 wages | ✅ Implemented |
| Dependents tracking | Spouse name, number of dependents | ✅ Implemented |
| Coverage tier | Individual, Employee+Spouse, Employee+Children, Family | ✅ Implemented |
| Eligibility status | Auto-calculated: Eligible, Not Eligible, Waiting Period (90-day rule) | ✅ Implemented |
| Mock employee generation | Generate 40-70 realistic employees for testing | ✅ Implemented |
| Individual employee compliance | Per-employee compliance status with plan, offer code, risk assessment | ✅ Implemented |

---

### 3.3 Plan Library
**Collections:** `plan_library`
**Page:** PlanLibraryPage

| Feature | Description | Status |
|---------|-------------|--------|
| Plan CRUD | Create/Edit/Delete medical, dental, vision plans | ✅ Implemented |
| Plan details | Carrier, plan type (PPO/HMO/HDHP/EPO/POS), premiums by tier, employer contributions, deductibles, copays, coinsurance, OOP max | ✅ Implemented |
| CSV upload | Bulk import plans via CSV file | ✅ Implemented |
| CSV template download | Download template for plan data entry | ✅ Implemented |
| MEC badge | Shows if plan meets Minimum Essential Coverage | ✅ Implemented |
| MV badge | Shows MV pass/fail with clear failure reason | ✅ Implemented |
| **Compliance check** | Per-plan MEC + MV (HHS calculator) + Affordability analysis | ✅ Implemented |
| **Employee assignment** | Assign employees to plans with affordability gate | ✅ Implemented |
| **Affordability gate** | FT employees with plan cost > 9.96% of salary are blocked from assignment with tooltip | ✅ Implemented |
| Assignment count badges | Shows how many employees are assigned per plan | ✅ Implemented |
| MV Fail → Actuary Quote | Direct link to request actuarial certification for MV-failing plans | ✅ Implemented |

#### 3.3.1 MV Compliance Logic (HHS Calculator)
- Uses standard population total allowed costs: **$12,500**
- 8 service categories with weighted costs: Inpatient (28%), Outpatient (22%), Physician (20%), Specialist (7%), ER (5%), Generic Rx (8%), Brand Rx (5%), Lab/Imaging (5%)
- Calculation: Deductible → Copays → Coinsurance → OOP Max cap
- **Pass requires BOTH:**
  - Actuarial value ≥ 60% (plan design covers ≥60% of standard costs)
  - Employer contribution ≥ 60% of total premium

#### 3.3.2 Affordability Logic
- **ACA threshold (2026):** Employee cost ≤ 9.96% of annual salary
- **FPL Safe Harbor:** $129.89/month
- Affordability applies only to **full-time employees**
- Per-employee affordability breakdown in compliance check dialog

---

### 3.4 Enrollment Workflow (5-Step Pipeline)
**Collections:** `enrollments`, `plan_assignments`, `eligibility_results`, `enrollment_periods`, `enrollment_exceptions`
**Pages:** EnrollmentReviewPage, EmployeePortalPage, WorkflowPage

#### Step 1: Plan Library Setup (HR Admin)
- Configure carrier plans with premiums, cost-sharing, compliance settings
- Run compliance checks (MEC/MV/Affordability)

#### Step 2: Auto-Eligibility Engine
| Feature | Description | Status |
|---------|-------------|--------|
| Run eligibility | Batch process all employees for FT/PT, affordability, offer codes | ✅ Implemented |
| IRS Offer Codes | Auto-assign 1A-1H based on plan assignments and coverage tiers | ✅ Implemented |
| Safe harbor method | W-2, Rate of Pay, FPL safe harbors | ✅ Implemented |
| Eligibility table | Filterable table showing status, hours, salary, offer code per employee | ✅ Implemented |

#### Step 3: Employee Self-Service Portal
| Feature | Description | Status |
|---------|-------------|--------|
| Employee registration | Register with employer access code | ✅ Implemented |
| View eligible plans | Medical + add-on (dental/vision) plans with details | ✅ Implemented |
| Enroll in plan | Select plan + coverage tier | ✅ Implemented |
| Decline coverage | Decline with reason (too expensive, other coverage, spouse, Medicaid, marketplace, other) | ✅ Implemented |
| View enrolled plan | Dashboard showing enrolled plan details, copays, premiums | ✅ Implemented |
| Download 1095-C | PDF download of IRS Form 1095-C | ✅ Implemented |

#### Step 4: HR Compliance Review
| Feature | Description | Status |
|---------|-------------|--------|
| Enrollment list | Table of all enrollments with status (Enrolled/Declined) | ✅ Implemented |
| Approve enrollments | Single or batch approval | ✅ Implemented |
| Enrollment proof PDF | Generate proof-of-enrollment/decline document | ✅ Implemented |

#### Step 5: Post-Enrollment Actions
| Feature | Description | Status |
|---------|-------------|--------|
| Payroll deduction export | Excel export of employee deductions for ADP | ✅ Implemented |
| Carrier census export | Excel export for insurance carrier | ✅ Implemented |
| Census history | Track generated census files | ✅ Implemented |
| IRS code auto-updates | Offer codes auto-recalculate on enrollment changes | ✅ Implemented |

#### Open Enrollment Period Management
| Feature | Description | Status |
|---------|-------------|--------|
| Create enrollment periods | Named periods with start/end dates | ✅ Implemented |
| Activate/Close periods | Toggle enrollment windows open/closed | ✅ Implemented |
| Exception requests | Employees can request exceptions for closed periods | ✅ Implemented |
| Approve/Deny exceptions | HR reviews and acts on exception requests | ✅ Implemented |

---

### 3.5 ALE Calculator
**Collections:** `ale_calculations`, `employees_headcount`
**Page:** ALECalculatorPage

| Feature | Description | Status |
|---------|-------------|--------|
| Monthly headcount entry | FT count, PT count, PT total hours per month | ✅ Implemented |
| FTE calculation | PT hours / 120 = FTE equivalents | ✅ Implemented |
| ALE determination | Combined FTE ≥ 50 = Applicable Large Employer | ✅ Implemented |
| Custom measurement periods | 2024, 2025, 2026, Last 3/6/9/12 months | ✅ Implemented |
| Penalty estimation | 4980H(a): $3,340/employee; 4980H(b): $5,010/employee | ✅ Implemented |

---

### 3.6 MEC Checker
**Page:** MECTrackingPage

| Feature | Description | Status |
|---------|-------------|--------|
| 7-point MEC checklist | Group health plan, essential benefits, preventive care, no annual/lifetime limits, dependents to 26, no preexisting exclusions | ✅ Implemented |
| Monthly tracking | Month-by-month MEC coverage tracking for the year | ✅ Implemented |
| Compliance percentage | % of FT employees offered MEC | ✅ Implemented |

---

### 3.7 MV Calculator
**Page:** MVCalculatorPage

| Feature | Description | Status |
|---------|-------------|--------|
| HHS MV Calculator | Standard population cost methodology | ✅ Implemented |
| Service category breakdown | 8-category cost analysis with plan vs member split | ✅ Implemented |
| Premium analysis | Employer contribution %, employee cost analysis | ✅ Implemented |
| Standalone calculator form | Manual input of plan parameters for quick MV check | ✅ Implemented |

---

### 3.8 Affordability Calculator
**Page:** AffordabilityPage

| Feature | Description | Status |
|---------|-------------|--------|
| W-2 Safe Harbor | Employee cost ≤ 9.96% of W-2 wages | ✅ Implemented |
| Rate of Pay Safe Harbor | Employee cost ≤ 9.96% of hourly rate × 130 × 12 | ✅ Implemented |
| FPL Safe Harbor | Employee cost ≤ $129.89/month (2026) | ✅ Implemented |
| Per-employee breakdown | Filterable table showing affordable/unaffordable per employee | ✅ Implemented |
| Subsidy risk check | Identify employees likely to seek marketplace subsidies | ✅ Implemented |

---

### 3.9 IRS Forms
**Page:** IRSFormsPage
**Service:** `services/irs_forms.py`

| Feature | Description | Status |
|---------|-------------|--------|
| Form 1094-C data | Employer-level ALE transmittal data | ✅ Implemented |
| Form 1095-C data | Per-employee coverage offer and enrollment data | ✅ Implemented |
| 1094-C PDF | Official IRS layout PDF generation | ✅ Implemented |
| 1095-C PDF | Per-employee PDF with Lines 14-16 codes for all 12 months | ✅ Implemented |
| Offer code reference | IRS code definitions (1A-1H, 2A-2I) | ✅ Implemented |
| Tax year summary | Aggregated statistics for the tax year | ✅ Implemented |
| Employee 1095-C download | Employee portal self-service PDF download | ✅ Implemented |

---

### 3.10 Census Export
**Page:** CensusExportPage

| Feature | Description | Status |
|---------|-------------|--------|
| Generate census | Excel file with employee data + offer codes | ✅ Implemented |
| Census history | Track previously generated census files | ✅ Implemented |
| Download census | Download generated Excel files | ✅ Implemented |

---

### 3.11 Actuary Marketplace
**Collections:** `quote_requests`, `quote_messages`, `notifications`
**Page:** ActuaryMarketplacePage

| Feature | Description | Status |
|---------|-------------|--------|
| Actuary directory | List of registered actuaries with specializations | ✅ Implemented |
| Request quote | Employer requests MV certification for a plan | ✅ Implemented |
| Quote workflow | Pending → Accepted → Paid → Delivered → Validated | ✅ Implemented |
| Real-time chat | Message exchange between employer and actuary per quote | ✅ Implemented |
| Document exchange | Upload/download documents within quotes | ✅ Implemented |
| Payment flow | Simulated payment processing | ✅ Implemented |
| Deliver certification | Actuary submits MV percentage + notes | ✅ Implemented |
| Validate/Reject | Employer validates or rejects delivered certification | ✅ Implemented |
| Notifications | In-app notification system for quote updates | ✅ Implemented |

---

### 3.12 ADP Payroll Integration
**Collections:** `adp_connections`
**Route:** `routes/adp.py`

| Feature | Description | Status |
|---------|-------------|--------|
| OAuth 2.0 connect | Connect to ADP Workforce Now | ✅ Implemented |
| Sync employees | Pull employee data from ADP | ✅ Implemented |
| Disconnect | Remove ADP connection | ✅ Implemented |
| Connection status | Show ADP connection state | ✅ Implemented |

---

### 3.13 Dashboard & Predictive Intelligence
**Page:** DashboardPage
**Route:** `routes/predictive.py`

| Feature | Description | Status |
|---------|-------------|--------|
| Compliance dashboard | Workforce stats, MEC coverage %, MV status, risk alerts | ✅ Implemented |
| Predictive alerts | Rule-based compliance risk alerts (MEC gap, MV failure, affordability risk, ALE status) | ✅ Implemented |
| Growth projection | FTE trend forecasting with hiring scenarios | ✅ Implemented |
| Financial exposure | Penalty exposure analysis (4980H(a) + 4980H(b)) | ✅ Implemented |
| Scenario modeling | What-if analysis for plan changes, hiring, terminations | ✅ Implemented |
| AI summary | AI-powered compliance narrative (requires LLM integration) | ✅ Implemented |

---

### 3.14 Compliance Workflow
**Page:** WorkflowPage

| Feature | Description | Status |
|---------|-------------|--------|
| 5-step guided workflow | Visual step-by-step ACA compliance process | ✅ Implemented |
| Step execution | Run each compliance step with progress tracking | ✅ Implemented |
| Run all steps | Execute complete compliance pipeline in sequence | ✅ Implemented |

---

## 4. Data Model (MongoDB Collections)

| Collection | Purpose | Key Fields |
|-----------|---------|------------|
| `users` | Authentication | id, email, password (bcrypt), name, role, company_name |
| `employers` | Company profiles | id, user_id, name, ein, address, employer_code |
| `employee_profiles` | Employee data | id, employer_id, name, hire_date, salary, employment_type, eligibility_status |
| `payroll_employees` | Payroll data (mock/ADP) | id, employer_id, name, weekly_hours, annual_salary |
| `plan_library` | Health plans | id, employer_id, plan_name, premiums, employer_contribution, employee_cost, mv_percentage, mv_certified, mec_qualified |
| `plan_assignments` | HR plan offers | plan_id, employee_id, employer_id |
| `enrollments` | Employee responses | employee_id, plan_id, status (enrolled/declined), coverage_tier |
| `eligibility_results` | Calculated eligibility | employee_id, eligible, offer_code, affordable |
| `ale_calculations` | ALE determinations | employer_id, year, total_fte, is_ale |
| `employees_headcount` | Monthly headcount data | employer_id, year, month, ft_count, pt_count |
| `mec_tracking` | Monthly MEC compliance | employer_id, year, month, coverage_percentage |
| `certifications` | MV certifications (legacy) | employer_id, plan_id, status |
| `quote_requests` | Actuary marketplace quotes | employer_id, actuary_id, plan_id, status |
| `quote_messages` | Chat messages | quote_id, sender_id, message |
| `enrollment_periods` | Open enrollment windows | employer_id, start_date, end_date, status |
| `enrollment_exceptions` | Enrollment exception requests | employee_id, employer_id, reason, status |
| `census_exports` | Generated census files | employer_id, file_data |
| `notifications` | In-app notifications | user_id, type, message, read |
| `adp_connections` | ADP OAuth connections | employer_id, access_token, status |
| `compliance_workflows` | Workflow step state | employer_id, steps |

---

## 5. API Architecture

**Total API endpoints: ~100+**

| Module | Prefix | Count |
|--------|--------|-------|
| Auth | `/api/auth/*` | 3 |
| Employers | `/api/employers/*` | 3 |
| Employee Profiles | `/api/employee-profiles/*` | 7 |
| Plans (legacy) | `/api/plans/*` | 4 |
| MV Calculator | `/api/mv/*` | 3 |
| ALE Calculator | `/api/ale/*` | 2 |
| MEC | `/api/mec/*` | 3 |
| Payroll | `/api/payroll/*` | 4 |
| Affordability | `/api/affordability/*` | 2 |
| Dashboard | `/api/dashboard/*` | 3 |
| IRS Forms | `/api/irs-forms/*` | 7 |
| Workflow | `/api/workflow/*` | 3 |
| Certifications | `/api/certifications/*` | 4 |
| Enrollment Workflow | `/api/enrollment/*` | 30+ |
| Marketplace | `/api/marketplace/*` | 12 |
| Predictive | `/api/predictive/*` | 5 |
| ADP | `/api/adp/*` | 5 |
| Notifications | `/api/notifications/*` | 3 |

---

## 6. Phased Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Core infrastructure, auth, employer/employee management

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 1.1 | Project setup (FastAPI + React + MongoDB + Tailwind) | P0 | Low |
| 1.2 | JWT Authentication (register, login, session) | P0 | Medium |
| 1.3 | Role-based access (Employer, Employee, Actuary) | P0 | Medium |
| 1.4 | Employer CRUD (name, EIN, address, multi-employer) | P0 | Low |
| 1.5 | Employee profiles CRUD (personal + employment data) | P0 | Medium |
| 1.6 | Employee classification engine (FT/PT by hours) | P0 | Low |
| 1.7 | Dashboard layout with sidebar navigation | P0 | Medium |
| 1.8 | Mock employee generation for testing | P1 | Low |

**Deliverable:** Working app with auth, employer management, employee database

---

### Phase 2: Plan Management & Compliance Engines (Weeks 4-6)
**Goal:** Plan library with full ACA compliance checking

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 2.1 | Plan Library CRUD (medical/dental/vision) | P0 | Medium |
| 2.2 | Plan CSV upload/download | P1 | Medium |
| 2.3 | HHS MV Calculator (standard population methodology) | P0 | High |
| 2.4 | MEC compliance checker (7-point checklist) | P0 | Medium |
| 2.5 | Affordability calculator (W-2 / Rate of Pay / FPL safe harbors) | P0 | High |
| 2.6 | Per-plan compliance check dialog (MEC + MV + Affordability) | P0 | High |
| 2.7 | MV/MEC badge system on plan cards | P1 | Low |
| 2.8 | Monthly MEC tracking | P1 | Medium |

**Deliverable:** Full plan management with automated compliance analysis

---

### Phase 3: Eligibility & Assignment (Weeks 7-9)
**Goal:** Eligibility engine, plan assignment with affordability gates

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 3.1 | Auto-eligibility engine (batch FT/PT/affordability/offer codes) | P0 | High |
| 3.2 | IRS offer code assignment (1A-1H logic) | P0 | High |
| 3.3 | Employee-to-plan assignment UI | P0 | Medium |
| 3.4 | Affordability gate in assignment (disable unaffordable FT employees) | P0 | High |
| 3.5 | Affordability tooltip with salary/threshold details | P1 | Medium |
| 3.6 | Select All respects affordability constraints | P1 | Low |
| 3.7 | Assignment count badges on plan cards | P1 | Low |

**Deliverable:** Automated eligibility with compliant plan assignment

---

### Phase 4: ALE Calculator & Workforce Analysis (Weeks 10-11)
**Goal:** Full ALE determination with headcount tracking

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 4.1 | Monthly headcount data entry | P0 | Medium |
| 4.2 | FTE calculation engine | P0 | Medium |
| 4.3 | ALE determination (≥50 FTE threshold) | P0 | Low |
| 4.4 | Custom measurement periods | P1 | Medium |
| 4.5 | Penalty estimation (4980H(a) and 4980H(b)) | P1 | Medium |

**Deliverable:** Complete ALE status determination

---

### Phase 5: Enrollment Workflow (Weeks 12-15)
**Goal:** End-to-end enrollment from employee portal to HR review

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 5.1 | Employer access code generation | P0 | Low |
| 5.2 | Employee self-registration with employer code | P0 | Medium |
| 5.3 | Employee portal — view eligible plans | P0 | High |
| 5.4 | Employee enroll flow (plan + tier selection) | P0 | High |
| 5.5 | Employee decline flow (reason + detail) | P0 | Medium |
| 5.6 | Enrolled plan dashboard view | P1 | Medium |
| 5.7 | HR enrollment review table (enrolled/declined) | P0 | Medium |
| 5.8 | Single + batch enrollment approval | P0 | Medium |
| 5.9 | Enrollment proof PDF generation | P1 | Medium |
| 5.10 | Open enrollment period management (create/activate/close) | P1 | High |
| 5.11 | Enrollment exception requests + approval | P2 | Medium |
| 5.12 | IRS offer code auto-recalculation on enrollment changes | P0 | High |

**Deliverable:** Complete enrollment lifecycle with self-service employee portal

---

### Phase 6: IRS Reporting & Census Export (Weeks 16-18)
**Goal:** Official IRS form generation and carrier data export

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 6.1 | Form 1094-C data generation | P0 | High |
| 6.2 | Form 1095-C data generation (all 12 months, Lines 14-16) | P0 | High |
| 6.3 | 1094-C PDF generation (official IRS layout) | P0 | High |
| 6.4 | 1095-C PDF generation per employee | P0 | High |
| 6.5 | Employee 1095-C self-service download | P1 | Medium |
| 6.6 | Tax year summary statistics | P1 | Medium |
| 6.7 | Census Excel export with offer codes | P0 | Medium |
| 6.8 | Payroll deduction export (ADP format) | P1 | Medium |
| 6.9 | Carrier census export | P1 | Medium |
| 6.10 | Census history tracking | P2 | Low |

**Deliverable:** Complete IRS reporting suite with PDF generation

---

### Phase 7: Post-Enrollment & Payroll Integration (Weeks 19-21)
**Goal:** ADP integration and post-enrollment actions

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 7.1 | ADP OAuth 2.0 connection flow | P1 | High |
| 7.2 | ADP employee data sync | P1 | High |
| 7.3 | ADP disconnect | P1 | Low |
| 7.4 | Payroll summary with ADP/mock data source | P1 | Medium |
| 7.5 | Mock payroll generation | P1 | Medium |

**Deliverable:** Payroll integration with ADP

---

### Phase 8: Actuary Marketplace (Weeks 22-25)
**Goal:** Full marketplace for actuarial certification services

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 8.1 | Actuary directory listing | P1 | Medium |
| 8.2 | Quote request workflow (Pending → Accepted → Paid → Delivered) | P1 | High |
| 8.3 | Real-time chat per quote | P1 | High |
| 8.4 | Document upload/download in quotes | P1 | Medium |
| 8.5 | Payment simulation | P2 | Medium |
| 8.6 | MV certification delivery | P1 | High |
| 8.7 | Certification validation/rejection by employer | P1 | Medium |
| 8.8 | Notification system | P1 | Medium |
| 8.9 | Actuary dashboard overview | P2 | Medium |

**Deliverable:** Functioning marketplace connecting employers with actuaries

---

### Phase 9: Predictive Intelligence (Weeks 26-28)
**Goal:** AI-powered compliance forecasting and risk analysis

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 9.1 | Rule-based compliance alerts (MEC gap, MV fail, affordability risk) | P1 | High |
| 9.2 | Growth projection (FTE trend forecasting) | P2 | Medium |
| 9.3 | Financial exposure analysis (penalty calculations) | P1 | High |
| 9.4 | Scenario modeling (what-if for plan changes, hiring, terminations) | P2 | High |
| 9.5 | AI-powered compliance summary (LLM integration) | P2 | High |

**Deliverable:** Predictive compliance intelligence dashboard

---

### Phase 10: Polish & Production Readiness (Weeks 29-32)
**Goal:** Production-quality application with full testing

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 10.1 | Compliance workflow (5-step guided process) | P1 | Medium |
| 10.2 | Forgot password flow | P1 | Medium |
| 10.3 | Password strength enforcement | P1 | Low |
| 10.4 | Email verification | P2 | Medium |
| 10.5 | Batch 1095-C PDF download (zip) | P2 | Medium |
| 10.6 | SBC document parser | P2 | High |
| 10.7 | Email notifications (enrollment, compliance alerts) | P2 | High |
| 10.8 | CSV employee import | P2 | Medium |
| 10.9 | Multi-year tracking | P2 | High |
| 10.10 | Performance optimization & caching | P1 | Medium |
| 10.11 | Comprehensive test suite | P1 | High |
| 10.12 | Security audit (input validation, rate limiting) | P1 | Medium |

**Deliverable:** Production-ready application

---

## 7. At-Risk Employee Logic

An employee is flagged **at-risk** when ACA penalty exposure exists:

| Scenario | Risk Type | Penalty |
|----------|-----------|---------|
| FT employee not offered MEC | 4980H(a) | $3,340/employee (minus first 30) |
| FT employee on MV-failing plan | 4980H(b) | $5,010/employee |
| FT employee on unaffordable plan | 4980H(b) | $5,010/employee |

**NOT at-risk:** Employer has MEC+MV compliant plans available; employee was offered coverage (regardless of acceptance/decline).

---

## 8. Regulatory Constants (2026 Tax Year)

| Constant | Value | Usage |
|----------|-------|-------|
| ACA Affordability Threshold | 9.96% | Max % of employee income for self-only coverage |
| FPL Safe Harbor | $129.89/month | Alternative affordability test |
| MV Threshold | 60% | Minimum actuarial value for plan design |
| Employer Contribution Threshold | 60% | Minimum employer premium share |
| FTE Threshold | 50 | ALE determination |
| FT Hours (Monthly) | 130 | Full-time classification |
| FT Hours (Weekly) | 30 | Full-time classification |
| 4980H(a) Penalty | $3,340 | Per FT employee (minus 30) |
| 4980H(b) Penalty | $5,010 | Per affected employee |
| Standard Population Cost | $12,500 | HHS MV Calculator basis |

---

## 9. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Response time | < 500ms for API calls, < 2s for complex calculations |
| Concurrent users | 100+ simultaneous users |
| Data retention | 7+ years (IRS requirement) |
| Browser support | Chrome, Firefox, Safari, Edge (latest 2 versions) |
| PDF generation | < 5s per form |
| File uploads | Up to 10MB per document |
| Uptime | 99.5% availability |

---

## 10. Current Codebase Metrics

| Metric | Value |
|--------|-------|
| Total lines of code | ~16,000+ |
| Backend files | 7 (server.py + 4 routes + 3 services) |
| Frontend pages | 17 |
| API endpoints | 100+ |
| MongoDB collections | 23 |
| Dependencies (backend) | 127 packages |
| Dependencies (frontend) | 55 packages |
