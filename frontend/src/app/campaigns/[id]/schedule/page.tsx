'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { campaigns } from '@/lib/api';

interface ScheduleStep {
    step: number;
    planned_at: string;
    subject: string;
    body?: string;
    body_preview: string;
    status: string;
    sent_at?: string;
    message_id?: string;
}

interface ScheduleItem {
    campaign_lead_id: number;
    lead_email: string;
    lead_name: string | null;
    followup_state: string;
    next_scheduled_at: string | null;
    current_step: number;
    max_followups: number;
    cancel_reason: string | null;
    cancel_detail: string | null;
    cancelled_at: string | null;
    schedule_json: ScheduleStep[] | null;
}

const formatDateTime = (value?: string | null) => {
    if (!value) return '-';
    return new Date(value).toLocaleString();
};

export default function CampaignSchedulePage({ params }: { params: { id: string } }) {
    const router = useRouter();
    const { id } = params;
    const [items, setItems] = useState<ScheduleItem[]>([]);
    const [campaignName, setCampaignName] = useState('');
    const [selected, setSelected] = useState<ScheduleItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [cancelingId, setCancelingId] = useState<number | null>(null);

    const loadSchedule = async () => {
        const token = localStorage.getItem('token');
        if (!token) return router.push('/');
        const data = await campaigns.getSchedule(token, parseInt(id));
        setItems(data.items || []);
        setCampaignName(data.campaign_name || '');
        if (data.items?.length && !selected) {
            setSelected(data.items[0]);
        }
    };

    useEffect(() => {
        loadSchedule().catch(console.error).finally(() => setLoading(false));
    }, [id]);

    const handleCancel = async (campaignLeadId: number) => {
        const token = localStorage.getItem('token');
        if (!token) return;
        setCancelingId(campaignLeadId);
        try {
            await campaigns.cancelLeadFollowups(token, campaignLeadId, 'MANUAL', 'User cancelled from UI');
            await loadSchedule();
        } catch (err) {
            console.error(err);
        } finally {
            setCancelingId(null);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
                <div className="animate-pulse text-gray-500">Loading schedule...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-950 text-white font-sans">
            <header className="border-b border-gray-800 bg-gray-900 p-6 sticky top-0 z-20">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div>
                        <Link href="/dashboard" className="text-gray-400 text-sm hover:text-white mb-2 block">Back to dashboard</Link>
                        <h1 className="text-2xl font-bold">{campaignName || 'Campaign Schedule'}</h1>
                    </div>
                    <div className="text-sm text-gray-400">
                        {items.length} Leads
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto p-6 space-y-6">
                {items.length === 0 ? (
                    <div className="text-center py-20 text-gray-500 border border-dashed border-gray-800 rounded-xl">
                        No leads scheduled yet.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <div className="border border-gray-800 rounded-xl overflow-hidden">
                                <div className="grid grid-cols-5 gap-2 bg-gray-900 text-xs uppercase tracking-wide text-gray-400 px-4 py-3">
                                    <div>Lead</div>
                                    <div>Next Send</div>
                                    <div>Step</div>
                                    <div>State</div>
                                    <div>Reason</div>
                                </div>
                                {items.map((lead) => (
                                    <div
                                        key={lead.campaign_lead_id}
                                        onClick={() => setSelected(lead)}
                                        className={`grid grid-cols-5 gap-2 px-4 py-3 border-t border-gray-800 cursor-pointer ${lead.followup_state !== 'SCHEDULED' ? 'opacity-60' : ''}`}
                                    >
                                        <div>
                                            <div className="font-medium">{lead.lead_name || lead.lead_email}</div>
                                            <div className="text-xs text-gray-500">{lead.lead_email}</div>
                                        </div>
                                        <div className="text-sm text-gray-300">{formatDateTime(lead.next_scheduled_at)}</div>
                                        <div className="text-sm text-gray-300">{lead.current_step}/{lead.max_followups}</div>
                                        <div className="text-sm text-gray-300">{lead.followup_state}</div>
                                        <div className="text-xs text-gray-500">{lead.cancel_reason || '-'}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="border border-gray-800 rounded-xl p-4 bg-gray-900">
                            {selected ? (
                                <>
                                    <div className="flex items-center justify-between mb-3">
                                        <div>
                                            <div className="font-semibold">{selected.lead_name || selected.lead_email}</div>
                                            <div className="text-xs text-gray-500">{selected.lead_email}</div>
                                        </div>
                                        <button
                                            className="btn btn-secondary"
                                            disabled={cancelingId === selected.campaign_lead_id || selected.followup_state === 'CANCELLED'}
                                            onClick={() => handleCancel(selected.campaign_lead_id)}
                                        >
                                            {cancelingId === selected.campaign_lead_id ? 'Cancelling...' : 'Cancel follow-ups'}
                                        </button>
                                    </div>
                                    {selected.cancelled_at && (
                                        <div className="text-xs text-gray-400 mb-3">
                                            Cancelled: {formatDateTime(selected.cancelled_at)} • {selected.cancel_reason || 'Unknown'}
                                            {selected.cancel_detail ? ` — ${selected.cancel_detail}` : ''}
                                        </div>
                                    )}
                                    <div className="text-xs text-gray-500 mb-2">Schedule timeline</div>
                                    <div className="space-y-3">
                                        {(selected.schedule_json || []).map((step, idx) => (
                                            <div key={`${step.step}-${idx}`} className="border border-gray-800 rounded-lg p-3">
                                                <div className="text-xs text-gray-500 mb-1">Step {step.step} • {step.status}</div>
                                                <div className="text-sm text-gray-200">{step.subject || '(No subject)'}</div>
                                                <div className="text-xs text-gray-500 mt-1">{step.body || step.body_preview || '(Draft content)'}</div>
                                                <div className="text-[11px] text-gray-600 mt-2">Planned: {formatDateTime(step.planned_at)}</div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            ) : (
                                <div className="text-sm text-gray-500">Select a lead to view schedule.</div>
                            )}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
