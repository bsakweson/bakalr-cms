#!/bin/bash
# Seed email templates for device verification and login alerts
# These use the CMS content model with auto-translation support

set -e

CMS_API_URL="${CMS_API_URL:-http://localhost:8000/api/v1}"
API_KEY="${CMS_API_KEY:-}"

if [ -z "$API_KEY" ]; then
    echo "❌ CMS_API_KEY environment variable is required"
    exit 1
fi

AUTH_HEADER="X-API-Key: $API_KEY"

echo "🔍 Finding email_template content type..."
CONTENT_TYPE_ID=$(curl -s "${CMS_API_URL}/content/types" \
  -H "$AUTH_HEADER" | jq -r '.[] | select(.api_id == "email_template") | .id')

if [ -z "$CONTENT_TYPE_ID" ] || [ "$CONTENT_TYPE_ID" == "null" ]; then
    echo "❌ email_template content type not found. Please create it first."
    exit 1
fi

echo "✅ Found email_template content type: $CONTENT_TYPE_ID"

# Device Verification Email Template
echo ""
echo "📧 Creating device_verification template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "Device Verification",
    "slug": "device-verification",
    "status": "published",
    "data": {
      "template_key": "device_verification",
      "subject": "Verify Your Device - {{verification_code}}",
      "heading": "Verify Your Device",
      "body": "<p>Hi {{user_name}},</p><p>We detected a login from a new device: <strong>{{device_name}}</strong></p><p>To verify this device, please enter the following code:</p><p style=\"font-size: 32px; font-weight: bold; letter-spacing: 8px; text-align: center; padding: 20px; background: #f5f5f5; border-radius: 8px;\">{{verification_code}}</p><p>This code expires in <strong>{{expires_minutes}} minutes</strong>.</p><p>If you did not attempt to log in, please secure your account immediately.</p>",
      "footer_text": "This is an automated security message. Do not share this code with anyone."
    }
  }' | jq .

# New Login Alert Email Template
echo ""
echo "📧 Creating new_login_alert template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "New Login Alert",
    "slug": "new-login-alert",
    "status": "published",
    "data": {
      "template_key": "new_login_alert",
      "subject": "New Login to Your Account",
      "heading": "New Login Detected",
      "body": "<p>Hi {{user_name}},</p><p>We noticed a new login to your account:</p><table style=\"width: 100%; border-collapse: collapse; margin: 20px 0;\"><tr><td style=\"padding: 10px; border-bottom: 1px solid #eee;\"><strong>Device:</strong></td><td style=\"padding: 10px; border-bottom: 1px solid #eee;\">{{device_info}}</td></tr><tr><td style=\"padding: 10px; border-bottom: 1px solid #eee;\"><strong>Location:</strong></td><td style=\"padding: 10px; border-bottom: 1px solid #eee;\">{{location}}</td></tr><tr><td style=\"padding: 10px; border-bottom: 1px solid #eee;\"><strong>IP Address:</strong></td><td style=\"padding: 10px; border-bottom: 1px solid #eee;\">{{ip_address}}</td></tr><tr><td style=\"padding: 10px;\"><strong>Time:</strong></td><td style=\"padding: 10px;\">{{login_time}}</td></tr></table><p>If this was you, you can ignore this email.</p><p><strong>If you did not log in</strong>, please secure your account immediately by changing your password.</p>",
      "cta_text": "Secure My Account",
      "cta_url": "{{security_url}}",
      "footer_text": "This is an automated security alert from your account."
    }
  }' | jq .

# Password Reset Email Template
echo ""
echo "📧 Creating password_reset template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "Password Reset",
    "slug": "password-reset",
    "status": "published",
    "data": {
      "template_key": "password_reset",
      "subject": "Reset Your Password",
      "heading": "Reset Your Password",
      "body": "<p>Hi {{user_name}},</p><p>We received a request to reset your password. Click the button below to create a new password:</p>",
      "cta_text": "Reset Password",
      "cta_url": "{{reset_url}}",
      "footer_text": "This link expires in {{expiry_hours}} hours. If you did not request a password reset, you can safely ignore this email."
    }
  }' | jq .

# Welcome Email Template
echo ""
echo "📧 Creating welcome template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "Welcome",
    "slug": "welcome",
    "status": "published",
    "data": {
      "template_key": "welcome",
      "subject": "Welcome to {{organization_name}}",
      "heading": "Welcome to {{organization_name}}!",
      "body": "<p>Hi {{user_name}},</p><p>Thank you for joining <strong>{{organization_name}}</strong>! We'\''re excited to have you on board.</p><p>Your account has been created successfully. You can now log in and start exploring.</p>",
      "cta_text": "Go to Dashboard",
      "cta_url": "{{dashboard_url}}",
      "footer_text": "Need help getting started? Check out our documentation or contact support."
    }
  }' | jq .

# Email Verification Template
echo ""
echo "📧 Creating verify_email template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "Email Verification",
    "slug": "email-verification",
    "status": "published",
    "data": {
      "template_key": "verify_email",
      "subject": "Verify Your Email - {{organization_name}}",
      "heading": "Verify Your Email Address",
      "body": "<p>Hi {{user_name}},</p><p>Please verify your email address to complete your registration with <strong>{{organization_name}}</strong>.</p><p>Click the button below to verify your email:</p>",
      "cta_text": "Verify Email",
      "cta_url": "{{verification_url}}",
      "footer_text": "This link expires in {{expiry_hours}} hours. If you did not create an account, you can safely ignore this email."
    }
  }' | jq .

# User Invitation Email Template
echo ""
echo "📧 Creating user_invitation template..."
curl -s -X POST "${CMS_API_URL}/content/entries" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": "'"$CONTENT_TYPE_ID"'",
    "title": "User Invitation",
    "slug": "user-invitation",
    "status": "published",
    "data": {
      "template_key": "user_invitation",
      "subject": "You'\''ve been invited to join {{organization_name}}",
      "heading": "You'\''re Invited!",
      "body": "<p>Hi {{user_name}},</p><p><strong>{{inviter_name}}</strong> has invited you to join <strong>{{organization_name}}</strong> as a <strong>{{role_name}}</strong>.</p><p>Click the button below to accept the invitation and set up your account:</p>",
      "cta_text": "Accept Invitation",
      "cta_url": "{{invite_url}}",
      "footer_text": "This invitation expires in {{expiry_hours}} hours. If you did not expect this invitation, you can safely ignore this email."
    }
  }' | jq .

echo ""
echo "✅ All email templates created successfully!"
echo ""
echo "📝 Templates created:"
echo "   - device_verification"
echo "   - new_login_alert"
echo "   - password_reset"
echo "   - welcome"
echo "   - verify_email"
echo "   - user_invitation"
echo ""
echo "💡 To enable translations, add translations for each template in the CMS admin."
