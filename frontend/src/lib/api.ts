const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

interface ApiOptions {
    method?: string;
    body?: any;
    token?: string;
}

export class ApiError extends Error {
    status: number;
    detail: any;

    constructor(message: string, status: number, detail: any = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.detail = detail;
    }
}

async function apiRequest<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { method = 'GET', body, token } = options;

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Ensure endpoint starts with a slash
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

    const response = await fetch(`${API_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
        let errorMsg = 'Request failed';
        let errorDetail: any = null;
        try {
            const error = await response.json();
            errorDetail = error?.detail ?? error?.message ?? null;
            errorMsg = typeof errorDetail === 'string' ? errorDetail : errorMsg;
        } catch (e) {
            // Not JSON
        }
        throw new ApiError(errorMsg, response.status, errorDetail);
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

// Auth
export const auth = {
    register: (email: string, password: string) =>
        apiRequest<{ id: number; email: string }>('/auth/register', {
            method: 'POST',
            body: { email, password },
        }),

    login: (email: string, password: string) =>
        apiRequest<{ access_token: string; token_type: string }>('/auth/login', {
            method: 'POST',
            body: { email, password },
        }),

    getMe: (token: string) =>
        apiRequest<{ id: number; email: string }>('/auth/me', { token }),
};

// Workspaces
export const workspaces = {
    create: (token: string, name: string) =>
        apiRequest<any>('/workspaces/', {
            method: 'POST',
            body: { name },
            token,
        }),

    list: (token: string) =>
        apiRequest<any[]>('/workspaces/', { token }),

    get: (token: string, id: number) =>
        apiRequest<any>(`/workspaces/${id}`, { token }),

    updateSetup: (token: string, id: number, data: any) =>
        apiRequest<any>(`/workspaces/${id}/setup`, {
            method: 'PUT',
            body: data,
            token,
        }),

    safetyStatus: (token: string, id: number) =>
        apiRequest<any>(`/workspaces/${id}/safety-status`, { token }),
};

// Mailboxes
export const mailboxes = {
    getOAuthUrl: (token: string, workspaceId: number) =>
        apiRequest<{ auth_url: string }>(`/mailboxes/oauth/url?workspace_id=${workspaceId}`, {
            token,
        }),

    list: (token: string, workspaceId: number) =>
        apiRequest<any[]>(`/mailboxes/?workspace_id=${workspaceId}`, { token }),

    disconnect: (token: string, mailboxId: number) =>
        apiRequest<void>(`/mailboxes/${mailboxId}`, {
            method: 'DELETE',
            token,
        }),
};

// Domains
export const domains = {
    check: (token: string, workspaceId: number, domain: string) =>
        apiRequest<any>(`/domains/check?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { domain },
            token,
        }),
};

// Leads
export const leads = {
    list: (token: string, workspaceId: number) =>
        apiRequest<any[]>(`/leads/?workspace_id=${workspaceId}`, { token }),

    source: (token: string, workspaceId: number, domains: string[]) =>
        apiRequest<any>(`/leads/source?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { domains },
            token,
        }),

    uploadCsv: (token: string, workspaceId: number, formData: FormData) => {
        return fetch(`${API_URL}/leads/upload-csv?workspace_id=${workspaceId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
            body: formData,
        }).then(res => {
            if (!res.ok) throw new Error('Upload failed');
            return res.json();
        });
    },

    mapColumns: (token: string, workspaceId: number, formData: FormData) => {
        return fetch(`${API_URL}/leads/map-columns?workspace_id=${workspaceId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
            body: formData,
        }).then(res => {
            if (!res.ok) throw new Error('Import failed');
            return res.json();
        });
    },

    leadgenSearch: (token: string, workspaceId: number, query: string, location?: string, desiredCount?: number) =>
        apiRequest<any>(`/leads/leadgen/search?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { query, location, desired_count: desiredCount },
            token,
        }),

    leadgenImport: (token: string, workspaceId: number, leads: any[]) =>
        apiRequest<any[]>(`/leads/leadgen/import?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { leads },
            token,
        }),

    leadgenEnrich: (token: string, workspaceId: number, company: string, website: string) =>
        apiRequest<any[]>(`/leads/leadgen/enrich?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { company, website },
            token,
        }),

    importManual: (token: string, workspaceId: number, leads: any[]) =>
        apiRequest<any[]>(`/leads/manual?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: { leads },
            token,
        }),
};

// Campaigns
export const campaigns = {
    create: (token: string, workspaceId: number, data: any) =>
        apiRequest<any>(`/campaigns/?workspace_id=${workspaceId}`, {
            method: 'POST',
            body: data,
            token,
        }),

    list: (token: string, workspaceId: number) =>
        apiRequest<any[]>(`/campaigns/?workspace_id=${workspaceId}`, { token }),

    get: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}`, { token }),

    setEmails: (token: string, campaignId: number, data: {
        subject: string;
        body: string;
        followup_enabled: boolean;
        followup_delay_days: number;
        followup_subject?: string;
        followup_body?: string;
        followup_templates?: any[];
    }) =>
        apiRequest<any>(`/campaigns/${campaignId}/emails`, {
            method: 'PUT',
            body: data,
            token,
        }),

    updateFollowupTemplates: (token: string, campaignId: number, templates: any[]) =>
        apiRequest<any>(`/campaigns/${campaignId}/followup-templates`, {
            method: 'PATCH',
            body: templates,
            token,
        }),

    preview: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/preview`, { token }),

    launch: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/launch`, {
            method: 'POST',
            token,
        }),

    pause: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/pause`, {
            method: 'POST',
            token,
        }),

    resume: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/resume`, {
            method: 'POST',
            token,
        }),

    dashboard: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/dashboard`, { token }),

    terminate: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}`, {
            method: 'DELETE',
            token,
        }),

    getSchedule: (token: string, id: number) =>
        apiRequest<any>(`/campaigns/${id}/schedule`, { token }),

    cancelLeadFollowups: (token: string, campaignLeadId: number, reason: string, detail: string) =>
        apiRequest<any>(`/campaign_leads/${campaignLeadId}/cancel-followups`, {
            method: 'POST',
            body: { reason, detail },
            token,
        }),
};

