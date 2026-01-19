'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, workspaces, campaigns, campaignsAI, mailboxes, leads } from '@/lib/api';

export default function NewCampaignPage() {
    const router = useRouter();
    const [token, setToken] = useState<string | null>(null);
    const [workspaceId, setWorkspaceId] = useState<number | null>(null);
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Data
    const [mailboxList, setMailboxList] = useState<any[]>([]);
    const [leadList, setLeadList] = useState<any[]>([]);

    // Form state
    const [name, setName] = useState('');
    const [selectedMailbox, setSelectedMailbox] = useState<number | null>(null);
    const [selectedLeads, setSelectedLeads] = useState<number[]>([]);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [followupEnabled, setFollowupEnabled] = useState(true);
    const [followupDays, setFollowupDays] = useState(3);
    const [followupSubject, setFollowupSubject] = useState('');
    const [followupBody, setFollowupBody] = useState('');
    const [customerInfoText, setCustomerInfoText] = useState(''); // JSON or freeform
    const [contextWhatYouSell, setContextWhatYouSell] = useState('');
    const [contextTargetIndustry, setContextTargetIndustry] = useState('');
    const [contextTargetRole, setContextTargetRole] = useState('');
    const [contextTargetRegion, setContextTargetRegion] = useState('');
    const [contextOfferType, setContextOfferType] = useState('');
    const [contextPainPoints, setContextPainPoints] = useState('');
    const [contextValueProp, setContextValueProp] = useState('');
    const [contextSocialProof, setContextSocialProof] = useState('');
    const [contextCtaPreference, setContextCtaPreference] = useState('');
    const [contextPersonalizationNotes, setContextPersonalizationNotes] = useState('');

    const [campaignId, setCampaignId] = useState<number | null>(null);
    const [preview, setPreview] = useState<any>(null);
    const [generatingCopy, setGeneratingCopy] = useState(false);
    const [draftResponse, setDraftResponse] = useState<any>(null);
    const [lintResult, setLintResult] = useState<any>(null);
    const [lintLoading, setLintLoading] = useState(false);

    // Add Leads Modal State
    const [showAddLeadsModal, setShowAddLeadsModal] = useState(false);
    const [addLeadsTab, setAddLeadsTab] = useState<'csv' | 'source' | 'leadgen'>('csv');
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [csvMapping, setCsvMapping] = useState<any>(null); // Columns from backend
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
    const [leadGenQuery, setLeadGenQuery] = useState('');
    const [leadGenLocation, setLeadGenLocation] = useState('');
    const [leadGenResults, setLeadGenResults] = useState<any[]>([]);
    const [leadGenSelected, setLeadGenSelected] = useState<string[]>([]);
    const [leadGenSearched, setLeadGenSearched] = useState(false);
    const [leadGenDesiredCount, setLeadGenDesiredCount] = useState(50);
    const [leadGenCompanies, setLeadGenCompanies] = useState<any[]>([]);
    const [leadGenEnriching, setLeadGenEnriching] = useState<string | null>(null);

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

    const handleCreateCampaign = async () => {
        if (!token || !workspaceId || !selectedMailbox) return;
        setSaving(true);
        setError(null);

        try {
            const customerInfo: any = {};
            if (contextWhatYouSell.trim()) customerInfo.what_you_sell = contextWhatYouSell.trim();
            if (contextTargetIndustry.trim()) customerInfo.target_industry = contextTargetIndustry.trim();
            if (contextTargetRole.trim()) customerInfo.target_role = contextTargetRole.trim();
            if (contextTargetRegion.trim()) customerInfo.target_region = contextTargetRegion.trim();
            if (contextOfferType.trim()) customerInfo.offer_type = contextOfferType.trim();
            if (contextPainPoints.trim()) customerInfo.pain_points = contextPainPoints.trim();
            if (contextValueProp.trim()) customerInfo.value_prop = contextValueProp.trim();
            if (contextSocialProof.trim()) customerInfo.social_proof = contextSocialProof.trim();
            if (contextCtaPreference.trim()) customerInfo.cta_preference = contextCtaPreference.trim();
            if (contextPersonalizationNotes.trim()) customerInfo.personalization_notes = contextPersonalizationNotes.trim();
            if (customerInfoText.trim()) customerInfo.additional_context = customerInfoText.trim();

            // Create campaign
            const campaign = await campaigns.create(token, workspaceId, {
                name,
                mailbox_id: selectedMailbox,
                lead_ids: selectedLeads,
                customer_info: Object.keys(customerInfo).length ? customerInfo : undefined,
            });
            setCampaignId(campaign.id);

            // Auto-generate email copy
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
                if (draft.followup_subject) setFollowupSubject(draft.followup_subject);
                if (draft.followup_body) setFollowupBody(draft.followup_body);
            } catch (draftErr: any) {
                console.error('Error generating copy:', draftErr);
                const draftErrMsg = draftErr?.detail || draftErr?.message || 'Failed to generate email copy';
                setError(`Campaign created, but failed to generate copy: ${draftErrMsg}`);
                // Still proceed to Step 3 even if generation fails
            } finally {
                setGeneratingCopy(false);
            }

            setStep(3);
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
            await campaigns.setEmails(token, campaignId, {
                subject,
                body,
                followup_enabled: followupEnabled,
                followup_delay_days: followupDays,
                followup_subject: followupSubject || undefined,
                followup_body: followupBody || undefined,
            });

            const previewData = await campaigns.preview(token, campaignId);
            setPreview(previewData);
            setStep(4);
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
            // Auto-map common columns
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
            setCsvMapping(true); // Switch to mapping view
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
            formData.append('mapping', JSON.stringify(columnMap)); // Backend expects JSON in body for map endpoint? 
            // Wait, leads.py map_columns takes mapping: CSVColumnMapping AND file: UploadFile. 
            // FastAPI handles mixed form/json typically by treating JSON as a form field string if not using Depends properly.
            // Let's check leads.py... it uses mapping: CSVColumnMapping which implies JSON body if not Form(...). 
            // Actually, in FastAPI, if you mix File and Pydantic model, you usually need to make the Pydantic model Depends() or json string.
            // Let's try sending mapping as fields in FormData for now? No, standard is weird.
            // Let me check leads.py again. `mapping: CSVColumnMapping, file: UploadFile = File(...)`.
            // Because one arg is File/Form, Pydantic model is NOT read from JSON body by default. It expects query params or needs special handling.
            // The most robust way is to send each field: `mapping.email`, `mapping.first_name` etc as form fields? 
            // OR the backend might fail. Let's assume for a moment the backend expects JSON. 
            // Wait, I can't check backend leads.py easily right now without switching context.
            // Let's assume the previous `leads.py` showed `mapping: CSVColumnMapping`. 
            // To be safe, I will construct a JSON blob and valid FormData if possible, OR I will just append fields.
            // Actually, let's look at `uploadCsv` in `api.ts`. It's fine.
            // For `mapColumns`, I'll append the mapping as a JSON string field named 'mapping' if backend supports it, or individual fields.
            // Let's assume individual fields to be safe if backend uses Form/Depends. 
            // BUT, `leads.py` Step 839: `mapping: CSVColumnMapping`. It's a Request Body model. 
            // Mixing Body and File is tricky. Usually requires `mapping: str = Body(...)` and then parsing.
            // If the backend isn't set up for "Pydantic-in-Form", this might 422. 
            // I'll assume the backend expects JSON encoded in a form field or individual helper.
            // Let's try sending 'mapping' as a JSON string in formData.
            // Wait, checking `leads.py` step 839 again... 
            // `async def map_columns_and_import(workspace_id: int, mapping: CSVColumnMapping, ...)`
            // It does NOT say `Depends`. So it expects JSON Body. 
            // But `file` is `File(...)`. You CANNOT have JSON Body and File in same request easily (spec issue).
            // It practically *must* be that `mapping` fields are expected as query params OR the backend is broken for this mixed type.
            // Oh, unless `CSVColumnMapping` properties are sent as Form fields.
            // Let's try sending `mapping` as a JSON string. If it fails, I'll fix it.

            // Actually, looking at `api.ts` I just modified, I pass `formData`.
            // I'll append `mapping` as a JSON string key, and hopefully backend parses it?
            // If not, I'll need to send `email`, `first_name` etc as individual keys. 
            // Let's try individual keys matching the model structure.
            formData.append('email', columnMap.email);
            if (columnMap.first_name) formData.append('first_name', columnMap.first_name);
            if (columnMap.last_name) formData.append('last_name', columnMap.last_name);
            if (columnMap.company) formData.append('company', columnMap.company);
            if (columnMap.title) formData.append('title', columnMap.title);

            // Re-read leads.py from memory... 
            // `leads.py` line 64: `mapping: CSVColumnMapping`.
            // FastAPI automatically tries to read Pydantic models from Query params if it's GET, or Body if POST.
            // Since it's Multimart/Form-data (due to File), it expects these as Form fields!
            // So `email`, `first_name` should work as form fields.

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
            // Don't close modal yet, show results
        } catch (err) {
            alert('Sourcing failed.');
        }
        setSaving(false);
    };

    const handleLeadGenSearch = async () => {
        if (!token || !workspaceId || !leadGenQuery.trim()) return;
        setSaving(true);
        try {
            setLeadGenSearched(false);
            setLeadGenResults([]);
            setLeadGenCompanies([]);
            const res = await leads.leadgenSearch(
                token,
                workspaceId,
                leadGenQuery.trim(),
                leadGenLocation.trim() || undefined,
                leadGenDesiredCount
            );
            const results = res?.leads || [];
            setLeadGenResults(results);
            setLeadGenCompanies(res?.companies || []);
            setLeadGenSelected(results.filter((lead: any) => !(lead.missing_fields?.length)).map((lead: any) => lead.email));
        } catch (err) {
            alert('Lead gen search failed.');
        }
        setLeadGenSearched(true);
        setSaving(false);
    };

    const handleLeadGenImport = async () => {
        if (!token || !workspaceId || leadGenSelected.length === 0) return;
        setSaving(true);
        try {
            const selected = leadGenResults.filter(lead => leadGenSelected.includes(lead.email));
            const res = await leads.leadgenImport(token, workspaceId, selected);
            await refreshLeads(token, workspaceId);
            setLeadGenResults([]);
            setLeadGenSelected([]);
            setLeadGenQuery('');
            setLeadGenLocation('');
            setLeadGenSearched(false);
            setLeadGenCompanies([]);
            setShowAddLeadsModal(false);
            alert(`Imported ${res.length} leads!`);
        } catch (err) {
            alert('Lead gen import failed.');
        }
        setSaving(false);
    };

    const handleLeadGenEnrich = async (company: string, website: string) => {
        if (!token || !workspaceId) return;
        if (!website) {
            alert('No website available to enrich.');
            return;
        }
        setLeadGenEnriching(website);
        try {
            const res = await leads.leadgenEnrich(token, workspaceId, company, website);
            const existing = new Set(leadGenResults.map(l => l.email));
            const merged = [...leadGenResults];
            let added = 0;
            for (const lead of res) {
                if (!existing.has(lead.email)) {
                    merged.push(lead);
                    existing.add(lead.email);
                    added += 1;
                }
            }
            setLeadGenResults(merged);
            if (added === 0) {
                alert('No new contacts found for this company.');
            }
        } catch (err) {
            alert('Lead enrichment failed.');
        }
        setLeadGenEnriching(null);
    };

    if (loading) {
        return (
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="animate-pulse">Loading...</div>
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
                gap: '32px',
                padding: '24px',
                borderBottom: '1px solid var(--border-color)',
            }}>
                {['Setup', 'Select Leads', 'Email Copy', 'Launch'].map((label, i) => (
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
                        <span style={{ color: step === i + 1 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                            {label}
                        </span>
                    </div>
                ))}
            </div>

            {/* Step Content */}
            <div className="container" style={{ maxWidth: '700px', padding: '32px 24px' }}>
                {/* Step 1: Setup */}
                {step === 1 && (
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

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                Campaign context (used for AI prompt)
                            </label>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                <input
                                    type="text"
                                    className="input"
                                    value={contextWhatYouSell}
                                    onChange={(e) => setContextWhatYouSell(e.target.value)}
                                    placeholder="What do you sell?"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextTargetIndustry}
                                    onChange={(e) => setContextTargetIndustry(e.target.value)}
                                    placeholder="Target industry"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextTargetRole}
                                    onChange={(e) => setContextTargetRole(e.target.value)}
                                    placeholder="Target role"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextTargetRegion}
                                    onChange={(e) => setContextTargetRegion(e.target.value)}
                                    placeholder="Target region"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextOfferType}
                                    onChange={(e) => setContextOfferType(e.target.value)}
                                    placeholder="Offer type (demo, audit, etc.)"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextPainPoints}
                                    onChange={(e) => setContextPainPoints(e.target.value)}
                                    placeholder="Primary pain point"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextValueProp}
                                    onChange={(e) => setContextValueProp(e.target.value)}
                                    placeholder="Value proposition"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextSocialProof}
                                    onChange={(e) => setContextSocialProof(e.target.value)}
                                    placeholder="Social proof (optional)"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextCtaPreference}
                                    onChange={(e) => setContextCtaPreference(e.target.value)}
                                    placeholder="CTA preference (no meeting asks, etc.)"
                                />
                                <input
                                    type="text"
                                    className="input"
                                    value={contextPersonalizationNotes}
                                    onChange={(e) => setContextPersonalizationNotes(e.target.value)}
                                    placeholder="Personalization notes"
                                />
                            </div>
                            <textarea
                                className="input"
                                placeholder="Additional context or constraints"
                                value={customerInfoText}
                                onChange={(e) => setCustomerInfoText(e.target.value)}
                                rows={4}
                                style={{ marginTop: '12px' }}
                            />
                            <small style={{ color: 'var(--text-muted)' }}>These fields are passed into the AI prompt for this campaign.</small>
                        </div>

                        <button
                            className="btn btn-primary"
                            onClick={() => setStep(2)}
                            disabled={!name || !selectedMailbox}
                        >
                            Continue
                        </button>
                    </div>
                )}

                {/* Step 2: Select Leads */}
                {step === 2 && (
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
                                    <button className="btn btn-secondary" onClick={() => setStep(1)}>
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

                {/* Step 3 & 4 remain the same... omitting for brevity if file already has them, but assuming I'm overwriting full file I should include them. */}
                {/* To ensure file correctness I must include all. */}
                {/* Step 3: Email Copy */}
                {step === 3 && (
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
                                <div style={{ marginBottom: '12px' }}>🤖</div>
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
                                    borderLeft: '3px solid var(--accent-primary)'
                                }}>
                                    💡 This email was generated by AI using your campaign context. Feel free to edit it to match your style.
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

                                {/* Draft warnings and optional lint */}
                                {draftResponse?.risky_phrases_found?.length > 0 && (
                                    <div style={{ marginBottom: '16px', padding: '12px', borderRadius: '6px', background: 'var(--bg-warning)' }}>
                                        <div style={{ fontWeight: 600, color: 'var(--text-warning)' }}>⚠️ Potential risky phrases detected</div>
                                        <ul style={{ marginTop: '8px' }}>
                                            {draftResponse.risky_phrases_found.map((p: string, i: number) => (
                                                <li key={i} style={{ color: 'var(--text-secondary)' }}>{p}</li>
                                            ))}
                                        </ul>
                                        <div style={{ marginTop: '8px' }}>
                                            <button className="btn btn-outline btn-sm" onClick={async () => {
                                                if (!token || !campaignId) return;
                                                setLintLoading(true);
                                                try {
                                                    const res = await campaignsAI.lintEmail(token, campaignId, subject, body);
                                                    setLintResult(res);
                                                } catch (err: any) {
                                                    alert('Risk check failed: ' + (err?.message || err));
                                                }
                                                setLintLoading(false);
                                            }} disabled={lintLoading}>
                                                {lintLoading ? 'Checking...' : '🔍 Full Risk Check (AI)'}
                                            </button>
                                        </div>
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

                                <div style={{ marginBottom: '20px' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={followupEnabled}
                                            onChange={(e) => setFollowupEnabled(e.target.checked)}
                                        />
                                        <span>Enable follow-up emails</span>
                                    </label>
                                    {followupEnabled && (
                                        <div style={{ marginTop: '12px', paddingLeft: '24px' }}>
                                            <div style={{ marginBottom: '12px' }}>
                                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                                    Follow-up Subject
                                                </label>
                                                <input
                                                    type="text"
                                                    className="input"
                                                    value={followupSubject}
                                                    onChange={(e) => setFollowupSubject(e.target.value)}
                                                    placeholder="Quick follow-up on this"
                                                />
                                            </div>
                                            <div style={{ marginBottom: '12px' }}>
                                                <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                                    Follow-up Body
                                                </label>
                                                <textarea
                                                    className="input"
                                                    value={followupBody}
                                                    onChange={(e) => setFollowupBody(e.target.value)}
                                                    placeholder="Just following up on my note..."
                                                    rows={4}
                                                    style={{ resize: 'vertical' }}
                                                />
                                            </div>
                                            <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                                Days between follow-ups
                                            </label>
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
                                        </div>
                                    )}
                                </div>

                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button className="btn btn-secondary" onClick={() => setStep(2)}>
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

                {/* Step 4: Launch */}
                {step === 4 && preview && (
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
                            <button className="btn btn-secondary" onClick={() => setStep(3)}>
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
                            <button
                                onClick={() => setAddLeadsTab('leadgen')}
                                style={{
                                    padding: '8px 16px',
                                    background: 'none',
                                    border: 'none',
                                    borderBottom: addLeadsTab === 'leadgen' ? '2px solid var(--accent-primary)' : 'none',
                                    color: addLeadsTab === 'leadgen' ? 'var(--text-primary)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontWeight: '500'
                                }}
                            >
                                Lead Gen
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

                        {addLeadsTab === 'leadgen' && (
                            <div>
                                <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                                    Search the web for companies and extract contacts with full names and titles.
                                </p>
                                <div style={{ display: 'grid', gap: '12px', marginBottom: '16px' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                            Query
                                        </label>
                                        <input
                                            className="input"
                                            placeholder="e.g., restaurants"
                                            value={leadGenQuery}
                                            onChange={(e) => setLeadGenQuery(e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                            Location (optional)
                                        </label>
                                        <input
                                            className="input"
                                            placeholder="e.g., Jaipur"
                                            value={leadGenLocation}
                                            onChange={(e) => setLeadGenLocation(e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                                            Desired leads
                                        </label>
                                        <input
                                            className="input"
                                            type="number"
                                            min={1}
                                            max={200}
                                            value={leadGenDesiredCount}
                                            onChange={(e) => setLeadGenDesiredCount(Number(e.target.value) || 50)}
                                        />
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right', marginBottom: '16px' }}>
                                    <button
                                        className="btn btn-primary"
                                        disabled={!leadGenQuery.trim() || saving}
                                        onClick={handleLeadGenSearch}
                                    >
                                        {saving ? 'Searching...' : 'Search'}
                                    </button>
                                </div>

                                {leadGenResults.length > 0 && (
                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Results</div>
                                        <div style={{ display: 'grid', gap: '8px', marginBottom: '16px' }}>
                                            {leadGenResults.map((lead) => (
                                                <label key={lead.email} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                                                    <input
                                                        type="checkbox"
                                                        checked={leadGenSelected.includes(lead.email)}
                                                        onChange={(e) => {
                                                            const checked = e.target.checked;
                                                            setLeadGenSelected(prev =>
                                                                checked
                                                                    ? [...prev, lead.email]
                                                                    : prev.filter(email => email !== lead.email)
                                                            );
                                                        }}
                                                    />
                                                    <div>
                                                        <div style={{ fontWeight: 500 }}>
                                                            {lead.first_name} {lead.last_name} - {lead.title}
                                                        </div>
                                                        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                                                            {lead.company} | {lead.email}
                                                        </div>
                                                        {lead.missing_fields?.length > 0 && (
                                                            <div style={{ color: 'var(--text-warning)', fontSize: '12px' }}>
                                                                Needs enrichment: {lead.missing_fields.join(', ')}
                                                            </div>
                                                        )}
                                                    </div>
                                                </label>
                                            ))}
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <button
                                                className="btn btn-primary"
                                                disabled={leadGenSelected.length === 0 || saving}
                                                onClick={handleLeadGenImport}
                                            >
                                                {saving ? 'Importing...' : 'Import Selected'}
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {leadGenCompanies.length > 0 && (
                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Companies</div>
                                        <div style={{ display: 'grid', gap: '8px' }}>
                                        {leadGenCompanies.map((company) => {
                                            const companyKey = company.website || company.source_url;
                                            const isEnriching = leadGenEnriching === companyKey;
                                            return (
                                                <div key={companyKey} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                                                    <div>
                                                        <div style={{ fontWeight: 500 }}>{company.company}</div>
                                                        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                                                            {companyKey}
                                                        </div>
                                                    </div>
                                                    <button
                                                        className="btn btn-secondary btn-sm"
                                                        disabled={isEnriching || !companyKey}
                                                        onClick={() => handleLeadGenEnrich(company.company, companyKey)}
                                                    >
                                                        {isEnriching ? 'Enriching...' : 'Enrich Contacts'}
                                                    </button>
                                                </div>
                                            );
                                        })}
                                        </div>
                                    </div>
                                )}

                                {leadGenSearched && leadGenResults.length === 0 && leadGenCompanies.length === 0 && (
                                    <div className="alert alert-warning">
                                        No leads found. Try a different query or location.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
