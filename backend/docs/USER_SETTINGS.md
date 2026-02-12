# User Settings and 2FA Management

This guide covers user profile management, settings configuration, and Two-Factor Authentication (2FA) setup in the FastAPI template.

## Table of Contents
- [Overview](#overview)
- [User Profile Fields](#user-profile-fields)
- [Managing Your Profile](#managing-your-profile)
- [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
- [Email Verification](#email-verification)
- [Phone Verification](#phone-verification)
- [User Preferences](#user-preferences)
- [API Reference](#api-reference)

## Overview

Each user account has:
- **Profile Information**: Name, contact details, bio, avatar
- **Security Settings**: 2FA, email/phone verification
- **Preferences**: Timezone, language
- **Activity Tracking**: Login history, account timestamps

All settings are **per-user** and can be managed independently.

## User Profile Fields

### Core Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username (3-50 chars) |
| `email` | string | Yes | Unique email address |
| `password` | string | Yes (create) | Securely hashed password (8-100 chars) |
| `first_name` | string | No | User's first name (max 50 chars) |
| `last_name` | string | No | User's last name (max 50 chars) |

### Contact & Profile

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `phone_number` | string | null | Phone number (max 20 chars) |
| `phone_verified` | boolean | false | Phone verification status |
| `avatar_url` | string | null | Profile picture URL (max 500 chars) |
| `bio` | text | null | User bio/description |

### Settings & Preferences

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timezone` | string | "UTC" | User's timezone (e.g., "America/New_York") |
| `language` | string | "en" | Language preference (ISO 639-1 code) |

### Security & Status

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | enum | USER | User role (USER, ADMIN, SUPERADMIN) |
| `is_active` | boolean | true | Account active status |
| `two_fa_enabled` | boolean | false | 2FA enabled for this user |
| `email_verified` | boolean | false | Email verification status |

### Timestamps

| Field | Type | Description |
|-------|------|-------------|
| `last_login_at` | datetime | Last successful login |
| `created_at` | datetime | Account creation time |
| `updated_at` | datetime | Last profile update time |

## Managing Your Profile

### View Your Profile

**Endpoint:** `GET /api/v1/users/me`

**Authentication:** Required (any role)

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "avatar_url": "https://example.com/avatars/johndoe.jpg",
  "bio": "Software developer",
  "timezone": "America/New_York",
  "language": "en",
  "is_active": true,
  "role": "user",
  "two_fa_enabled": false,
  "email_verified": true,
  "phone_verified": false,
  "last_login_at": "2025-01-15T10:30:00Z",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-15T08:00:00Z"
}
```

### Update Your Profile

**Endpoint:** `PUT /api/v1/users/update/{user_id}`

**Authentication:** Required (self or admin)

**Updatable Fields:**
- `first_name`, `last_name`
- `phone_number`
- `avatar_url`
- `bio`
- `timezone`
- `language`
- `password` (provide new password)

**Example:**

```bash
curl -X PUT "http://localhost:8000/api/v1/users/update/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "bio": "Full-stack developer specializing in Python and FastAPI",
    "timezone": "America/Los_Angeles",
    "phone_number": "+1234567890",
    "avatar_url": "https://example.com/avatars/newphoto.jpg"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Smith",
  "bio": "Full-stack developer specializing in Python and FastAPI",
  ...
}
```

### Update Password

Include `password` field in update request:

```bash
curl -X PUT "http://localhost:8000/api/v1/users/update/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "newSecurePassword123"
  }'
```

Password is automatically hashed with bcrypt before storage.

## Two-Factor Authentication (2FA)

2FA adds an extra security layer by requiring a code sent to your email after password authentication.

### How It Works

1. User logs in with username/email and password
2. If 2FA is enabled, system sends 6-digit code to email
3. User submits code to complete login
4. System validates code and issues JWT tokens

### Enable 2FA

**Prerequisites:**
- Email must be verified (`email_verified: true`)
- Valid email address on account
- SMTP configured (see [EMAIL_SETUP.md](EMAIL_SETUP.md))

**Endpoint:** `POST /api/v1/auth/enable-2fa`

**Authentication:** Required

```bash
curl -X POST "http://localhost:8000/api/v1/auth/enable-2fa" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "message": "2FA has been enabled successfully",
  "two_fa_enabled": true
}
```

You'll receive a confirmation email.

### Disable 2FA

**Endpoint:** `POST /api/v1/auth/disable-2fa`

**Authentication:** Required

**Security:** Requires password confirmation

```bash
curl -X POST "http://localhost:8000/api/v1/auth/disable-2fa" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "your-current-password"
  }'
```

**Response:**
```json
{
  "message": "2FA has been disabled successfully",
  "two_fa_enabled": false
}
```

You'll receive a notification email.

### Login with 2FA

**Step 1: Initial Login**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "johndoe",
    "password": "securepass123"
  }'
```

**Response (2FA enabled):**
```json
{
  "message": "2FA code sent to your email",
  "requires_2fa": true,
  "user_id": 1
}
```

**Step 2: Check Email**

You'll receive an email with a 6-digit code:

```
Subject: Your 2FA Code

Hi johndoe,

Your verification code is: 123456

This code will expire in 10 minutes.
```

**Step 3: Verify 2FA Code**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-2fa" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "code": "123456"
  }'
```

**Response (success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Test 2FA

Test your email configuration without logging out:

**Endpoint:** `POST /api/v1/auth/test-2fa`

```bash
curl -X POST "http://localhost:8000/api/v1/auth/test-2fa" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "message": "Test 2FA code sent to your email",
  "email": "john@example.com"
}
```

Check your inbox for the test code.

### 2FA Code Expiration

- **Default TTL:** 10 minutes
- **Configurable:** Set `TWO_FA_CODE_EXPIRE_MINUTES` in `.env`
- **Storage:** Codes stored in Redis cache with automatic expiration

```env
TWO_FA_CODE_EXPIRE_MINUTES=10
```

### 2FA Security Best Practices

1. **Keep email secure** - 2FA is only as secure as your email account
2. **Enable email 2FA** - Protect your email with its own 2FA
3. **Don't share codes** - Never share your 2FA code with anyone
4. **Watch for suspicious emails** - Unexpected 2FA codes may indicate account compromise
5. **Secure password** - Use a strong, unique password

## Email Verification

Email verification confirms users own their email address.

### Current Status

Check your email verification status:

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Look for `email_verified` field in response.

### Implementation (Coming Soon)

Full email verification workflow:

1. User registers with email
2. Verification email sent with token
3. User clicks link or submits token
4. Email marked as verified

**Note:** Currently, superadmins created via `setup_first_superadmin.py` have `email_verified: true` by default. Regular registrations default to `false`.

## Phone Verification

Phone verification confirms users own their phone number.

### Current Status

Check phone verification:

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Look for `phone_verified` field in response.

### Future Implementation

Phone verification via SMS:

1. User adds phone number
2. SMS with verification code sent
3. User submits code
4. Phone marked as verified

**Note:** Phone verification is not yet implemented. The `phone_number` and `phone_verified` fields are available for future use.

## User Preferences

### Timezone

Set your timezone for accurate timestamps:

```bash
curl -X PUT "http://localhost:8000/api/v1/users/update/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "timezone": "America/New_York"
  }'
```

**Valid timezone values:** Use IANA timezone names
- `"UTC"` (default)
- `"America/New_York"`
- `"Europe/London"`
- `"Asia/Tokyo"`
- [Full list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### Language

Set your preferred language:

```bash
curl -X PUT "http://localhost:8000/api/v1/users/update/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "es"
  }'
```

**Valid language codes:** ISO 639-1 codes
- `"en"` - English (default)
- `"es"` - Spanish
- `"fr"` - French
- `"de"` - German
- [Full list](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)

**Note:** Language preference is stored but localization is not yet implemented in the template.

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login (initiates 2FA if enabled) | No |
| POST | `/api/v1/auth/verify-2fa` | Verify 2FA code | No |
| POST | `/api/v1/auth/enable-2fa` | Enable 2FA | Yes |
| POST | `/api/v1/auth/disable-2fa` | Disable 2FA | Yes |
| POST | `/api/v1/auth/test-2fa` | Send test 2FA email | Yes |

### User Management Endpoints

| Method | Endpoint | Description | Auth | Permission |
|--------|----------|-------------|------|------------|
| GET | `/api/v1/users/me` | Get own profile | Yes | Any |
| GET | `/api/v1/users/` | List all users | Yes | Admin |
| GET | `/api/v1/users/role/{role}` | List users by role | Yes | Admin |
| GET | `/api/v1/users/get/{user_id}` | Get user by ID | Yes | Self or Admin |
| PUT | `/api/v1/users/update/{user_id}` | Update user | Yes | Self or Admin |
| PUT | `/api/v1/users/update/{user_id}/role` | Change user role | Yes | Superadmin |
| DELETE | `/api/v1/users/delete/{user_id}` | Delete user | Yes | Admin |

### Request/Response Examples

**Registration:**

```json
// Request
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "Software developer",
  "timezone": "America/New_York",
  "language": "en"
}

// Response
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "bio": "Software developer",
  "timezone": "America/New_York",
  "language": "en",
  "role": "user",
  "is_active": true,
  "two_fa_enabled": false,
  "email_verified": false,
  "phone_verified": false,
  "last_login_at": null,
  "created_at": "2025-01-15T12:00:00Z",
  "updated_at": null
}
```

**Profile Update:**

```json
// Request
{
  "first_name": "Jonathan",
  "bio": "Senior Python developer",
  "avatar_url": "https://example.com/new-avatar.jpg"
}

// Response
{
  "id": 1,
  "username": "johndoe",
  "first_name": "Jonathan",  // Updated
  "bio": "Senior Python developer",  // Updated
  "avatar_url": "https://example.com/new-avatar.jpg",  // Updated
  ...
}
```

## Troubleshooting

### Can't enable 2FA

**Error:** "Please verify your email before enabling 2FA"

**Solution:**
1. Check `email_verified` status: `GET /api/v1/users/me`
2. If false, email verification not yet implemented
3. Workaround: Have admin manually set `email_verified = True`

### 2FA code not received

**Possible causes:**
1. Email in spam folder
2. SMTP not configured
3. Invalid email address

**Solutions:**
- Check spam/junk folder
- Test SMTP: `POST /api/v1/auth/test-2fa`
- Verify email address in profile
- Check [EMAIL_SETUP.md](EMAIL_SETUP.md)

### 2FA code expired

**Error:** "Invalid or expired 2FA code"

**Solution:**
- Request new code by logging in again
- Default expiration: 10 minutes
- Codes are single-use

### Can't update profile

**Error:** 403 Forbidden

**Solution:**
- Verify you're updating your own profile (`user_id` matches your ID)
- Or have admin/superadmin role
- Check token is valid and not expired

### Password update not working

**Possible causes:**
1. Password too short (minimum 8 characters)
2. Password too long (maximum 100 characters)

**Solution:**
```bash
# Ensure password meets requirements
curl -X PUT "/api/v1/users/update/1" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"password": "NewSecurePass123"}'  # 8-100 chars
```

---

**Related Documentation:**
- [Roles](ROLES.md) - Role-based access control and permissions
- [Email Setup](EMAIL_SETUP.md) - Configuring SMTP for 2FA and notifications
