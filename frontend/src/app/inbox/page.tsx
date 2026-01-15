'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, workspaces, inbox } from '@/lib/api';

interface Reply {
    id: number;
    lead_email: string;
    lead_name?: string;
    campaign_name?: string;
    subject?: string;
    body?: string;
    classification?: string;
    received_at?: string;
}

const classificationColors: Record<string, string> = {
    booking_intent: 'success',
    neutral: 'info',
    negative: 'warning',
    unsubscribe: 'danger',
    unknown: 'info',
};

const classificationLabels: Record<string, string> = {
    booking_intent: '📅 Interested',
    neutral: '💬 Neutral',
    negative: '❌ Not Interested',
    unsubscribe: '🚫 Unsubscribed',
    unknown: '❓ Unknown',
};

export default function InboxPage() {
    const router = useRouter();
    const [token, setToken] = useState<string | null>(null);
    const [workspaceId, setWorkspaceId] = useState<number | null>(null);
    const [replies, setReplies] = useState<Reply[]>([]);
    const [selectedReply, setSelectedReply] = useState<any | null>(null);
    const [thread, setThread] = useState<any[]>([]);
    const [replyBody, setReplyBody] = useState('');
    const [sending, setSending] = useState(false);
    const [loading, setLoading] = useState(true);
    const [userName, setUserName] = useState('');

    // AI Draft State
    const [draftLoading, setDraftLoading] = useState(false);
    const [activeDraft, setActiveDraft] = useState<any>(null); // To store current generated draft
    const [isEditingDraft, setIsEditingDraft] = useState(false);

    useEffect(() => {
        const init = async () => {
            const storedToken = localStorage.getItem('token');
            if (!storedToken) {
                router.push('/');
                return;
            }
            setToken(storedToken);

            try {
                const user = await auth.getMe(storedToken);
                setUserName(user.email);

                const userWorkspaces = await workspaces.list(storedToken);
                if (userWorkspaces.length === 0) {
                    router.push('/wizard');
                    return;
                }
                const wsId = userWorkspaces[0].id;
                setWorkspaceId(wsId);

                const replyList = await inbox.replies(storedToken, wsId);
                setReplies(replyList);

                if (replyList.length > 0) {
                    handleSelectReply(replyList[0], storedToken);
                }

            } catch (err) {
                console.error('Error loading inbox:', err);
            }
            setLoading(false);
        };

        const handleSelectReply = async (reply: any, authToken?: string) => {
            setSelectedReply(reply);
            const t = authToken || token;
            if (!t) return;

            try {
                const fullReply = await inbox.getReply(t, reply.id);
                setThread(fullReply.thread || []);
            } catch (err) {
                console.error('Error fetching thread:', err);
                setThread([]);
            }
        };

        init();
    }, [router]);

    const handleSelectReply = async (reply: any) => {
        setSelectedReply(reply);
        if (!token) return;

        try {
            const fullReply = await inbox.getReply(token, reply.id);
            setThread(fullReply.thread || []);
            setReplyBody(''); // Reset reply body when switching
        } catch (err) {
            console.error('Error fetching thread:', err);
            setThread([]);
        }
    };

    const handleClassify = async (replyId: number, classification: string) => {
        if (!token) return;

        try {
            await inbox.classify(token, replyId, classification);
            setReplies((prev: Reply[]) => prev.map((r: Reply) =>
                r.id === replyId ? { ...r, classification } : r
            ));
            if (selectedReply?.id === replyId) {
                setSelectedReply({ ...selectedReply, classification });
            }
        } catch (err) {
            console.error('Error classifying:', err);
        }
    };

    const handleSendReply = async () => {
        if (!token || !selectedReply || !replyBody.trim()) return;

        setSending(true);
        try {
            await inbox.sendReply(token, selectedReply.id, replyBody);
            // Re-fetch thread to show new message
            const fullReply = await inbox.getReply(token, selectedReply.id);
            setThread(fullReply.thread || []);
            setReplyBody('');
            setActiveDraft(null); // Clear draft after sending manual reply too?
        } catch (err: any) {
            console.error('Error sending reply:', err);
            alert(`Failed to send: ${err.message}`);
        }
        setSending(false);
    };

    const handleGenerateDraft = async () => {
        if (!token || !selectedReply) return;
        setDraftLoading(true);
        try {
            // Find gmail_thread_id from the selected reply or thread
            // selectedReply only has superficial data, need thread_id. 
            // Luckily `handleSelectReply` fetches fullReply which usually has it? 
            // Wait, I need to look at `selectedReply` or `thread` structure. 
            // `selectedReply` comes from list_replies which has no thread_id exposed in Reply model explicitly? 
            // checking `get_reply` response, it returns `gmail_thread_id`.

            // So I should grab it from the full details loaded:
            // But `selectedReply` is the list item. I need to store the FULL reply details including thread_id.
            // Let's re-fetch or assume `handleSelectReply` updates state... NO, it updates `thread` state. 

            // I need the thread ID. I'll get it from the API call for single reply.
            // Let's fetch it again to be safe or store it. 
            // Actually `handleSelectReply` does `inbox.getReply`. I should store the result in a state variable `fullReplyData`.
            // But for now, let's just re-fetch or assume I can get it.

            const fullData = await inbox.getReply(token, selectedReply.id);
            const threadId = fullData.gmail_thread_id;

            const draft = await inbox.generateDraft(token, threadId);
            setActiveDraft(draft);
            setReplyBody(draft.body || ""); // Pre-fill textarea
            setIsEditingDraft(true); // Enable edit mode concept

        } catch (err: any) {
            alert(`Failed to generate draft: ${err.message}`);
        }
        setDraftLoading(false);
    };

    const handleSaveDraft = async () => {
        if (!token || !activeDraft) return;
        try {
            await inbox.updateDraft(token, activeDraft.id, replyBody);
            alert("Draft saved!");
        } catch (err: any) {
            alert(`Failed to save: ${err.message}`);
        }
    };

    const handleSendDraft = async () => {
        if (!token || !activeDraft) return;
        setSending(true);
        try {
            // If body changed, update first? Yes ideally.
            if (replyBody !== activeDraft.body) {
                await inbox.updateDraft(token, activeDraft.id, replyBody);
            }

            const result = await inbox.sendDraft(token, activeDraft.id);
            console.log("Send Result:", result);

            // Refresh
            const fullReply = await inbox.getReply(token, selectedReply.id);
            setThread(fullReply.thread || []);
            setReplyBody('');
            setActiveDraft(null);
            setIsEditingDraft(false);

            alert("Reply sent successfully!");

        } catch (err: any) {
            console.error('Error sending draft:', err);
            // Check if it's a specific HTTP error object
            const msg = err.response?.data?.detail || err.message || "Unknown error";
            alert(`Failed to send draft: ${msg}`);
        }
        setSending(false);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        router.push('/');
    };

    if (loading) {
        return (
            <div style={{
                height: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}>
                <div className="animate-pulse">Loading inbox...</div>
            </div>
        );
    }

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
                    <Link href="/dashboard" style={{ color: 'var(--text-secondary)' }}>
                        Dashboard
                    </Link>
                    <Link href="/inbox" style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
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

            {/* Main Content - Split View */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '350px 1fr',
                height: 'calc(100vh - 65px)',
            }}>
                {/* Reply List */}
                <div style={{
                    borderRight: '1px solid var(--border-color)',
                    overflowY: 'auto',
                    background: 'var(--bg-secondary)',
                }}>
                    <div style={{
                        padding: '16px',
                        borderBottom: '1px solid var(--border-color)',
                        fontWeight: '600',
                    }}>
                        Replies ({replies.length})
                    </div>

                    {replies.length === 0 ? (
                        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                            No replies yet
                        </div>
                    ) : (
                        replies.map((reply: Reply) => (
                            <div
                                key={reply.id}
                                onClick={() => handleSelectReply(reply)}
                                style={{
                                    padding: '16px',
                                    borderBottom: '1px solid var(--border-color)',
                                    cursor: 'pointer',
                                    background: selectedReply?.id === reply.id ? 'var(--bg-card)' : 'transparent',
                                }}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span style={{ fontWeight: '500' }}>
                                        {reply.lead_name || reply.lead_email}
                                    </span>
                                    {reply.classification && (
                                        <span className={`badge badge-${classificationColors[reply.classification] || 'info'}`}>
                                            {classificationLabels[reply.classification] || reply.classification}
                                        </span>
                                    )}
                                </div>
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                                    {reply.subject || '(no subject)'}
                                </div>
                                {reply.campaign_name && (
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                        Campaign: {reply.campaign_name}
                                    </div>
                                )}
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                    {reply.received_at && new Date(reply.received_at).toLocaleString()}
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Reply Detail & Thread */}
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    {selectedReply ? (
                        <>
                            <div style={{
                                padding: '24px',
                                borderBottom: '1px solid var(--border-color)',
                                background: 'var(--bg-primary)'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '8px' }}>
                                            {selectedReply.subject || '(no subject)'}
                                        </h2>
                                        <div style={{ display: 'flex', gap: '16px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                                            <span>With: {selectedReply.lead_email}</span>
                                        </div>
                                    </div>

                                    {/* Classification Dropdown/Buttons */}
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                        {Object.entries(classificationLabels).map(([key, label]) => (
                                            <button
                                                key={key}
                                                onClick={() => handleClassify(selectedReply.id, key)}
                                                className={`badge badge-${selectedReply.classification === key ? classificationColors[key] : 'outline'}`}
                                                style={{
                                                    cursor: 'pointer',
                                                    border: selectedReply.classification === key ? 'none' : '1px solid var(--border-color)',
                                                    background: selectedReply.classification === key ? undefined : 'transparent',
                                                    color: selectedReply.classification === key ? undefined : 'var(--text-secondary)',
                                                    padding: '4px 8px',
                                                    fontSize: '11px'
                                                }}
                                            >
                                                {label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Thread View */}
                            <div style={{
                                flex: 1,
                                overflowY: 'auto',
                                padding: '24px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '20px',
                                background: 'var(--bg-primary)'
                            }}>
                                {thread.map((msg: any) => (
                                    <div
                                        key={msg.id}
                                        style={{
                                            alignSelf: msg.direction === 'outbound' ? 'flex-end' : 'flex-start',
                                            maxWidth: '80%',
                                        }}
                                    >
                                        <div style={{
                                            fontSize: '12px',
                                            color: 'var(--text-muted)',
                                            marginBottom: '4px',
                                            textAlign: msg.direction === 'outbound' ? 'right' : 'left'
                                        }}>
                                            {msg.direction === 'outbound' ? 'You' : (selectedReply.lead_name || selectedReply.lead_email)} • {new Date(msg.sent_at || msg.received_at).toLocaleString()}
                                        </div>
                                        <div style={{
                                            background: msg.direction === 'outbound' ? 'var(--bg-tertiary)' : 'var(--bg-card)',
                                            padding: '16px',
                                            borderRadius: '12px',
                                            border: '1px solid var(--border-color)',
                                            fontSize: '14px',
                                            lineHeight: '1.6',
                                            whiteSpace: 'pre-wrap',
                                        }}>
                                            {msg.body}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Reply Input Area */}
                            <div style={{
                                padding: '24px',
                                borderTop: '1px solid var(--border-color)',
                                background: 'var(--bg-secondary)'
                            }}>
                                {activeDraft && (
                                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800 flex justify-between items-center">
                                        <span>
                                            ✨ AI Draft Generated ({activeDraft.model})
                                            {activeDraft.risk_flags && activeDraft.risk_flags.length > 0 &&
                                                <span className="ml-2 text-red-600 font-bold">⚠️ Risk Flags: {activeDraft.risk_flags.join(', ')}</span>
                                            }
                                        </span>
                                        <button
                                            onClick={() => { setActiveDraft(null); setReplyBody(''); }}
                                            className="text-blue-600 hover:text-blue-800"
                                        >
                                            Discard
                                        </button>
                                    </div>
                                )}

                                <div style={{ position: 'relative' }}>
                                    <textarea
                                        className="input w-full"
                                        placeholder={`Reply to ${selectedReply.lead_email}...`}
                                        value={replyBody}
                                        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReplyBody(e.target.value)}
                                        style={{
                                            minHeight: '120px',
                                            padding: '16px',
                                            paddingBottom: '60px',
                                            resize: 'vertical',
                                        }}
                                    />
                                    <div style={{
                                        position: 'absolute',
                                        bottom: '12px',
                                        right: '12px',
                                        display: 'flex',
                                        gap: '8px'
                                    }}>
                                        <button
                                            type="button"
                                            onClick={handleGenerateDraft}
                                            disabled={draftLoading || sending}
                                            style={{
                                                marginRight: '8px',
                                                backgroundColor: '#e0e7ff',
                                                color: '#3730a3',
                                                border: '1px solid #c7d2fe',
                                                padding: '8px 16px',
                                                borderRadius: '6px',
                                                cursor: 'pointer',
                                                fontWeight: '500',
                                                display: activeDraft ? 'none' : 'flex',
                                                alignItems: 'center',
                                                gap: '8px'
                                            }}
                                        >
                                            {draftLoading ? '✨ Generating...' : '✨ AI Draft Reply'}
                                        </button>

                                        {activeDraft && (
                                            <button
                                                className="btn btn-secondary"
                                                onClick={handleSaveDraft}
                                                disabled={sending}
                                                style={{ marginRight: '8px' }}
                                            >
                                                💾 Save Draft
                                            </button>
                                        )}

                                        <button
                                            className="btn btn-primary"
                                            disabled={!replyBody.trim() || sending}
                                            onClick={activeDraft ? handleSendDraft : handleSendReply}
                                        >
                                            {sending ? 'Sending...' : '🚀 Send Reply'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div style={{
                            height: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--text-muted)',
                        }}>
                            Select a reply to view conversation
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
