# Restaurant Labor-Cost Dashboard Micro SaaS
## Complete Technical Blueprint + Vibe Coding Reference

---

# 1. Project Overview

## Working Product Names
- ShiftPulse
- LaborIQ
- StaffSight
- KitchenMetrics
- LaborLens

---

# 2. Core Product Idea

A lightweight SaaS platform for restaurants that:
- tracks labor costs
- analyzes staffing efficiency
- imports payroll/POS data
- provides AI-generated operational insights
- helps owners reduce labor waste

Primary goal:
> Give independent restaurants enterprise-style labor analytics without enterprise complexity.

---

# 3. Target Market

## Ideal Customers
- Independent restaurants
- Small chains (1–5 locations)
- Bars
- Cafes
- Fast casual restaurants
- Food trucks

## Why This Market Works
Restaurants:
- already pay for software
- constantly monitor margins
- have recurring operational pain
- rely heavily on labor optimization

---

# 4. Core MVP Features

## Authentication
- Email/password login
- Password reset
- Role-based permissions
- Restaurant-level access control

---

## Dashboard

### KPI Widgets
- Total Sales
- Labor Cost
- Labor Cost %
- Sales Per Labor Hour
- Overtime Hours
- Weekly Trends

---

## CSV Upload System

Supported imports:
- Toast exports
- Square exports
- QuickBooks exports
- 7Shifts exports
- Manual payroll CSVs

Requirements:
- drag-and-drop upload
- CSV validation
- preview before import
- error handling

---

## AI Insights

Generate:
- staffing recommendations
- labor inefficiency alerts
- overtime warnings
- slow shift analysis
- staffing trend summaries

Example:
> Tuesday lunch shifts appear overstaffed by approximately 18%.

---

## Email Alerts

Examples:
- Overtime approaching
- Labor % exceeds threshold
- Weekly summary reports
- AI operational recommendations

---

# 5. Recommended Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js |
| Backend | Node.js |
| Styling | Tailwind CSS |
| Database | Supabase |
| Auth | Supabase Auth |
| Hosting | Vercel or Hostinger |
| Automation | n8n |
| AI API | OpenRouter |
| Payments | Stripe |
| Charts | Recharts |
| ORM | Prisma |
| File Storage | Supabase Storage |

---

# 6. Recommended Folder Structure

```txt
restaurant-saas/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── dashboard/
│   ├── auth/
│   ├── uploads/
│   └── charts/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── ai/
│   ├── parsers/
│   ├── jobs/
│   └── middleware/
│
├── database/
│   ├── schema.sql
│   ├── migrations/
│   └── seeds/
│
├── n8n/
│   ├── workflows/
│   └── templates/
│
├── prompts/
│   └── ai-prompts.md
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── roadmap.md
│
└── README.md
```

---

# 7. Core Database Schema

## restaurants

```sql
CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_email TEXT,
    plan_type TEXT DEFAULT 'starter',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## employees

```sql
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID REFERENCES restaurants(id),
    name TEXT NOT NULL,
    role TEXT,
    hourly_rate NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## shifts

```sql
CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(id),
    restaurant_id UUID REFERENCES restaurants(id),
    clock_in TIMESTAMP,
    clock_out TIMESTAMP,
    hours_worked NUMERIC,
    labor_cost NUMERIC,
    shift_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## sales

```sql
CREATE TABLE sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID REFERENCES restaurants(id),
    sales_date DATE,
    gross_sales NUMERIC,
    net_sales NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## ai_insights

