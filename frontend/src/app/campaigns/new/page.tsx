'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, workspaces, campaigns, campaignsAI, mailboxes, leads } from '@/lib/api';

export default function NewCampaignPage() {
    const router = useRouter();
    const [token, setToken] = useState<string | null>(null);
    const [workspaceId, setWorkspaceId] = useState<number | null>(null);
    const [workspaceData, setWorkspaceData] = useState<any>(null);
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Data
    const [mailboxList, setMailboxList] = useState<any[]>([]);
    const [leadList, setLeadList] = useState<any[]>([]);

    // Campaign Context Wizard (Step 1)
    const [wizardData, setWizardData] = useState({
        what_you_sell: '',
        target_industry: '',
        target_role: '',
        target_region: '',
        offer_type: 'consultation',
    });

    // Form state (Step 2+)
    const [name, setName] = useState('');
    const [selectedMailbox, setSelectedMailbox] = useState<number | null>(null);
    const [selectedLeads, setSelectedLeads] = useState<number[]>([]);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [followupEnabled, setFollowupEnabled] = useState(true);
    const [followupDays, setFollowupDays] = useState(3);
    const [followupSubject, setFollowupSubject] = useState('');
    const [followupBody, setFollowupBody] = useState('');
    const [followupTemplates, setFollowupTemplates] = useState<any[]>([]);

    const [campaignId, setCampaignId] = useState<number | null>(null);
    const [preview, setPreview] = useState<any>(null);
    const [generatingCopy, setGeneratingCopy] = useState(false);
    const [draftResponse, setDraftResponse] = useState<any>(null);
    const [lintResult, setLintResult] = useState<any>(null);
    const [lintLoading, setLintLoading] = useState(false);

    // Add Leads Modal State
    const [showAddLeadsModal, setShowAddLeadsModal] = useState(false);
    const [addLeadsTab, setAddLeadsTab] = useState<'csv' | 'source'>('csv');
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [csvMapping, setCsvMapping] = useState<any>(null);
    const [csvColumns, setCsvColumns] = useState<string[]>([]);
    const [columnMap, setColumnMap] = useState({
        email: '',
        first_name: '',
        last_name: '',
        company: '',
        title: ''
    });
    const [sourcingDomains, setSourcingDomains] = useState('');
    const [sourcingResults, setSourcingResults] = useState<any>(null);

    useEffect(() => {
        const init = async () => {
            const storedToken = localStorage.getItem('token');
            if (!storedToken) {
                router.push('/');
                return;
            }
            setToken(storedToken);

            try {
                const userWorkspaces = await workspaces.list(storedToken);
                if (userWorkspaces.length === 0) {
                    router.push('/wizard');
                    return;
                }
                const wsId = userWorkspaces[0].id;
                setWorkspaceId(wsId);
                setWorkspaceData(userWorkspaces[0]);

                // Pre-fill wizard with workspace defaults if available
                const ws = userWorkspaces[0];
                setWizardData({
                    what_you_sell: ws.what_you_sell || '',
                    target_industry: ws.target_industry || '',
                    target_role: ws.target_role || '',
                    target_region: ws.target_region || '',
                    offer_type: ws.offer_type || 'consultation',
                });

                const mboxes = await mailboxes.list(storedToken, wsId);
                setMailboxList(mboxes);
                if (mboxes.length > 0) {
                    setSelectedMailbox(mboxes[0].id);
                }

                refreshLeads(storedToken, wsId);

            } catch (err) {
                console.error('Error:', err);
            }
            setLoading(false);
        };

        init();
    }, [router]);

    const refreshLeads = async (t: string, wid: number) => {
        try {
            const leadData = await leads.list(t, wid);
            setLeadList(leadData);
        } catch (err) {
            console.error(err);
        }
    };

    const handleWizardNext = () => {
        // Validate wizard data
        if (!wizardData.what_you_sell.trim()) {
            setError('Please describe what you sell');
            return;
        }
        if (!wizardData.target_role.trim()) {
            setError('Please specify your target role');
            return;
        }
        setError(null);
        setStep(2);
    };

    const handleCreateCampaign = async () => {
        if (!token || !workspaceId || !selectedMailbox) return;
        setSaving(true);
        setError(null);

        try {
            // Create campaign with wizard context
            const campaign = await campaigns.create(token, workspaceId, {
                name,
                mailbox_id: selectedMailbox,
                lead_ids: selectedLeads,
                customer_info: wizardData,
            });
            setCampaignId(campaign.id);

            // Auto-generate email copy using AI
            setGeneratingCopy(true);
            try {
                const draft = await campaignsAI.generateDraft(
                    token,
                    campaign.id,
                    'friendly',
                    'medium',
                    true
                );
                setDraftResponse(draft);
                setSubject(draft.subject);
                setBody(draft.body);
                if (draft.followup_templates) {
                    setFollowupTemplates(draft.followup_templates);
                    if (draft.followup_templates.length > 0) {
                        setFollowupSubject(draft.followup_templates[0].subject);
                        setFollowupBody(draft.followup_templates[0].body);
                    }
                } else {
                    if (draft.followup_subject) {
                        setFollowupSubject(draft.followup_subject);
                    }
                    if (draft.followup_body) {
                        setFollowupBody(draft.followup_body);
                    }
                }
            } catch (draftErr: any) {
                console.error('Error generating copy:', draftErr);
                const draftErrMsg = draftErr?.detail || draftErr?.message || 'Failed to generate email copy';
                setError(`Campaign created, but failed to generate copy: ${draftErrMsg}`);
            } finally {
                setGeneratingCopy(false);
            }

            setStep(4);
        } catch (err: any) {
            console.error('Error creating campaign:', err);
            const errorMsg = err?.detail || err?.message || 'Failed to create campaign';
            setError(errorMsg);
        }
        setSaving(false);
    };

    const handleSetEmails = async () => {
        if (!token || !campaignId) return;
        setSaving(true);
        setError(null);

        try {
            const result = await campaigns.setEmails(token, campaignId, {
                subject,
                body,
                followup_enabled: followupEnabled,
                followup_delay_days: followupDays,
                followup_subject: followupSubject,
                followup_body: followupBody,
                followup_templates: followupTemplates,
            });

            const previewData = await campaigns.preview(token, campaignId);
            setPreview(previewData);
            setStep(5);
        } catch (err: any) {
            console.error('Error:', err);
            const errorMsg = err?.detail || err?.message || 'Failed to save email content';
            setError(errorMsg);
        }
        setSaving(false);
    };

    const handleLaunch = async () => {
        if (!token || !campaignId) return;
        setSaving(true);
        setError(null);

        try {
            const result = await campaigns.launch(token, campaignId);
            if (result) {
                router.push('/dashboard');
            }
        } catch (err: any) {
            console.error('Error launching:', err);
            const errorMsg = err?.detail || err?.message || 'Failed to launch campaign. Please check that your mailbox is active and domain is properly configured.';
            setError(errorMsg);
        }
        setSaving(false);
    };

    // --- Lead Management Logic ---

    const handleCsvUpload = async () => {
        if (!token || !workspaceId || !csvFile) return;
        setSaving(true);
        try {
            const formData = new FormData();
            formData.append('file', csvFile);
            const res = await leads.uploadCsv(token, workspaceId, formData);
            setCsvColumns(res.columns);
            const map: any = { ...columnMap };
            res.columns.forEach((col: string) => {
                const lower = col.toLowerCase();
                if (lower.includes('email')) map.email = col;
                else if (lower.includes('first')) map.first_name = col;
                else if (lower.includes('last')) map.last_name = col;
                else if (lower.includes('company') || lower.includes('organization')) map.company = col;
                else if (lower.includes('title') || lower.includes('role')) map.title = col;
            });
            setColumnMap(map);
            setCsvMapping(true);
        } catch (err) {
            alert('Upload failed. Please check your CSV.');
        }
        setSaving(false);
    };

    const handleCsvImport = async () => {
        if (!token || !workspaceId || !csvFile) return;
        setSaving(true);
        try {
            const formData = new FormData();
            formData.append('file', csvFile);
            formData.append('email', columnMap.email);
            if (columnMap.first_name) formData.append('first_name', columnMap.first_name);
            if (columnMap.last_name) formData.append('last_name', columnMap.last_name);
            if (columnMap.company) formData.append('company', columnMap.company);
            if (columnMap.title) formData.append('title', columnMap.title);

            const res = await leads.mapColumns(token, workspaceId, formData);

            await refreshLeads(token, workspaceId);
            setCsvFile(null);
            setCsvMapping(null);
            setShowAddLeadsModal(false);
            alert(`Imported ${res.length} leads!`);
        } catch (err) {
            console.error(err)
            alert('Import failed. Make sure columns are mapped.');
        }
        setSaving(false);
    };

    const handleSourcing = async () => {
        if (!token || !workspaceId || !sourcingDomains) return;
        setSaving(true);
        try {
            const domainList = sourcingDomains.split(',').map(d => d.trim()).filter(Boolean);
            const res = await leads.source(token, workspaceId, domainList);
            setSourcingResults(res);
            await refreshLeads(token, workspaceId);
        } catch (err) {
            alert('Sourcing failed.');
        }
        setSaving(false);
    };

    const handleRegenerateDraft = async () => {
        if (!token || !campaignId) return;
        setGeneratingCopy(true);
        setError(null);
        try {
            const draft = await campaignsAI.generateDraft(
                token,
                campaignId,
                'friendly',
                'medium',
                true
            );
            setDraftResponse(draft);
            setSubject(draft.subject);
            setBody(draft.body);
            if (draft.followup_subject) setFollowupSubject(draft.followup_subject);
            if (draft.followup_body) setFollowupBody(draft.followup_body);
        } catch (err: any) {
            setError('Failed to regenerate: ' + (err?.message || err));
        }
        setGeneratingCopy(false);
    };

    if (loading) {
        return (
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="animate-pulse">Loading...</div>
            </div>
        );
    }

    const stepLabels = ['Campaign Context', 'Setup', 'Select Leads', 'Email Copy', 'Launch'];

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
            {/* Header */}
            <header style={{
                borderBottom: '1px solid var(--border-color)',
                padding: '16px 24px',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
            }}>
                <Link href="/dashboard" style={{ color: 'var(--text-muted)' }}>
                    ← Back
                </Link>
                <h1 style={{ fontSize: '18px', fontWeight: '600' }}>New Campaign</h1>
            </header>

            {/* Progress Steps */}
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '24px',
                padding: '24px',
                borderBottom: '1px solid var(--border-color)',
                flexWrap: 'wrap',
            }}>
                {stepLabels.map((label, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            background: step > i + 1 ? 'var(--accent-success)' : step === i + 1 ? 'var(--gradient-primary)' : 'var(--bg-tertiary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '13px',
                            fontWeight: '600',
                        }}>
                            {step > i + 1 ? '✓' : i + 1}
                        </div>
                        <span style={{ color: step === i + 1 ? 'var(--text-primary)' : 'var(--text-muted)', fontSize: '14px' }}>
                            {label}
                        </span>
                    </div>
                ))}
            </div>

            {/* Step Content */}
            <div className="container" style={{ maxWidth: '700px', padding: '32px 24px' }}>

                {/* Step 1: Campaign Context Wizard */}
                {step === 1 && (
                    <div className="card">
                        <div style={{ marginBottom: '24px' }}>
                            <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>
                                🎯 Tell us about this campaign
                            </h2>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                                This information helps our AI write personalized, high-converting emails for your outreach.
                            </p>
                        </div>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                                What do you sell? <span style={{ color: 'var(--accent-danger)' }}>*</span>
                            </label>
                            <textarea
                                className="input"
                                value={wizardData.what_you_sell}
                                onChange={(e) => setWizardData({ ...wizardData, what_you_sell: e.target.value })}
                                placeholder="e.g., We help B2B SaaS companies reduce churn through predictive analytics and customer health scoring."
                                rows={3}
                                style={{ resize: 'vertical' }}
                            />
                            <small style={{ color: 'var(--text-muted)' }}>Be specific about the problem you solve and the value you provide.</small>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                                    Target Industry
                                </label>
                                <input
                                    type="text"
                                    className="input"
                                    value={wizardData.target_industry}
                                    onChange={(e) => setWizardData({ ...wizardData, target_industry: e.target.value })}
                                    placeholder="e.g., SaaS, FinTech, Healthcare"
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                                    Target Role <span style={{ color: 'var(--accent-danger)' }}>*</span>
                                </label>
                                <input
                                    type="text"
                                    className="input"
                                    value={wizardData.target_role}
                                    onChange={(e) => setWizardData({ ...wizardData, target_role: e.target.value })}
                                    placeholder="e.g., VP of Sales, CTO, Head of Marketing"
                                />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                                    Target Region
                                </label>
                                <input
                                    type="text"
                                    className="input"
                                    value={wizardData.target_region}
                                    onChange={(e) => setWizardData({ ...wizardData, target_region: e.target.value })}
                                    placeholder="e.g., US, Europe, Global"
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                                    What are you offering?
                                </label>
                                <select
                                    className="input"
                                    value={wizardData.offer_type}
                                    onChange={(e) => setWizardData({ ...wizardData, offer_type: e.target.value })}
                                >
                                    <option value="consultation">Free Consultation</option>
                                    <option value="demo">Product Demo</option>
                                    <option value="audit">Free Audit</option>
                                    <option value="call">Quick Call</option>
                                    <option value="trial">Free Trial</option>
                                    <option value="resource">Free Resource</option>
                                </select>
                            </div>
                        </div>

                        <div style={{
                            padding: '16px',
                            background: 'var(--bg-secondary)',
                            borderRadius: '8px',
                            marginBottom: '24px',
                            borderLeft: '4px solid var(--accent-primary)'
                        }}>
                            <div style={{ fontWeight: '600', marginBottom: '8px', fontSize: '14px' }}>💡 Pro Tips</div>
                            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                <li>Be specific about your value proposition—vague descriptions lead to generic emails</li>
                                <li>The more context you provide, the better the AI-generated emails will convert</li>
                                <li>You can refine the generated email copy in the next steps</li>
                            </ul>
                        </div>

                        <button
                            className="btn btn-primary"
                            onClick={handleWizardNext}
                            style={{ width: '100%' }}
                        >
                            Continue →
                        </button>
                    </div>
                )}

                {/* Step 2: Campaign Setup */}
                {step === 2 && (
                    <div className="card">
                        <h2 style={{ fontSize: '18px', marginBottom: '24px' }}>Campaign Setup</h2>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                Campaign Name
                            </label>
                            <input
                                type="text"
                                className="input"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Q1 Outreach"
                            />
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                Send From
                            </label>
                            <select
                                className="input"
                                value={selectedMailbox || ''}
                                onChange={(e) => setSelectedMailbox(Number(e.target.value))}
                            >
                                {mailboxList.map((m) => (
                                    <option key={m.id} value={m.id}>{m.email}</option>
                                ))}
                            </select>
                        </div>

                        {/* Show campaign context summary */}
                        <div style={{
                            padding: '16px',
                            background: 'var(--bg-secondary)',
                            borderRadius: '8px',
                            marginBottom: '20px',
                        }}>
                            <div style={{ fontWeight: '600', marginBottom: '12px', fontSize: '14px' }}>📋 Campaign Context</div>
                            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                <div style={{ marginBottom: '4px' }}><strong>Selling:</strong> {wizardData.what_you_sell || '—'}</div>
                                <div style={{ marginBottom: '4px' }}><strong>Target:</strong> {wizardData.target_role} {wizardData.target_industry ? `in ${wizardData.target_industry}` : ''}</div>
                                <div><strong>Offer:</strong> {wizardData.offer_type}</div>
                            </div>
                            <button
                                onClick={() => setStep(1)}
                                style={{
                                    marginTop: '12px',
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--accent-primary)',
                                    cursor: 'pointer',
                                    fontSize: '13px',
                                    padding: 0,
                                }}
                            >
                                ← Edit context
                            </button>
                        </div>

                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => setStep(1)}>
                                Back
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={() => setStep(3)}
                                disabled={!name || !selectedMailbox}
                            >
                                Continue
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 3: Select Leads */}
                {step === 3 && (
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <h2 style={{ fontSize: '18px' }}>Select Leads</h2>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setShowAddLeadsModal(true)}
                            >
                                + Add Leads
                            </button>
                        </div>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
                            {selectedLeads.length} of {leadList.length} selected
                        </p>

                        {leadList.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '32px', border: '1px dashed var(--border-color)', borderRadius: '8px' }}>
                                <p style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
                                    No leads available.
                                </p>
                                <button className="btn btn-primary" onClick={() => setShowAddLeadsModal(true)}>
                                    Import Leads
                                </button>
                            </div>
                        ) : (
                            <>
                                <div style={{ marginBottom: '16px' }}>
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => setSelectedLeads(
                                            selectedLeads.length === leadList.length ? [] : leadList.map(l => l.id)
                                        )}
                                    >
                                        {selectedLeads.length === leadList.length ? 'Deselect All' : 'Select All'}
                                    </button>
                                </div>

                                <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '20px' }}>
                                    {leadList.map((lead) => (
                                        <div
                                            key={lead.id}
                                            onClick={() => {
                                                setSelectedLeads(prev =>
                                                    prev.includes(lead.id)
                                                        ? prev.filter(id => id !== lead.id)
                                                        : [...prev, lead.id]
                                                );
                                            }}
                                            style={{
                                                padding: '12px',
                                                borderRadius: 'var(--radius-md)',
                                                marginBottom: '8px',
                                                background: selectedLeads.includes(lead.id) ? 'var(--bg-tertiary)' : 'transparent',
                                                border: '1px solid',
                                                borderColor: selectedLeads.includes(lead.id) ? 'var(--accent-primary)' : 'var(--border-color)',
                                                cursor: 'pointer',
                                            }}
                                        >
                                            <div style={{ fontWeight: '500' }}>{lead.email}</div>
                                            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                                                {[lead.first_name, lead.company].filter(Boolean).join(' • ')}
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button className="btn btn-secondary" onClick={() => setStep(2)}>
                                        Back
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleCreateCampaign}
                                        disabled={selectedLeads.length === 0 || saving}
                                    >
                                        {saving ? 'Creating...' : 'Continue'}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* Step 4: Email Copy */}
                {step === 4 && (
                    <div className="card">
                        <h2 style={{ fontSize: '18px', marginBottom: '24px' }}>
                            ✨ AI-Generated Email Content
                        </h2>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        {generatingCopy && (
                            <div style={{
                                padding: '32px',
                                textAlign: 'center',
                                border: '2px dashed var(--border-color)',
                                borderRadius: '8px',
                                marginBottom: '24px',
                                background: 'var(--bg-secondary)'
                            }}>
                                <div style={{ marginBottom: '12px', fontSize: '32px' }}>🤖</div>
                                <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
                                    Generating your email copy...
                                </div>
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                    This usually takes 2-5 seconds
                                </div>
                            </div>
                        )}

                        {!generatingCopy && (
                            <>
                                <div style={{
                                    padding: '12px',
                                    background: 'var(--bg-secondary)',
                                    borderRadius: '6px',
                                    marginBottom: '20px',
                                    fontSize: '12px',
                                    color: 'var(--text-secondary)',
                                    borderLeft: '3px solid var(--accent-primary)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                }}>
                                    <span>💡 This email was generated by AI using your campaign context. Feel free to edit it to match your style.</span>
                                    <button
                                        onClick={handleRegenerateDraft}
                                        disabled={generatingCopy}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--accent-primary)',
                                            cursor: 'pointer',
                                            fontSize: '12px',
                                            whiteSpace: 'nowrap',
                                        }}
                                    >
                                        🔄 Regenerate
                                    </button>
                                </div>

                                <div style={{ marginBottom: '20px' }}>
                                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                        Subject Line
                                    </label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        placeholder="Quick question, {{first_name}}"
                                    />
                                </div>

                                <div style={{ marginBottom: '20px' }}>
                                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                        Email Body
                                    </label>
                                    <textarea
                                        className="input"
                                        value={body}
                                        onChange={(e) => setBody(e.target.value)}
                                        placeholder="Hi {{first_name}},&#10;&#10;I noticed {{company}} is..."
                                        rows={8}
                                        style={{ resize: 'vertical' }}
                                    />
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                        Use {'{{first_name}}'} and {'{{company}}'} for personalization
                                    </div>
                                </div>

                                {/* Draft warnings */}
                                {draftResponse?.risky_phrases_found?.length > 0 && (
                                    <div style={{ marginBottom: '16px', padding: '12px', borderRadius: '6px', background: 'var(--bg-warning)' }}>
                                        <div style={{ fontWeight: 600, color: 'var(--text-warning)' }}>⚠️ Potential risky phrases detected</div>
                                        <ul style={{ marginTop: '8px', marginBottom: '8px' }}>
                                            {draftResponse.risky_phrases_found.map((p: string, i: number) => (
                                                <li key={i} style={{ color: 'var(--text-secondary)' }}>{p}</li>
                                            ))}
                                        </ul>
                                        <button className="btn btn-outline btn-sm" onClick={async () => {
                                            if (!token || !campaignId) return;
                                            setLintLoading(true);
                                            try {
                                                const res = await campaignsAI.lintEmail(token, campaignId, subject, body, followupSubject, followupBody);
                                                setLintResult(res);
                                            } catch (err: any) {
                                                alert('Risk check failed: ' + (err?.message || err));
                                            }
                                            setLintLoading(false);
                                        }} disabled={lintLoading}>
                                            {lintLoading ? 'Checking...' : '🔍 Full Risk Check (AI)'}
                                        </button>
                                    </div>
                                )}

                                {lintResult && (
                                    <div style={{ marginBottom: '16px', padding: '12px', borderRadius: '6px', background: lintResult.verdict === 'SAFE' ? 'var(--bg-success)' : 'var(--bg-danger)' }}>
                                        <div style={{ fontWeight: 600 }}>{lintResult.verdict === 'SAFE' ? '✅ Email is SAFE' : '⚠️ Email is RISKY'} <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>(Risk score: {lintResult.risk_score}/100)</span></div>
                                        {lintResult.issues?.length > 0 && (
                                            <ul style={{ marginTop: 8 }}>
                                                {lintResult.issues.map((issue: any, idx: number) => (
                                                    <li key={idx} style={{ marginBottom: 6 }}>
                                                        <strong>{issue.category}</strong> ({issue.severity}): {issue.explanation}
                                                        {issue.suggestion && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>💡 {issue.suggestion}</div>}
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}

                                <div style={{ marginBottom: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginBottom: '16px' }}>
                                        <input
                                            type="checkbox"
                                            checked={followupEnabled}
                                            onChange={(e) => setFollowupEnabled(e.target.checked)}
                                        />
                                        <span style={{ fontWeight: 600 }}>Enable follow-up sequence</span>
                                    </label>

                                    {followupEnabled && (
                                        <div style={{ paddingLeft: '24px' }}>
                                            <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Send each follow-up after</span>
                                                <select
                                                    className="input"
                                                    value={followupDays}
                                                    onChange={(e) => setFollowupDays(Number(e.target.value))}
                                                    style={{ width: 'auto' }}
                                                >
                                                    {[2, 3, 4, 5, 7].map(d => (
                                                        <option key={d} value={d}>{d} days</option>
                                                    ))}
                                                </select>
                                                <span style={{ color: 'var(--text-secondary)' }}>of no reply</span>
                                            </div>

                                            <div style={{ display: 'grid', gap: '20px' }}>
                                                {followupTemplates.map((tmpl, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '16px',
                                                        background: 'var(--bg-secondary)',
                                                        borderRadius: '8px',
                                                        border: '1px solid var(--border-color)'
                                                    }}>
                                                        <div style={{ fontWeight: 600, marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                                                            <span>Follow-up #{idx + 1} (Step {idx + 1})</span>
                                                            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'normal' }}>
                                                                Will send ~{followupDays * (idx + 1)} days after initial email
                                                            </span>
                                                        </div>
                                                        <div style={{ marginBottom: '12px' }}>
                                                            <input
                                                                type="text"
                                                                className="input"
                                                                value={tmpl.subject}
                                                                onChange={(e) => {
                                                                    const newDrafts = [...followupTemplates];
                                                                    newDrafts[idx].subject = e.target.value;
                                                                    setFollowupTemplates(newDrafts);
                                                                    if (idx === 0) setFollowupSubject(e.target.value);
                                                                }}
                                                                placeholder="Subject"
                                                            />
                                                        </div>
                                                        <textarea
                                                            className="input"
                                                            value={tmpl.body}
                                                            onChange={(e) => {
                                                                const newDrafts = [...followupTemplates];
                                                                newDrafts[idx].body = e.target.value;
                                                                setFollowupTemplates(newDrafts);
                                                                if (idx === 0) setFollowupBody(e.target.value);
                                                            }}
                                                            placeholder="Body"
                                                            rows={4}
                                                            style={{ fontSize: '14px' }}
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button className="btn btn-secondary" onClick={() => setStep(3)}>
                                        Back
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleSetEmails}
                                        disabled={!subject || !body || saving}
                                    >
                                        {saving ? 'Saving...' : 'Preview & Launch'}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* Step 5: Launch */}
                {step === 5 && preview && (
                    <div className="card">
                        <h2 style={{ fontSize: '18px', marginBottom: '24px' }}>Ready to Launch</h2>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '16px',
                            marginBottom: '24px',
                        }}>
                            <div className="stat-card">
                                <div className="stat-value">{preview.total_leads}</div>
                                <div className="stat-label">Total Leads</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{preview.daily_send_limit}</div>
                                <div className="stat-label">Daily Limit</div>
                            </div>
                        </div>

                        <div className="alert alert-warning" style={{ marginBottom: '24px' }}>
                            <div>
                                <strong>Safety Information</strong>
                                <pre style={{
                                    whiteSpace: 'pre-wrap',
                                    fontSize: '13px',
                                    marginTop: '8px',
                                    fontFamily: 'inherit',
                                }}>
                                    {preview.safety_explanation}
                                </pre>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button className="btn btn-secondary" onClick={() => setStep(4)}>
                                Back
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleLaunch}
                                disabled={saving}
                            >
                                {saving ? 'Launching...' : '🚀 Launch Campaign'}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Add Leads Modal */}
            {showAddLeadsModal && (
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                }}>
                    <div className="card" style={{ width: '90%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
                            <h2 style={{ fontSize: '20px' }}>Add Leads</h2>
                            <button onClick={() => setShowAddLeadsModal(false)} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>&times;</button>
                        </div>

                        <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
                            <button
                                onClick={() => setAddLeadsTab('csv')}
                                style={{
                                    padding: '8px 16px',
                                    background: 'none',
                                    border: 'none',
                                    borderBottom: addLeadsTab === 'csv' ? '2px solid var(--accent-primary)' : 'none',
                                    color: addLeadsTab === 'csv' ? 'var(--text-primary)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontWeight: '500'
                                }}
                            >
                                Upload CSV
                            </button>
                            <button
                                onClick={() => setAddLeadsTab('source')}
                                style={{
                                    padding: '8px 16px',
                                    background: 'none',
                                    border: 'none',
                                    borderBottom: addLeadsTab === 'source' ? '2px solid var(--accent-primary)' : 'none',
                                    color: addLeadsTab === 'source' ? 'var(--text-primary)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontWeight: '500'
                                }}
                            >
                                Find Leads
                            </button>
                        </div>

                        {addLeadsTab === 'csv' && (
                            <div>
                                {!csvMapping ? (
                                    <>
                                        <div style={{ border: '2px dashed var(--border-color)', padding: '32px', textAlign: 'center', borderRadius: '8px', marginBottom: '16px' }}>
                                            <input
                                                type="file"
                                                accept=".csv"
                                                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                                                style={{ marginBottom: '16px' }}
                                            />
                                            <p style={{ color: 'var(--text-muted)' }}>Select a CSV file containing email addresses</p>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <button
                                                className="btn btn-primary"
                                                disabled={!csvFile || saving}
                                                onClick={handleCsvUpload}
                                            >
                                                {saving ? 'Uploading...' : 'Upload & Map'}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <p style={{ marginBottom: '16px' }}>Map columns from your CSV:</p>
                                        <div style={{ display: 'grid', gap: '12px', marginBottom: '24px' }}>
                                            {['email', 'first_name', 'last_name', 'company', 'title'].map(field => (
                                                <div key={field} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', alignItems: 'center', gap: '8px' }}>
                                                    <label style={{ fontSize: '14px', textTransform: 'capitalize' }}>{field.replace('_', ' ')}</label>
                                                    <select
                                                        className="input"
                                                        value={columnMap[field as keyof typeof columnMap]}
                                                        onChange={(e) => setColumnMap({ ...columnMap, [field]: e.target.value })}
                                                    >
                                                        <option value="">-- Ignore --</option>
                                                        {csvColumns.map(col => (
                                                            <option key={col} value={col}>{col}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            ))}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => setCsvMapping(false)}
                                            >
                                                Back
                                            </button>
                                            <button
                                                className="btn btn-primary"
                                                disabled={!columnMap.email || saving}
                                                onClick={handleCsvImport}
                                            >
                                                {saving ? 'Importing...' : 'Import Leads'}
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        )}

                        {addLeadsTab === 'source' && (
                            <div>
                                <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                                    Enter websites to find email addresses automatically.
                                </p>
                                <textarea
                                    className="input"
                                    placeholder="acme.com, stripe.com, google.com"
                                    rows={4}
                                    value={sourcingDomains}
                                    onChange={(e) => setSourcingDomains(e.target.value)}
                                    style={{ marginBottom: '16px' }}
                                />
                                {sourcingResults && (
                                    <div className="alert alert-success" style={{ marginBottom: '16px' }}>
                                        Found {sourcingResults.leads_found} new leads from {sourcingResults.domains_searched} domains!
                                    </div>
                                )}
                                <div style={{ textAlign: 'right' }}>
                                    <button
                                        className="btn btn-primary"
                                        disabled={!sourcingDomains || saving}
                                        onClick={handleSourcing}
                                    >
                                        {saving ? 'Searching...' : 'Find Leads'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
