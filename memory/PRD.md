# FundTrack - Product Requirements Document

## Overview
FundTrack is a mobile-first responsive web application enabling organizations to manage multiple fund groups, each with isolated fund collections, utilizations, and member access. Features per-group role-based access control, email invitations, and a Super Admin who can view all groups.

## Architecture
- **Frontend**: React 18 + Recharts + React Router + react-hot-toast
- **Backend**: FastAPI (Python) + MongoDB (Motor async driver)
- **Auth**: Emergent-managed Google OAuth
- **Email**: Resend API for invitation emails
- **Export**: openpyxl for server-side Excel generation

## User Personas
1. **Super Admin** (Global) - First user to register. Can see ALL groups, create groups, manage everything
2. **Group Admin** - Full access within a specific group: manage members, invite users, edit/delete any entry
3. **Contributor** - Can add/edit their own fund/utilization entries within their groups
4. **Viewer** - Read-only access to group dashboard and reports

## Core Architecture: Multi-Group
- Each fund group is isolated with its own funds, utilizations, dashboard, and members
- Roles are **per-group** (a user can be Admin in Group A but Viewer in Group B)
- Super Admin bypasses group membership checks and sees all groups
- Email invitations: Admin invites by email → Resend sends invite → user clicks link → logs in → auto-joins group

## Data Models
- `users`: { user_id, name, email, avatar_url, is_super_admin, is_active }
- `groups`: { group_id, name, description, created_by_user_id }
- `group_members`: { group_id, user_id, role }
- `invitations`: { invite_id, group_id, email, role, status, invited_by }
- `funds`: { fund_id, group_id, source_name, amount_inr, category, ... }
- `utilizations`: { util_id, group_id, purpose, amount_inr, linked_fund_id, ... }

## What's Been Implemented

### Phase 1 (April 14, 2026) - Single-tracker MVP
- Google OAuth, fund/utilization CRUD, dashboard, charts, Excel export, user management

### Phase 2 (April 20, 2026) - Multi-Group Architecture
- **Groups**: Create, list, view, delete fund groups
- **Group-scoped data**: All funds, utilizations, dashboard, reports scoped to group_id
- **Per-group roles**: Admin/Contributor/Viewer per group
- **Super Admin**: Global admin sees all groups with badge
- **Email Invitations**: Resend API integration, invitation accept flow
- **Members Management**: List members, change roles, remove members, view pending invitations
- **Group Navigation**: Groups list → Group sidebar with back navigation
- **Accept Invite Page**: Standalone page for invitation acceptance

### Testing Results (Phase 2)
- Backend: 100% (23/23 tests passed)
- Frontend: 95% (all core features working)

## Prioritized Backlog

### P0 (Done)
- [x] Multi-group architecture
- [x] Per-group RBAC
- [x] Email invitations via Resend
- [x] Group-scoped dashboard with charts
- [x] Group-scoped fund/utilization CRUD
- [x] Excel export per group
- [x] Member management
- [x] Theme toggle (light/dark)

### P1 (Next)
- [ ] Fund-level utilization tracking with status badges (green/amber/red per fund)
- [ ] Super Admin aggregated dashboard across all groups
- [ ] File attachment upload for funds/utilizations
- [ ] Pagination for large lists

### P2 (Future)
- [ ] Offline caching via Service Worker
- [ ] Audit log for all CRUD operations
- [ ] Budget alerts per fund category
- [ ] Custom sender domain for Resend emails