```sql
CREATE TABLE ai_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID REFERENCES restaurants(id),
    insight_text TEXT,
    severity TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 8. Key Business Calculations

## Labor Cost Percentage

```txt
Labor Cost % = Labor Cost / Sales * 100
```

---

## Sales Per Labor Hour

```txt
Sales Per Labor Hour = Total Sales / Total Labor Hours
```

---

## Overtime Detection

```txt
IF employee_hours > 40 THEN flag_overtime
```

---

# 9. Frontend Pages

## Public Pages
- Landing page
- Pricing page
- Login page
- Signup page
- Demo request page

---

## App Pages

### Dashboard
Displays:
- charts
- KPIs
- alerts
- trends

### Uploads
- upload CSVs
- validate imports
- import history

### Employees
- employee management
- overtime tracking
- labor analysis

### Reports
- weekly reports
- labor summaries
- export PDF/CSV

### AI Insights
- operational recommendations
- anomaly detection
- staffing suggestions

### Settings
- billing
- integrations
- restaurant profile

---

# 10. API Design

## Auth Routes

```txt
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
```

---

## Upload Routes

```txt
POST /api/upload/payroll
POST /api/upload/sales
```

---

## Dashboard Routes

```txt
GET /api/dashboard/kpis
GET /api/dashboard/trends
GET /api/dashboard/alerts
```

---

## AI Routes

```txt
POST /api/ai/analyze
GET /api/ai/insights
```

---

# 11. CSV Parsing Logic

## Required Features
- column mapping
- date normalization
- missing value handling
- duplicate detection
- validation rules

---

## Example Workflow

```txt
Upload CSV
→ Validate Headers
→ Parse Rows
→ Normalize Dates
→ Calculate Labor Costs
→ Save to Database
→ Trigger Dashboard Refresh
```

---

# 12. n8n Workflow Ideas

## Payroll Import Workflow

```txt
Webhook Trigger
→ Download CSV
→ Parse CSV
→ Validate Data
→ Insert Into Supabase
→ Send Confirmation Email
```

---

## AI Analysis Workflow

```txt
Cron Trigger
→ Pull Restaurant Metrics
→ Send Metrics to OpenRouter
→ Receive Insights
→ Save Insights
→ Email Restaurant Owner
```

---

## Weekly Report Workflow

```txt
Weekly Cron
→ Generate KPI Summary
→ Build Report
→ Email PDF
```

---

# 13. AI Integration Plan

## OpenRouter Use Cases

### Labor Optimization
Analyze:
- staffing levels
- overtime
- labor efficiency
- sales trends

---

## Example AI Prompt

```txt
You are a restaurant operations analyst.

Analyze:
- labor percentages
- overtime usage
- sales trends
- staffing levels

Provide:
- operational recommendations
- labor optimization ideas
- anomalies
- staffing suggestions

Be concise and practical.
```

---

# 14. AI Output Example

```txt
Insights:

1. Friday dinner shifts generate the highest revenue per labor hour.

2. Tuesday lunch shifts appear consistently overstaffed.

3. Overtime costs increased 22% week-over-week.

4. Consider reducing staffing by one employee during low-volume afternoon periods.
```

---

# 15. Dashboard Chart Ideas

## Recommended Charts
- Labor % over time
- Sales vs labor hours
- Revenue by shift
- Overtime trends
- Weekly staffing efficiency
- AI anomaly alerts

---

# 16. Authentication Architecture

## Recommended Approach
Use Supabase Auth.

Benefits:
- simple setup
- secure sessions
- social auth options
- JWT support
- row-level security

---

# 17. Multi-Tenant Security

Critical requirement:
> Restaurants must NEVER access other restaurant data.

---

## Recommended Strategy
Use:
- Row-Level Security
- restaurant_id filtering
- protected API middleware

---

# 18. Stripe Billing Setup

## Pricing Ideas

| Plan | Price |
|---|---|
| Starter | $19/month |
| Pro | $49/month |
| Multi-Location | $99/month |

---

## Stripe Features
- subscriptions
- free trial
- usage billing
- webhooks
- invoice handling

---

# 19. MVP Development Roadmap

## Phase 1 — Setup

### Goals
- initialize Next.js app
- connect Supabase
- configure auth
- setup Tailwind

---

## Phase 2 — Core Backend

### Goals
- create database schema
- build upload endpoints
- create KPI calculations
- create dashboard APIs

---

## Phase 3 — Frontend Dashboard

### Goals
- charts
- KPI cards
- upload UI
- reports UI

---

## Phase 4 — Automation

### Goals
- n8n workflows
- scheduled jobs
- email alerts
- CSV automation

---

## Phase 5 — AI Layer

### Goals
- AI recommendations
- anomaly detection
- operational summaries

---

## Phase 6 — Production

### Goals
- Stripe integration
- deployment
- monitoring
- backups
- onboarding flow

---

# 20. Recommended MVP Priorities

## MUST HAVE
- auth
- CSV upload
- dashboard
- KPI calculations
- charts

---

## NICE TO HAVE
- AI insights
- email alerts
- API integrations
- forecasting

---

# 21. Things NOT To Build Initially

Avoid:
- mobile apps
- enterprise integrations
- custom hardware
- advanced forecasting
- multi-language support
- complicated permissions

Keep the MVP small.

---

# 22. Example Vibe Coding Prompts

## Dashboard Prompt

```txt
Build a modern restaurant analytics dashboard using Next.js and Tailwind.

