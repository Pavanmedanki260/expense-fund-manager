# FundTrack Test Credentials (Multi-Group Architecture)

## Test Users

### Super Admin
- Email: admin@fundtrack.test
- User ID: user_testadmin001
- Session Token: test_session_admin_001
- is_super_admin: true (can see all groups)

### Contributor User
- Email: contributor@fundtrack.test
- User ID: user_testcontrib01
- Session Token: test_session_contrib_001
- is_super_admin: false

### Viewer User
- Email: viewer@fundtrack.test
- User ID: user_testviewer001
- Session Token: test_session_viewer_001
- is_super_admin: false

## Auth Type
- Emergent-managed Google OAuth (Google Social Login)
- Session tokens set via httpOnly cookies
- For API testing, use Authorization header: `Bearer <session_token>`

## Test Groups

### Group 1: Education Fund 2025
- Group ID: grp_education01
- Members: admin (admin role), contributor (contributor role), viewer (viewer role)
- Has 3 funds, 2 utilizations seeded

### Group 2: CSR Fund Q1
- Group ID: grp_csrfund0001
- Members: admin (admin role), contributor (contributor role)
- Viewer is NOT a member (should get 403)
- Has 2 funds, 1 utilization seeded

## Sample Fund IDs
- fund_edu001, fund_edu002, fund_edu003 (Group 1)
- fund_csr001, fund_csr002 (Group 2)

## API Endpoints (all group-scoped)
- Groups: /api/groups, /api/groups/{groupId}
- Funds: /api/groups/{groupId}/funds
- Utilizations: /api/groups/{groupId}/utilizations
- Dashboard: /api/groups/{groupId}/dashboard
- Members: /api/groups/{groupId}/members
- Invite: /api/groups/{groupId}/invite
- Export: /api/groups/{groupId}/export/excel

## Resend API
- Key: configured in backend .env
- Sender: onboarding@resend.dev (testing mode)
