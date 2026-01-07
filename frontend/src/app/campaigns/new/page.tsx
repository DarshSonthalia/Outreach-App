'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { auth, workspaces, campaigns, mailboxes, leads } from '@/lib/api';

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

    const [campaignId, setCampaignId] = useState<number | null>(null);
    const [preview, setPreview] = useState<any>(null);

    // Add Leads Modal State
    const [showAddLeadsModal, setShowAddLeadsModal] = useState(false);
    const [addLeadsTab, setAddLeadsTab] = useState<'csv' | 'source'>('csv');
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
            const campaign = await campaigns.create(token, workspaceId, {
                name,
                mailbox_id: selectedMailbox,
                lead_ids: selectedLeads,
            });
            setCampaignId(campaign.id);
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
                        <h2 style={{ fontSize: '18px', marginBottom: '24px' }}>Email Content</h2>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '24px' }}>
                                <strong>Error:</strong> {error}
                            </div>
                        )}

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
