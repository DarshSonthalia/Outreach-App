# Email Notifications Setup Guide

## Overview
Your SafeMail landing page is now configured to send **two types of emails** when someone joins the waitlist:

1. **Admin Notification** → Sent to **sonthaliadarsh@gmail.com** (you get immediate notification)
2. **User Confirmation** → Sent to the **signup user's email** (welcome message)

---

## Setup Steps

### Step 1: Get Your Resend API Key
1. Go to https://resend.com
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Create a new API key (or copy your existing one)
5. Copy the full API key

### Step 2: Add the API Key to Your Project
In the v0 UI, go to the **Vars** section in the sidebar and add:

```
RESEND_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with the key you copied from Resend.

### Step 3: Deploy
Once the environment variable is added, deploy your project to Vercel:
- Click the **Publish** button in the top right
- Your changes will be live in ~30 seconds

---

## How It Works

When someone submits the waitlist form:
1. Their data is saved to the JSON file
2. **Two emails are automatically sent in parallel:**

### Email 1: Admin Notification (to you)
Sent to **sonthaliadarsh@gmail.com** with:
- Their full name
- Email address
- Company name
- Role (Founder, Sales, Marketing, etc.)
- Monthly email volume
- Lead strategy preference (if provided)
- Signup timestamp
- Clear header: "New SafeMail Waitlist Signup!"
- All user information in an organized box

### Email 2: User Confirmation (to the signup user)
Sent to the **user's email address** with:
- Personalized welcome message
- Thank you for joining
- What to expect next
- Link to the product page
- Professional footer with SafeMail branding

---

## Testing (Before Going Live)

### Test Locally (Optional)
1. Set `RESEND_API_KEY` in your `.env.local` file
2. Run `npm run dev`
3. Submit the waitlist form
4. Check the console for `[v0] Notification email sent to...` confirmation
5. Check your email inbox for the test notification

### Test After Deployment
1. Ensure `RESEND_API_KEY` is set in your Vercel project (Vars section)
2. Submit the waitlist form on your deployed site
3. You should receive the notification email within 1-2 seconds

---

## Troubleshooting

### No email received?

**Check 1: API Key Missing**
- Go to Vars in v0 sidebar
- Verify `RESEND_API_KEY` is set
- If not set, add it and redeploy

**Check 2: Wrong Email Address**
- Ensure `sonthaliadarsh@gmail.com` is correct in the code
- Current setup sends to this exact address

**Check 3: Check Spam Folder**
- Resend emails sometimes go to spam
- Add `onboarding@resend.dev` to your contacts to whitelist

**Check 4: Monitor Console Logs**
- Go to your Vercel project dashboard
- Check the Function Logs for the `/api/waitlist` endpoint
- Look for `[v0]` log messages to see if email was sent

### API Key Invalid?
- If you see errors mentioning "unauthorized" or "invalid", your key may be wrong
- Go back to https://resend.com and regenerate a fresh API key
- Update it in Vars and redeploy

---

## Important Notes

- **Non-blocking**: If the emails fail to send for any reason, the user's signup will still be saved. This ensures your waitlist stays functional even if there are email service issues.
- **Lead Strategy Field**: The optional "How do you plan to get leads?" dropdown is now captured and included in admin notifications.
- **Two Emails Sent**: Both admin and user confirmation emails are sent simultaneously using Promise.all() for efficiency.
- **Email Verification**: Users won't be verified/confirmed at this stage—the confirmation email is just a welcome message. You can add double-opt-in verification later if needed.
- **First Email**: You might not receive your first test email if `RESEND_API_KEY` is not yet set. Once you add it, all future signups will trigger both emails.

---

## API Rate Limits

Resend free tier allows:
- 100 emails per day
- This should be plenty for a waitlist

For production with higher volume, consider upgrading your Resend plan.

---

## Customizing the Email

If you want to change:
- The email subject line
- The email content/formatting
- The "from" address

Edit `/app/api/waitlist/route.ts` and modify the `sendAdminNotification()` function.

---

## Need Help?

If you encounter issues:
1. Check the troubleshooting section above
2. Verify Resend API key is valid: https://resend.com/api-keys
3. Check Vercel function logs: https://vercel.com/docs/functions/edge-functions/observability
4. Contact Resend support: https://resend.com/support