// Campaigns AI
export const campaignsAI = {
    generateDraft: (token: string, campaignId: number, tone: string, length: string, includeFollowup: boolean) =>
        apiRequest<any>(`/campaigns/${campaignId}/ai/draft`, {
            method: 'POST',
            body: { tone, length, include_followup: includeFollowup },
            token,
        }),

    draftUsage: (token: string, campaignId: number) =>
        apiRequest<any>(`/campaigns/${campaignId}/ai/draft-usage`, { token }),

    lintEmail: (token: string, campaignId: number, subject: string, body: string, followupSubject?: string, followupBody?: string) =>
        apiRequest<any>(`/campaigns/${campaignId}/ai/lint`, {
            method: 'POST',
            body: { subject, body, followup_subject: followupSubject, followup_body: followupBody },
            token,
        }),
};

// Inbox AI
export const inboxAI = {
    classify: (token: string, messageId: number) =>
        apiRequest<any>(`/inbox/replies/${messageId}/ai/classify`, {
            method: 'POST',
            body: {},
            token,
        }),
};

// Inbox
export const inbox = {
    replies: (token: string, workspaceId: number, campaignId?: number) => {
        let url = `/inbox/replies?workspace_id=${workspaceId}`;
        if (campaignId) url += `&campaign_id=${campaignId}`;
        return apiRequest<any[]>(url, { token });
    },

    getReply: (token: string, replyId: number) =>
        apiRequest<any>(`/inbox/replies/${replyId}`, { token }),

    sendReply: (token: string, replyId: number, body: string) =>
        apiRequest<any>(`/inbox/replies/${replyId}/send`, {
            method: 'POST',
            body: { body },
            token,
        }),

    classify: (token: string, replyId: number, classification: string) =>
        apiRequest<any>(`/inbox/replies/${replyId}/classify`, {
            method: 'POST',
            body: { classification },
            token,
        }),

    generateDraft: (token: string, threadId: string) =>
        apiRequest<any>(`/inbox/threads/${threadId}/ai-draft`, {
            method: 'POST',
            body: {},
            token,
        }),

    updateDraft: (token: string, draftId: number, body: string) =>
        apiRequest<any>(`/inbox/drafts/${draftId}/update`, {
            method: 'POST',
            body: { body },
            token,
        }),

    // Correction: I should update the router to Body, or use query param here. 
    // Let's assume I will fix the router later or use query param. 
    // Using query param for body is bad for long text. 
    // I should have made a Pydantic model for UpdateDraftRequest. 
    // I will use `?body=...` for now in the frontend call to match default FastAPI behavior for scalars.

    // Actually, I'll update the router next step to be safe. 
    // Let's assume standard POST body structure for cleanliness.

    sendDraft: (token: string, draftId: number) =>
        apiRequest<any>(`/inbox/drafts/${draftId}/send`, {
            method: 'POST',
            body: {},
            token,
        }),
};

export const booking = {
    setupInfo: (token: string) =>
        apiRequest<any>('/booking/setup-info', { token }),
};

export const health = {
    celery: () => apiRequest<any>('/health/celery'),
};

export default {
    auth,
    workspaces,
    mailboxes,
    domains,
    leads,
    campaigns,
    campaignsAI,
    inbox,
    inboxAI,
    booking,
    health,
};
