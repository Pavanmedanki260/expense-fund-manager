# FundTrack Test Credentials (Email/Password Auth)

## Admin Account (Super Admin)
- Email: admin@fundtrack.com
- Password: Admin@123
- is_super_admin: true

## Test Users (registered via API)
- Ravi Kumar: ravi@test.com / Ravi@123
- Priya Sharma: priya@test.com / Priya@123

## Auth Type
- Email + Password with JWT tokens
- JWT stored in httpOnly cookies (access_token + refresh_token)
- For API testing: login first to get cookies, or use Bearer token from login response

## API Endpoints
- POST /api/auth/register - Register (name, email, password)
- POST /api/auth/login - Login (email, password)
- GET /api/auth/me - Current user
- POST /api/auth/logout - Logout
- POST /api/auth/refresh - Refresh token

## Groups, Funds, Utilizations
- All scoped under /api/groups/{groupId}/...
- Roles per group: admin/contributor/viewer
