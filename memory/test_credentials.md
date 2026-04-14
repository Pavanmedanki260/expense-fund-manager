# FundTrack Test Credentials

## Test Users (seeded in MongoDB)

### Admin User
- Email: admin@fundtrack.test
- User ID: user_testadmin001
- Session Token: test_session_admin_001
- Role: admin

### Contributor User
- Email: contributor@fundtrack.test
- User ID: user_testcontrib01
- Session Token: test_session_contrib_001
- Role: contributor

### Viewer User
- Email: viewer@fundtrack.test
- User ID: user_testviewer001
- Session Token: test_session_viewer_001
- Role: viewer

## Authentication
- Auth Type: Emergent-managed Google OAuth (Google Social Login)
- No email/password auth
- Session tokens are set via cookies
- For testing, use Authorization header: `Bearer <session_token>`

## Database
- MongoDB: fundtrack
- Collections: users, user_sessions, funds, utilizations

## Sample Fund IDs (seeded)
- fund_seed001: Corporate Donation - TCS (₹5,00,000)
- fund_seed002: Government Grant - Education (₹12,00,000)
- fund_seed003: Workshop Revenue (₹75,000)
- fund_seed004: Individual Donation - Rahul (₹25,000)
- fund_seed005: Misc Fund (₹30,000)

## Sample Utilization IDs (seeded)
- util_seed001 to util_seed005
