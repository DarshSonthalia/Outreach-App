import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'
import { Resend } from 'resend'

interface WaitlistEntry {
  id: string
  fullName: string
  workEmail: string
  companyName: string
  role: string
  monthlyVolume: string
  leadStrategy?: string
  createdAt: string
}

const WAITLIST_FILE = path.join(process.cwd(), 'data', 'waitlist.json')
const ADMIN_EMAIL = 'sonthaliadarsh@gmail.com'
const resendApiKey = process.env.RESEND_API_KEY
const resend = resendApiKey ? new Resend(resendApiKey) : null

async function sendAdminNotification(entry: WaitlistEntry) {
  try {
    if (!resend) {
      console.warn('[v0] RESEND_API_KEY not configured - skipping email notification')
      return
    }

    const leadStrategyText = entry.leadStrategy 
      ? `Lead Strategy: ${entry.leadStrategy.replace('-', ' ')}`
      : 'Lead Strategy: Not specified'

    const emailHtml = `
      <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #a78bfa;">New intently-ai Waitlist Signup!</h2>
        <div style="background: #f5f5f7; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <p><strong>Name:</strong> ${entry.fullName}</p>
          <p><strong>Email:</strong> ${entry.workEmail}</p>
          <p><strong>Company:</strong> ${entry.companyName}</p>
          <p><strong>Role:</strong> ${entry.role}</p>
          <p><strong>Monthly Volume:</strong> ${entry.monthlyVolume}</p>
          <p><strong>${leadStrategyText}</strong></p>
          <p><strong>Joined:</strong> ${new Date(entry.createdAt).toLocaleString()}</p>
        </div>
        <p style="color: #666; font-size: 12px;">This is an automated notification from intently-ai.</p>
      </div>
    `

    await resend.emails.send({
      from: 'intently-ai <onboarding@resend.dev>',
      to: ADMIN_EMAIL,
      subject: `New intently-ai Signup: ${entry.fullName}`,
      html: emailHtml,
    })

    console.log(`[v0] Notification email sent to ${ADMIN_EMAIL}`)
  } catch (error) {
    console.error('[v0] Failed to send admin notification:', error)
    // Don't throw - allow signup to complete even if email fails
  }
}

async function sendUserConfirmationEmail(entry: WaitlistEntry) {
  try {
    if (!resend) {
      console.warn('[v0] RESEND_API_KEY not configured - skipping user confirmation email')
      return
    }

    // Only send to verified email in testing mode to avoid Resend 403 errors
    // In production with domain verification, this will work for all users
    if (entry.workEmail !== ADMIN_EMAIL) {
      console.log(`[v0] Resend in testing mode - user confirmation email skipped for ${entry.workEmail}. Will be enabled after domain verification.`)
      return
    }

    const confirmationHtml = `
      <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #a78bfa;">Welcome to intently-ai!</h1>
        <p>Hi ${entry.fullName},</p>
        <p>Thank you for joining our waitlist. We're excited to have you on board.</p>
        <div style="background: #f5f5f7; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <h3 style="margin-top: 0;">What's Next?</h3>
          <ul>
            <li>We're carefully onboarding early users to ensure the best experience.</li>
            <li>You'll hear from us soon with your private beta access.</li>
            <li>In the meantime, check out our <a href="https://intently.ai" style="color: #a78bfa;">product page</a> to learn more.</li>
          </ul>
        </div>
        <p style="margin-top: 30px;">Stay intentional,<br><strong>The intently-ai Team</strong></p>
        <p style="color: #999; font-size: 12px; border-top: 1px solid #e0e0e0; padding-top: 20px; margin-top: 30px;">
          This is an automated email. Please don't reply to this address. If you have questions, reach out to us directly.
        </p>
      </div>
    `

    await resend.emails.send({
      from: 'intently-ai <onboarding@resend.dev>',
      to: entry.workEmail,
      subject: 'Welcome to intently-ai - You\'re on the Waitlist!',
      html: confirmationHtml,
    })

    console.log(`[v0] Confirmation email sent to ${entry.workEmail}`)
  } catch (error) {
    console.error('[v0] Failed to send user confirmation email:', error)
    // Don't throw - allow signup to complete even if email fails
  }
}

async function ensureWaitlistFile() {
  try {
    await fs.access(WAITLIST_FILE)
  } catch {
    const dir = path.dirname(WAITLIST_FILE)
    try {
      await fs.mkdir(dir, { recursive: true })
    } catch (err) {
      // Directory might already exist
    }
    await fs.writeFile(WAITLIST_FILE, JSON.stringify([], null, 2))
  }
}

async function readWaitlist(): Promise<WaitlistEntry[]> {
  await ensureWaitlistFile()
  const data = await fs.readFile(WAITLIST_FILE, 'utf-8')
  return JSON.parse(data)
}

async function writeWaitlist(entries: WaitlistEntry[]): Promise<void> {
  await ensureWaitlistFile()
  await fs.writeFile(WAITLIST_FILE, JSON.stringify(entries, null, 2))
}

function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // Validate required fields
    const { fullName, workEmail, companyName, role, monthlyVolume, leadStrategy } = body

    if (!fullName || !workEmail || !companyName || !role || !monthlyVolume) {
      return NextResponse.json(
        { error: 'All fields are required' },
        { status: 400 }
      )
    }

    // Validate email format
    if (!validateEmail(workEmail)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      )
    }

    // Sanitize inputs
    const sanitizedData = {
      fullName: String(fullName).trim(),
      workEmail: String(workEmail).trim().toLowerCase(),
      companyName: String(companyName).trim(),
      role: String(role).trim(),
      monthlyVolume: String(monthlyVolume).trim(),
      leadStrategy: leadStrategy ? String(leadStrategy).trim() : undefined,
    }

    // Read existing waitlist
    const waitlist = await readWaitlist()

    // Check if email already exists
    const exists = waitlist.some(
      (entry) => entry.workEmail === sanitizedData.workEmail
    )

    if (exists) {
      return NextResponse.json(
        { error: 'This email is already on the waitlist' },
        { status: 409 }
      )
    }

    // Create new entry
    const newEntry: WaitlistEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      ...sanitizedData,
      createdAt: new Date().toISOString(),
    }

    // Add to waitlist
    waitlist.push(newEntry)

    // Save to file
    await writeWaitlist(waitlist)

    // Send notification emails (non-blocking)
    await Promise.all([
      sendAdminNotification(newEntry),
      sendUserConfirmationEmail(newEntry),
    ])

    // Return success response
    return NextResponse.json(
      {
        success: true,
        message: 'You have been added to the waitlist',
        id: newEntry.id,
      },
      { status: 201 }
    )
  } catch (error) {
    console.error('Waitlist API error:', error)

    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    )
  }
}

// Optional: GET endpoint to retrieve waitlist count (for demo purposes)
export async function GET(request: NextRequest) {
  try {
    const waitlist = await readWaitlist()

    return NextResponse.json({
      count: waitlist.length,
      message: `${waitlist.length} people on the waitlist`,
    })
  } catch (error) {
    console.error('Waitlist GET error:', error)

    return NextResponse.json(
      { error: 'Failed to retrieve data' },
      { status: 500 }
    )
  }
}