Requirements:
- KPI cards
- labor cost charts
- overtime alerts
- responsive layout
- clean SaaS UI
- dark mode support
```

---

## CSV Upload Prompt

```txt
Create a drag-and-drop CSV upload component in React.

Requirements:
- preview parsed rows
- validate headers
- show upload progress
- display import errors
- support payroll CSV imports
```

---

## AI Insights Prompt

```txt
Build an AI insights panel for a restaurant labor dashboard.

Requirements:
- display operational recommendations
- show severity badges
- support loading states
- clean card-based UI
```

---

# 23. Example Initial Landing Page Copy

## Headline

```txt
Reduce Restaurant Labor Costs With AI-Powered Insights
```

---

## Subheadline

```txt
Connect payroll and sales data to instantly monitor labor efficiency, overtime, and staffing performance.
```

---

# 24. Suggested Initial Workflow

## Realistic Founder Strategy

### Step 1
Build basic MVP.

### Step 2
Test with 1–3 local restaurants.

### Step 3
Manually onboard customers.

### Step 4
Refine based on feedback.

### Step 5
Add AI automation.

### Step 6
Scale acquisition.

---

# 25. Potential Expansion Features

Future possibilities:
- forecasting
- schedule optimization
- labor benchmarking
- POS integrations
- payroll syncing
- mobile app
- SMS alerts
- AI chat assistant
- manager scorecards
- shift recommendations

---

# 26. Biggest Risks

## Technical Risks
- inconsistent CSV formats
- multi-tenant security
- inaccurate AI recommendations
- integration maintenance

---

## Business Risks
- weak customer acquisition
- low retention
- building unnecessary features
- insufficient niche focus

---

# 27. Recommended Initial Stack Commands

## Next.js App

```bash
npx create-next-app@latest restaurant-saas
```

---

## Install Tailwind

```bash
npm install -D tailwindcss
```

---

## Install Prisma

```bash
npm install prisma @prisma/client
```

---

## Install Supabase

```bash
npm install @supabase/supabase-js
```

---

## Install Recharts

```bash
npm install recharts
```

---

## Install CSV Parser

```bash
npm install papaparse
```

---

# 28. Recommended Initial Build Order

1. Auth
2. Database
3. Dashboard
4. CSV upload
5. KPI calculations
6. Charts
7. AI insights
8. Stripe billing
9. Automation
10. Integrations

---

# 29. Recommended Infrastructure

## Cheap MVP Stack

| Service | Cost |
|---|---|
| Vercel | Free tier |
| Supabase | Free tier |
| OpenRouter | Usage-based |
| n8n | Self-hosted |
| Stripe | Transaction fees |

Possible to launch extremely cheaply.

---

# 30. Final Strategic Advice

The biggest mistake solo founders make:
> building too much before validating demand.

Best approach:
- solve one painful problem
- keep the MVP tiny
- manually support early customers
- automate repeated workflows later

Focus on:
> operational usefulness over technical complexity.

That is how many successful Micro SaaS businesses actually begin.

