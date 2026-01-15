'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, campaigns } from '@/lib/api';

interface ScheduleStep {
    step: number;
    planned_at: string;
    subject: string;
    body_preview: string;
    status: string;
    sent_at?: string;
    message_id?: string;
}

interface ScheduleItem {
    lead_email: string;
    lead_name: string;
    followup_state: string;
    current_step: number;
    next_scheduled_at: string | null;
    cancelled_at: string | null;
    cancel_reason: string | null;
    schedule_json: ScheduleStep[] | null;
}

const formatRelativeTime = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays < 0) return 'Overdue';
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    return `In ${diffDays} days`;
};

const StatusBadge = ({ state }: { state: string }) => {
    let style = "bg-gray-800 text-gray-400";
    if (state === 'SCHEDULED') style = "bg-blue-900 text-blue-200 border border-blue-800";
    if (state === 'CANCELLED') style = "bg-red-900 text-red-200 border border-red-800";
    if (state === 'COMPLETED') style = "bg-green-900 text-green-200 border border-green-800";

    return (
        <span className={`px-2 py-0.5 rounded textxs font-medium ${style}`}>
            {state}
        </span>
    );
};

export default function CampaignSchedulePage({ params }: { params: { id: string } }) {
    const router = useRouter();
    const { id } = params;
    const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
    const [campaignName, setCampaignName] = useState('');
    const [followupTemplates, setFollowupTemplates] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [savingTemplates, setSavingTemplates] = useState(false);
    const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

    useEffect(() => {
        const fetchSchedule = async () => {
            const token = localStorage.getItem('token');
            if (!token) return router.push('/');

            try {
                const data = await campaigns.getSchedule(token, parseInt(id));
                setSchedule(data.items);
                setCampaignName(data.campaign_name);
                setFollowupTemplates(data.followup_templates || []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchSchedule();
    }, [id, router]);

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
                <div className="animate-pulse text-gray-500">Loading schedule...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-950 text-white font-sans">
            {/* Simple Header */}
            <header className="border-b border-gray-800 bg-gray-900 p-6 sticky top-0 z-20">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div>
                        <Link href="/dashboard" className="text-gray-400 text-sm hover:text-white mb-2 block">← Dashboard</Link>
                        <h1 className="text-2xl font-bold">{campaignName}</h1>
                    </div>
                    <div className="text-sm text-gray-400">
                        {schedule.length} Leads
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto p-6 space-y-8">
                {/* Master Sequence Editor */}
                {followupTemplates.length > 0 && (
                    <section className="bg-indigo-950/20 border border-indigo-900/50 rounded-2xl p-6">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-indigo-100 flex items-center gap-2">
                                    <span className="text-2xl">📧</span> Campaign Email Sequence
                                </h2>
                                <p className="text-sm text-indigo-300/70 mt-1">Changes here apply to all leads in this campaign who hasn't reached these steps yet.</p>
                            </div>
                            <button
                                className={`px-6 py-2 rounded-lg font-bold transition-all ${savingTemplates ? 'bg-indigo-700 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-900/20'}`}
                                onClick={async () => {
                                    setSavingTemplates(true);
                                    try {
                                        const token = localStorage.getItem('token');
                                        if (token) await campaigns.updateFollowupTemplates(token, parseInt(id), followupTemplates);
                                        alert('Templates saved successfully!');
                                    } catch (err) {
                                        alert('Failed to save templates');
                                    } finally {
                                        setSavingTemplates(false);
                                    }
                                }}
                                disabled={savingTemplates}
                            >
                                {savingTemplates ? 'Saving...' : 'Save Sequence'}
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {followupTemplates.map((tmpl, idx) => (
                                <div key={idx} className="bg-gray-900 border border-gray-800 rounded-xl p-4 focus-within:border-indigo-500 transition-colors">
                                    <div className="flex items-center gap-2 mb-3">
                                        <div className="w-6 h-6 rounded-full bg-indigo-900 text-indigo-300 text-[10px] flex items-center justify-center font-bold">
                                            {tmpl.step}
                                        </div>
                                        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Follow-up #{idx + 1}</span>
                                    </div>
                                    <input
                                        className="w-full bg-black/30 border border-gray-800 rounded-lg p-2 text-sm text-white mb-2 focus:outline-none focus:border-indigo-500"
                                        placeholder="Subject"
                                        value={tmpl.subject}
                                        onChange={(e) => {
                                            const next = [...followupTemplates];
                                            next[idx].subject = e.target.value;
                                            setFollowupTemplates(next);
                                        }}
                                    />
                                    <textarea
                                        className="w-full bg-black/30 border border-gray-800 rounded-lg p-2 text-sm text-gray-300 h-32 resize-none focus:outline-none focus:border-indigo-500"
                                        placeholder="Body"
                                        value={tmpl.body}
                                        onChange={(e) => {
                                            const next = [...followupTemplates];
                                            next[idx].body = e.target.value;
                                            setFollowupTemplates(next);
                                        }}
                                    />
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <h3 className="text-lg font-bold text-gray-100 px-2 mt-8">Lead-Specific Schedule</h3>

                {schedule.length === 0 ? (
                    <div className="text-center py-20 text-gray-500 border border-dashed border-gray-800 rounded-xl">
                        No leads scheduled yet.
                    </div>
                ) : (
                    schedule.map((lead: ScheduleItem, i: number) => (
                        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-colors">
                            {/* Lead Header */}
                            <div className="p-4 bg-gray-900 border-b border-gray-800 flex flex-wrap gap-4 justify-between items-center relative">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-indigo-900 text-indigo-300 flex items-center justify-center font-bold">
                                        {(lead.lead_name || lead.lead_email).charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <div className="font-semibold text-white">{lead.lead_name || "Unknown"}</div>
                                        <div className="text-sm text-gray-400">{lead.lead_email}</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <StatusBadge state={lead.followup_state} />
                                    {lead.cancelled_at && (
                                        <div className="text-right">
                                            <div className="text-xs text-red-400 font-bold uppercase">Cancelled</div>
                                            <div className="text-xs text-red-300">{lead.cancel_reason}</div>
                                        </div>
                                    )}
                                    {!lead.cancelled_at && lead.next_scheduled_at && (
                                        <div className="text-right">
                                            <div className="text-xs text-blue-400 font-bold uppercase">Next: Step {lead.current_step + 1}</div>
                                            <div className="text-xs text-gray-300">{formatRelativeTime(lead.next_scheduled_at)}</div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Timeline / Plan */}
                            <div className="p-4 bg-black/20">
                                {lead.schedule_json ? (
                                    <div className="flex flex-col gap-0 relative">
                                        {/* Vertical line */}
                                        <div className="absolute left-[19px] top-2 bottom-2 w-0.5 bg-gray-800 z-0"></div>

                                        {lead.schedule_json.map((step: ScheduleStep, idx: number) => {
                                            const isPast = step.status === 'SENT';
                                            const isUpcoming = step.status === 'PLANNED' || step.status === 'PENDING';
                                            const isCancelled = lead.cancelled_at && isUpcoming;
                                            const stepKey = `${i}-${idx}`;
                                            const isExpanded = !!expandedSteps[stepKey];

                                            // Determine styles
                                            let dotClass = "bg-gray-700 border-gray-800";
                                            let textClass = "text-gray-500";

                                            if (isPast) {
                                                dotClass = "bg-green-500 border-green-900";
                                                textClass = "text-gray-400";
                                            } else if (isCancelled) {
                                                dotClass = "bg-red-500 border-red-900";
                                                textClass = "text-gray-600 line-through opacity-60";
                                            } else if (isUpcoming) {
                                                dotClass = "bg-blue-500 border-blue-900";
                                                textClass = "text-white";
                                            }

                                            return (
                                                <div key={idx} className={`relative flex gap-4 pb-6 last:pb-0 z-10 ${isCancelled ? 'opacity-50' : ''}`}>
                                                    {/* Dot */}
                                                    <div className={`mt-1.5 w-10 h-10 flex-shrink-0 rounded-full border-4 flex items-center justify-center text-xs font-bold ${dotClass} z-10`}>
                                                        {step.step}
                                                    </div>

                                                    {/* Content */}
                                                    <div className="mt-1 flex-1">
                                                        <div className="flex justify-between items-start">
                                                            <div>
                                                                <h4 className={`text-sm font-bold ${textClass}`}>
                                                                    {step.subject || "(No subject)"}
                                                                </h4>
                                                                <p className={`text-xs mt-1 ${isCancelled ? 'text-gray-600' : 'text-gray-400'}`}>
                                                                    {step.body_preview || "(Draft content)"}
                                                                </p>
                                                                {isExpanded && (
                                                                    <div className="text-[11px] text-gray-500 mt-2">
                                                                        Planned: {step.planned_at ? new Date(step.planned_at).toLocaleString() : "Unknown"}
                                                                    </div>
                                                                )}
                                                            </div>
                                                            <div className="text-right shrink-0">
                                                                <div className="text-xs font-mono text-gray-500">
                                                                    {new Date(step.planned_at).toLocaleDateString()}
                                                                </div>
                                                                <div className="text-[10px] text-gray-600 uppercase font-semibold mt-0.5">
                                                                    {step.status}
                                                                </div>
                                                                <button
                                                                    type="button"
                                                                    className="text-[10px] text-indigo-400 hover:text-indigo-300 mt-2"
                                                                    onClick={() => {
                                                                        setExpandedSteps((prev) => ({
                                                                            ...prev,
                                                                            [stepKey]: !prev[stepKey],
                                                                        }));
                                                                    }}
                                                                >
                                                                    {isExpanded ? "Hide" : "Details"}
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <div className="text-sm text-gray-500 italic">No detailed schedule available.</div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </main>
        </div>
    );
}
