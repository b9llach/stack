# Email and SMTP Configuration Guide

This guide covers setting up email functionality for the FastAPI template, including SMTP configuration for various providers and testing.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [SMTP Providers](#smtp-providers)
- [Environment Configuration](#environment-configuration)
- [Testing Email](#testing-email)
- [Email Features](#email-features)
- [Troubleshooting](#troubleshooting)

## Overview

The template uses **aiosmtplib** for async email sending with support for:
- Two-Factor Authentication (2FA) codes
- Welcome emails
- Password reset emails
- Account notifications
- Custom email templates (HTML + plaintext)

Email is **optional** but **required for 2FA functionality**.

## Quick Start

### 1. Choose an SMTP Provider

Pick a provider based on your needs:
- **Gmail** - Free, easy setup, good for development
- **Outlook/Office 365** - Free, Microsoft accounts
- **SendGrid** - Free tier (100 emails/day), production-ready
- **AWS SES** - Pay-as-you-go, highly scalable
- **Mailgun** - Free tier, developer-friendly

### 2. Get SMTP Credentials

Follow provider-specific instructions below to obtain:
- SMTP host
- SMTP port
- Username
- Password/API key

### 3. Configure .env File

Add credentials to your `.env` file:

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@yourdomain.com
EMAILS_FROM_NAME=FastAPI Template
```

### 4. Test Configuration

```bash
# Login to get a token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username_or_email": "youruser", "password": "yourpass"}'

# Test email sending
curl -X POST "http://localhost:8000/api/v1/auth/test-2fa" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## SMTP Providers

### Gmail

**Best for:** Development, personal projects, low-volume sending

**Setup Steps:**

1. **Enable 2-Step Verification:**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable "2-Step Verification"

2. **Generate App Password:**
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Configure .env:**
```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAILS_FROM_EMAIL=your-email@gmail.com
EMAILS_FROM_NAME=My App
```

**Limits:**
- 500 emails/day (free accounts)
- 2,000 emails/day (Google Workspace)

**Notes:**
- Must use App Password (not regular password)
- "Less secure app access" is deprecated

---

### Outlook / Office 365

**Best for:** Microsoft users, business accounts

**Setup Steps:**

1. **Use your Microsoft account credentials**
2. **Configure .env:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp-mail.outlook.com
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-outlook-password
EMAILS_FROM_EMAIL=your-email@outlook.com
EMAILS_FROM_NAME=My App
```

**For Office 365 Business:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.office365.com
SMTP_USER=your-email@yourdomain.com
SMTP_PASSWORD=your-password
EMAILS_FROM_EMAIL=your-email@yourdomain.com
EMAILS_FROM_NAME=My Company
```

**Limits:**
- 300 emails/day (Outlook.com)
- 10,000 emails/day (Office 365)

**Notes:**
- May require app password if 2FA is enabled
- Check [Microsoft security settings](https://account.microsoft.com/security)

---

### SendGrid

**Best for:** Production, scalable applications, detailed analytics

**Setup Steps:**

1. **Sign up:** [SendGrid](https://signup.sendgrid.com/)

2. **Create API Key:**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Choose "Full Access" or "Restricted Access"
   - Copy the API key (shown once!)

3. **Verify Sender Identity:**
   - Go to Settings → Sender Authentication
   - Verify a single sender or entire domain

4. **Configure .env:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.sendgrid.net
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-actual-api-key-here
EMAILS_FROM_EMAIL=verified@yourdomain.com
EMAILS_FROM_NAME=My App
```

**Important:** Username is literally the string `apikey`, password is your API key.

**Limits:**
- Free tier: 100 emails/day forever
- Paid: Starting at $15/month for 40,000 emails

**Benefits:**
- Detailed analytics and tracking
- Email validation API
- Template management
- Webhooks for events

---

### AWS SES (Simple Email Service)

**Best for:** High-volume sending, AWS infrastructure

**Setup Steps:**

1. **Sign up:** [AWS Console](https://aws.amazon.com/ses/)

2. **Verify Email/Domain:**
   - Go to SES Console → Verified Identities
   - Verify email or domain
   - Check DNS records for domain verification

3. **Request Production Access:**
   - By default, SES is in "sandbox mode"
   - Request production access to send to any email

4. **Create SMTP Credentials:**
   - Go to SMTP Settings
   - Create SMTP credentials
   - Save username and password

5. **Configure .env:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_USER=your-smtp-username
SMTP_PASSWORD=your-smtp-password
EMAILS_FROM_EMAIL=verified@yourdomain.com
EMAILS_FROM_NAME=My App
```

**Region-specific hosts:**
- US East (N. Virginia): `email-smtp.us-east-1.amazonaws.com`
- US West (Oregon): `email-smtp.us-west-2.amazonaws.com`
- EU (Ireland): `email-smtp.eu-west-1.amazonaws.com`
- [Full list](https://docs.aws.amazon.com/ses/latest/dg/regions.html)

**Limits:**
- Sandbox: 200 emails/day
- Production: 50,000 emails/day (request higher)

**Pricing:**
- $0.10 per 1,000 emails
- Free tier: 62,000 emails/month (if sending from EC2)

---

### Mailgun

**Best for:** Developers, detailed logs, email validation

**Setup Steps:**

1. **Sign up:** [Mailgun](https://signup.mailgun.com/)

2. **Verify Domain** (or use sandbox domain for testing)

3. **Get SMTP Credentials:**
   - Go to Sending → Domain Settings
   - Find SMTP credentials section

4. **Configure .env:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.mailgun.org
SMTP_USER=postmaster@yourdomain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
EMAILS_FROM_EMAIL=noreply@yourdomain.com
EMAILS_FROM_NAME=My App
```

**Limits:**
- Free trial: 5,000 emails/month for 3 months
- Paid: Starting at $35/month for 50,000 emails

**Benefits:**
- Powerful API
- Email validation
- Detailed logs
- Webhooks

---

### Mailtrap (Development/Testing)

**Best for:** Testing emails without sending to real users

**Setup Steps:**

1. **Sign up:** [Mailtrap](https://mailtrap.io/)

2. **Get Credentials:**
   - Go to Email Testing → Inboxes
   - Copy SMTP credentials

3. **Configure .env:**

```env
SMTP_TLS=True
SMTP_PORT=587
SMTP_HOST=smtp.mailtrap.io
SMTP_USER=your-mailtrap-username
SMTP_PASSWORD=your-mailtrap-password
EMAILS_FROM_EMAIL=test@example.com
EMAILS_FROM_NAME=Test App
```

**Benefits:**
- Catches all outgoing emails
- View HTML rendering
- Check spam score
- Perfect for development

**Limits:**
- Free tier: 500 emails/month
- Emails never sent to real recipients

---

## Environment Configuration

Complete `.env` email configuration:

```env
# Email / SMTP Configuration
SMTP_TLS=True                              # Use TLS encryption (recommended)
SMTP_PORT=587                              # Standard TLS port
SMTP_HOST=smtp.gmail.com                   # SMTP server hostname
SMTP_USER=your-email@gmail.com             # SMTP username
SMTP_PASSWORD=your-app-password            # SMTP password or API key
EMAILS_FROM_EMAIL=noreply@yourdomain.com   # "From" email address
EMAILS_FROM_NAME=FastAPI Template          # "From" name

# 2FA Settings
TWO_FA_CODE_EXPIRE_MINUTES=10              # 2FA code validity (minutes)
```

### Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SMTP_HOST` | SMTP server hostname | smtp.gmail.com | Yes |
| `SMTP_PORT` | SMTP server port | 587 | Yes |
| `SMTP_TLS` | Use TLS encryption | True | Yes |
| `SMTP_USER` | SMTP username | - | Yes |
| `SMTP_PASSWORD` | SMTP password/API key | - | Yes |
| `EMAILS_FROM_EMAIL` | Sender email address | noreply@yourdomain.com | Yes |
| `EMAILS_FROM_NAME` | Sender display name | FastAPI Template | Yes |
| `TWO_FA_CODE_EXPIRE_MINUTES` | 2FA code TTL | 10 | No |

## Testing Email

### Using the API

**1. Get an authentication token:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "youruser",
    "password": "yourpassword"
  }'
```

**2. Test email sending:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/test-2fa" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**3. Check response:**

```json
{
  "message": "Test 2FA code sent to your email",
  "email": "user@example.com"
}
```

### Using Swagger UI

1. Navigate to `http://localhost:8000/api/docs`
2. Click "Authorize" and enter your token
3. Find `/api/v1/auth/test-2fa` endpoint
4. Click "Try it out" → "Execute"
5. Check your email inbox

### Checking Logs

Enable debug logging to see email details:

```python
# In app/utils/logger.py or temporarily in email_service.py
import logging

logging.basicConfig(level=logging.DEBUG)
```

## Email Features

### 2FA Email

**Sent when:** User with 2FA enabled logs in

**Template:** 6-digit verification code

**Example:**
```
Subject: Your 2FA Code

Hi username,

Your verification code is: 123456

This code will expire in 10 minutes.

If you didn't request this code, please secure your account immediately.
```

### Welcome Email

**Implementation:** Add to `app/services/email_service.py`

```python
async def send_welcome_email(self, to: str, username: str) -> bool:
    subject = f"Welcome to {settings.PROJECT_NAME}!"
    body = f"Hi {username},\n\nWelcome to our platform! Your account has been created successfully."
    html = f"<h2>Welcome {username}!</h2><p>Your account has been created successfully.</p>"

    return await self.send_email(to=[to], subject=subject, body=body, html=html)
```

### Password Reset Email

**Implementation:**

```python
async def send_password_reset_email(self, to: str, reset_token: str) -> bool:
    subject = "Password Reset Request"
    reset_url = f"https://yourapp.com/reset-password?token={reset_token}"
    body = f"Click this link to reset your password: {reset_url}"
    html = f"""
        <h2>Password Reset</h2>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_url}" style="padding: 10px 20px; background: blue; color: white;">
            Reset Password
        </a>
    """

    return await self.send_email(to=[to], subject=subject, body=body, html=html)
```

## Troubleshooting

### Error: "SMTP connection failed"

**Possible causes:**
1. Wrong SMTP host or port
2. Firewall blocking port 587
3. Invalid credentials

**Solutions:**
```bash
# Test SMTP connection
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"

# Check firewall
telnet smtp.gmail.com 587
```

### Error: "Authentication failed"

**Possible causes:**
1. Wrong username/password
2. Need app password (Gmail, Outlook)
3. 2FA not configured

**Solutions:**
- Gmail: Generate App Password
- Outlook: Check account security settings
- SendGrid: Verify API key is correct

### Error: "Sender address rejected"

**Possible causes:**
1. Email not verified with provider
2. Using wrong "from" address

**Solutions:**
- Verify sender email with your provider
- Use verified domain for `EMAILS_FROM_EMAIL`

### Emails going to spam

**Solutions:**
1. Set up SPF, DKIM, DMARC records
2. Use reputable SMTP provider
3. Avoid spam trigger words
4. Include unsubscribe link

### Rate limiting errors

**Possible causes:**
1. Exceeded provider's sending limits
2. Too many emails too quickly

**Solutions:**
- Check provider's rate limits
- Implement email queue
- Upgrade to higher tier

### SSL/TLS errors

**Solutions:**
```env
# Try without TLS (port 25 or 465)
SMTP_TLS=False
SMTP_PORT=25

# Or use SSL (port 465)
SMTP_TLS=True
SMTP_PORT=465
```

## Best Practices

### 1. Use Environment Variables

Never hardcode credentials:

```python
# Good
smtp_user = settings.SMTP_USER

# Bad
smtp_user = "myemail@gmail.com"  # Never do this
```

### 2. Handle Failures Gracefully

```python
try:
    await email_service.send_2fa_email(user.email, username, code)
except Exception as e:
    logger.error(f"Failed to send email: {e}")
    # Don't block user registration/login
    # Queue for retry or notify admin
```

### 3. Use HTML + Plaintext

Always provide both formats:

```python
await email_service.send_email(
    to=[user.email],
    subject="Welcome!",
    body="Plain text version",  # Fallback for email clients that don't support HTML
    html="<h1>HTML version</h1>"  # Better presentation
)
```

### 4. Test in Development

Use Mailtrap or similar service during development to avoid:
- Sending test emails to real users
- Hitting rate limits
- Wasting email quota

### 5. Monitor Email Delivery

- Check bounce rates
- Monitor spam reports
- Track delivery rates
- Set up webhooks for events

---

**Related Documentation:**
- [User Settings](USER_SETTINGS.md) - 2FA and email verification
- [Roles](ROLES.md) - Role-based access control
