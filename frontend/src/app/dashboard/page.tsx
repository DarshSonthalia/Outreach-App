'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, workspaces, campaigns, mailboxes } from '@/lib/api';

interface Campaign {
    id: number;
    name: string;
    status: string;
    pause_reason?: string;
    launched_at?: string;
}

interface CampaignDashboard {
    campaign_id: number;
    name: string;
    status: string;
    pause_reason?: string;
    emails_sent_today: number;
    total_emails_sent: number;
    replies_count: number;
    meetings_booked: number;
    daily_limit: number;
    remaining_today: number;
}

export default function DashboardPage() {
    const router = useRouter();
    const [token, setToken] = useState<string | null>(null);
    const [workspaceId, setWorkspaceId] = useState<number | null>(null);
    const [activeCampaigns, setActiveCampaigns] = useState<CampaignDashboard[]>([]);
    const [allCampaigns, setAllCampaigns] = useState<Campaign[]>([]);
    const [connectedMailboxes, setConnectedMailboxes] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [userName, setUserName] = useState('');
    const [relinkingMailboxId, setRelinkingMailboxId] = useState<number | null>(null);
    const [disconnectingMailboxId, setDisconnectingMailboxId] = useState<number | null>(null);

    useEffect(() => {
        const init = async () => {
            console.log('DEBUG: Dashboard init started');
            const storedToken = localStorage.getItem('token');
            if (!storedToken) {
                console.log('DEBUG: No token found, redirecting');
                router.push('/');
                return;
            }
            setToken(storedToken);

            try {
                // Get user info
                console.log('DEBUG: Fetching user info...');
                const user = await auth.getMe(storedToken);
                setUserName(user.email);

                // Get workspace
                console.log('DEBUG: Fetching workspaces...');
                const userWorkspaces = await workspaces.list(storedToken);
                if (userWorkspaces.length === 0) {
                    router.push('/wizard');
                    return;
                }
                const wsId = userWorkspaces[0].id;
                console.log('DEBUG: Using workspace ID:', wsId);
                setWorkspaceId(wsId);

                // Fetch everything in parallel
                console.log('DEBUG: Fetching bulk data...');
                const [mboxes, campaignList] = await Promise.all([
                    mailboxes.list(storedToken, wsId),
                    campaigns.list(storedToken, wsId)
                ]);

                console.log('DEBUG: Mailboxes loaded:', mboxes.length);
                console.log('DEBUG: Campaigns loaded:', campaignList.length);

                setConnectedMailboxes(mboxes);
                setAllCampaigns(campaignList);

                // Normalize status check
                const getStatus = (c: any) => {
                    if (!c.status) return '';
                    return (typeof c.status === 'string' ? c.status : (c.status.value || '')).toUpperCase();
                };

                const running = campaignList.filter((c: any) => {
                    const s = getStatus(c);
                    return ['RUNNING', 'THROTTLED', 'PAUSED'].includes(s);
                });

                console.log('DEBUG: Running campaigns to fetch dashboards for:', running.length);

                if (running.length > 0) {
                    const dashResults = await Promise.allSettled(
                        running.map(c => campaigns.dashboard(storedToken, c.id))
                    );

                    const successfulDashes = dashResults
                        .filter((r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled')
                        .map(r => r.value);

                    console.log('DEBUG: Successful dashboards loaded:', successfulDashes.length);
                    setActiveCampaigns(successfulDashes);
                }

            } catch (err: any) {
                console.error('DEBUG: Error in dashboard init:', err);
            }
            setLoading(false);
            console.log('DEBUG: Dashboard init finished, loading=false');
        };

        init();
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        router.push('/');
    };

    const handleRelinkMailbox = async (mailboxId: number) => {
        if (!token || !workspaceId) {
            alert('Session expired. Please reload the page.');
            return;
        }

        try {
            setRelinkingMailboxId(mailboxId);
            console.log('DEBUG: Getting OAuth URL for workspace:', workspaceId);
            const resp = await mailboxes.getOAuthUrl(token, workspaceId);

            if (!resp.auth_url) {
                throw new Error('Failed to get authorization URL');
            }

            console.log('DEBUG: Redirecting to Google for re-authentication');
            window.location.href = resp.auth_url;
        } catch (err: any) {
            alert(`Failed to re-authenticate: ${err.message}`);
            setRelinkingMailboxId(null);
        }
    };

    const handleDisconnectMailbox = async (mailboxId: number, email: string) => {
        if (!confirm(`Are you sure you want to disconnect ${email}?\n\nAny campaigns using this mailbox will be paused.`)) {
            return;
        }

        try {
            setDisconnectingMailboxId(mailboxId);
            console.log('DEBUG: Disconnecting mailbox:', mailboxId);
            await mailboxes.disconnect(token!, mailboxId);

            // Refresh mailbox list
            const updatedMailboxes = await mailboxes.list(token!, workspaceId!);
            setConnectedMailboxes(updatedMailboxes);

            console.log('DEBUG: Mailbox disconnected successfully');
        } catch (err: any) {
            alert(`Failed to disconnect mailbox: ${err.message}`);
        } finally {
            setDisconnectingMailboxId(null);
        }
    };

    const handleAddMailbox = async () => {
        if (!token || !workspaceId) {
            alert('Session expired. Please reload the page.');
            return;
        }

        try {
            console.log('DEBUG: Getting OAuth URL for new mailbox, workspace:', workspaceId);
            const resp = await mailboxes.getOAuthUrl(token, workspaceId);

            if (!resp.auth_url) {
                throw new Error('Failed to get authorization URL');
            }

            console.log('DEBUG: Redirecting to Google to add new mailbox');
            window.location.href = resp.auth_url;
        } catch (err: any) {
            alert(`Failed to add mailbox: ${err.message}`);
        }
    };

    const handleTerminate = async (id: number) => {
        if (!confirm('Are you sure you want to terminate this campaign? All pending sends will be cancelled.')) return;

        try {
            await campaigns.terminate(token!, id);
            // Refresh
            const campaignList = await campaigns.list(token!, workspaceId!);
            setAllCampaigns(campaignList);
            const dashboards = await Promise.all(
                campaignList
                    .filter((c: Campaign) => c.status && ['RUNNING', 'THROTTLED', 'PAUSED'].includes(c.status.toUpperCase()))
                    .map(async (c: Campaign) => {
                        try {
                            return await campaigns.dashboard(token!, c.id);
                        } catch (e) {
                            return null;
                        }
                    })
            ).then(results => results.filter(d => d !== null));
            setActiveCampaigns(dashboards);
        } catch (err) {
            alert('Failed to terminate campaign');
            console.error(err);
        }
    };

    if (loading) {
        return (
            <div style={{
                height: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}>
                <div className="animate-pulse">Loading dashboard...</div>
            </div>
        );
    }

    const totalSentToday = activeCampaigns.reduce((sum: number, c: CampaignDashboard) => sum + c.emails_sent_today, 0);
    const totalReplies = activeCampaigns.reduce((sum: number, c: CampaignDashboard) => sum + (c.replies_count || 0), 0);
    const totalMeetings = activeCampaigns.reduce((sum: number, c: CampaignDashboard) => sum + (c.meetings_booked || 0), 0);

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
            {/* Header */}
            <header style={{
                borderBottom: '1px solid var(--border-color)',
                padding: '16px 24px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '10px',
                        background: 'var(--gradient-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}>
                        📧
                    </div>
                    <h1 style={{ fontSize: '18px', fontWeight: '600' }}>Email Outreach</h1>
                </div>

                <nav style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                    <Link href="/dashboard" style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
                        Dashboard
                    </Link>
                    <Link href="/inbox" style={{ color: 'var(--text-secondary)' }}>
                        Inbox
                    </Link>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        paddingLeft: '16px',
                        borderLeft: '1px solid var(--border-color)',
                    }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{userName}</span>
                        <button
                            onClick={handleLogout}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--text-muted)',
                                cursor: 'pointer',
                            }}
                        >
                            Logout
                        </button>
                    </div>
                </nav>
            </header>

            {/* Main Content */}
            <main className="container" style={{ padding: '32px 24px' }}>
                {/* Stats Overview */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '16px',
                    marginBottom: '32px',
                }}>
                    <div className="stat-card">
                        <div className="stat-value">{totalSentToday}</div>
                        <div className="stat-label">Emails Sent Today</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{totalReplies}</div>
                        <div className="stat-label">Total Replies</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{totalMeetings}</div>
                        <div className="stat-label">Meetings Booked</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{allCampaigns.filter((c: Campaign) => c.status && c.status.toUpperCase() === 'RUNNING').length}</div>
                        <div className="stat-label">Active Campaigns</div>
                    </div>
                </div>

                {/* Active Campaigns */}
                <div style={{ marginBottom: '32px' }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '16px',
                    }}>
                        <h2 style={{ fontSize: '18px', fontWeight: '600' }}>Active Campaigns</h2>
                        <Link href="/campaigns/new">
                            <button className="btn btn-primary">+ New Campaign</button>
                        </Link>
                    </div>

                    {activeCampaigns.length === 0 ? (
                        <div className="card" style={{ textAlign: 'center', padding: '48px' }}>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                No active campaigns yet
                            </p>
                            <Link href="/campaigns/new">
                                <button className="btn btn-primary">Create Your First Campaign</button>
                            </Link>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {activeCampaigns.map((campaign: CampaignDashboard) => (
                                <div key={campaign.campaign_id} className="card">
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'flex-start',
                                    }}>
                                        <div>
                                            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px' }}>
                                                {campaign.name}
                                            </h3>
                                            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                                                <span className={`badge badge-${campaign.status.toUpperCase() === 'RUNNING' ? 'success' :
                                                    campaign.status.toUpperCase() === 'PAUSED' ? 'danger' :
                                                        'warning'
                                                    }`}>
                                                    {campaign.status}
                                                </span>
                                                {campaign.pause_reason && (
                                                    <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                                                        {campaign.pause_reason}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent-primary)' }}>
                                                    {campaign.emails_sent_today}/{campaign.daily_limit}
                                                </div>
                                                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                                    sent today
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleTerminate(campaign.campaign_id)}
                                                style={{
                                                    background: 'rgba(255, 71, 87, 0.1)',
                                                    border: '1px solid rgba(255, 71, 87, 0.2)',
                                                    color: '#ff4757',
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    fontSize: '12px',
                                                    fontWeight: '600',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                Terminate
                                            </button>
                                            <Link href={`/campaigns/${campaign.campaign_id}/schedule`}>
                                                <button
                                                    style={{
                                                        background: 'rgba(33, 150, 243, 0.1)',
                                                        border: '1px solid rgba(33, 150, 243, 0.2)',
                                                        color: '#2196f3',
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        fontWeight: '600',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    View Schedule
                                                </button>
                                            </Link>
                                        </div>
                                    </div>

                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(3, 1fr)',
                                        gap: '16px',
                                        marginTop: '16px',
                                        paddingTop: '16px',
                                        borderTop: '1px solid var(--border-color)',
                                    }}>
                                        <div>
                                            <div style={{ fontSize: '20px', fontWeight: '600' }}>{campaign.total_emails_sent}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Total Sent</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '20px', fontWeight: '600' }}>{campaign.replies_count}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Replies</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '20px', fontWeight: '600' }}>{campaign.meetings_booked}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Meetings</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Connected Mailboxes */}
                <div>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '16px',
                    }}>
                        <h2 style={{ fontSize: '18px', fontWeight: '600' }}>
                            Connected Mailboxes
                        </h2>
                        <button
                            onClick={handleAddMailbox}
                            className="btn btn-primary"
                            style={{ fontSize: '14px' }}
                        >
                            + Add Mailbox
                        </button>
                    </div>

                    {connectedMailboxes.length === 0 ? (
                        <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                No mailboxes connected
                            </p>
                            <button
                                onClick={handleAddMailbox}
                                className="btn btn-secondary"
                            >
                                Connect Gmail
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {connectedMailboxes.map((mailbox: any) => (
                                <div key={mailbox.id} className="card" style={{ padding: '16px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        <div style={{
                                            width: '40px',
                                            height: '40px',
                                            borderRadius: '50%',
                                            background: 'var(--bg-tertiary)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                        }}>
                                            📬
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: '500' }}>{mailbox.email}</div>
                                            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                                                Connected {new Date(mailbox.connected_at).toLocaleDateString()}
                                            </div>
                                        </div>
                                        <span className={`badge badge-${mailbox.is_active ? 'success' : 'danger'}`}>
                                            {mailbox.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            {!mailbox.is_active && (
                                                <button
                                                    onClick={() => handleRelinkMailbox(mailbox.id)}
                                                    disabled={relinkingMailboxId === mailbox.id}
                                                    style={{
                                                        background: 'rgba(33, 150, 243, 0.1)',
                                                        border: '1px solid rgba(33, 150, 243, 0.2)',
                                                        color: '#2196f3',
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        fontWeight: '600',
                                                        cursor: relinkingMailboxId === mailbox.id ? 'not-allowed' : 'pointer',
                                                        opacity: relinkingMailboxId === mailbox.id ? 0.6 : 1,
                                                    }}
                                                >
                                                    {relinkingMailboxId === mailbox.id ? '🔄 Redirecting...' : '🔄 Re-link'}
                                                </button>
                                            )}
                                            <button
                                                onClick={() => handleDisconnectMailbox(mailbox.id, mailbox.email)}
                                                disabled={disconnectingMailboxId === mailbox.id}
                                                style={{
                                                    background: 'rgba(255, 71, 87, 0.1)',
                                                    border: '1px solid rgba(255, 71, 87, 0.2)',
                                                    color: '#ff4757',
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    fontSize: '12px',
                                                    fontWeight: '600',
                                                    cursor: disconnectingMailboxId === mailbox.id ? 'not-allowed' : 'pointer',
                                                    opacity: disconnectingMailboxId === mailbox.id ? 0.6 : 1,
                                                }}
                                            >
                                                {disconnectingMailboxId === mailbox.id ? '⏳' : '✕ Disconnect'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
