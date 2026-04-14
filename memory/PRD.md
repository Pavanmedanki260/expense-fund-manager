# FundTrack - Product Requirements Document

## Overview
FundTrack is a mobile-first responsive web application for organizations to track fund collections and utilizations with real-time analytics.

## Architecture
- **Frontend**: React 18 + Recharts + React Router + react-hot-toast
- **Backend**: FastAPI (Python) + MongoDB (Motor async driver)
- **Auth**: Emergent-managed Google OAuth
- **Export**: openpyxl for server-side Excel generation

## User Personas
1. **Admin** - Full access: manage users, edit/delete any entry, download reports
2. **Contributor** - Can add/edit their own fund/utilization entries
3. **Viewer** - Read-only access to dashboard and reports

## Core Requirements
- Google Social Login only (no email/password)
- INR currency with Indian number formatting
- Light/Dark theme toggle (persisted to localStorage)
- Role-based access control (Admin/Contributor/Viewer)

## What's Been Implemented (April 14, 2026)

### Backend (server.py)
- Google OAuth session exchange with Emergent Auth
- Auth middleware (cookie + Bearer token)
- Fund CRUD (create/read/update/delete) with ownership checks
- Utilization CRUD with linked fund validation
- Dashboard aggregation (totals, category breakdown, monthly data, activity feed)
- User management (list, role update, status toggle) - admin only
- Excel export with 3 sheets (Funds, Utilization, Summary)
- Health check endpoint

### Frontend
- **Login Page**: Split-screen layout, Google Sign-In button
- **Dashboard**: 4 KPI cards, PieChart (category breakdown), BarChart (monthly), activity feed
- **Fund Collection**: Searchable/filterable list, add/edit modal, delete confirmation
- **Utilization**: Filterable list, add/edit modal, linked fund dropdown
- **Reports**: Date range filters, charts, Excel download
- **User Management**: Role dropdowns, activate/deactivate users
- **Layout**: Sidebar navigation, responsive hamburger menu, theme toggle
- **ThemeContext**: Light/Dark theme with CSS variables
- **AuthContext**: Session management, protected routes

### Testing Results
- Backend: 100% (29/29 tests passed)
- Frontend: 95% (all features working, minor mobile automation issue)

## Prioritized Backlog

### P0 (Done)
- [x] Auth with Google OAuth
- [x] Dashboard with charts
- [x] Fund CRUD
- [x] Utilization CRUD
- [x] Reports & Excel export
- [x] User management
- [x] Theme toggle
- [x] Mobile responsive design

### P1 (Next)
- [ ] Fund-level utilization tracking (show % utilized per fund with status badges)
- [ ] Offline caching for dashboard data (Service Worker)
- [ ] File attachment upload for funds/utilizations
- [ ] Pagination for large lists

### P2 (Future)
- [ ] Email notifications for role changes
- [ ] Audit log for all CRUD operations
- [ ] Multi-currency support
- [ ] PDF report generation
- [ ] Invite users by email flow
