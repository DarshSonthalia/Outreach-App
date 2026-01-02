'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth, workspaces, mailboxes } from '@/lib/api';

interface Message {
    id: number;
    type: 'bot' | 'user';
    content: string;
    inputType?: 'text' | 'select' | 'button';
    options?: { value: string; label: string }[];
    action?: string;
}

const WIZARD_STEPS: Message[] = [
    {
        id: 1,
        type: 'bot',
        content: "Welcome! Let's set up your email outreach. First, what do you sell?",
        inputType: 'text',
        action: 'what_you_sell',
    },
    {
        id: 2,
        type: 'bot',
        content: "Great! What industry are your ideal customers in?",
        inputType: 'text',
        action: 'target_industry',
    },
    {
        id: 3,
        type: 'bot',
        content: "What role or job title are you targeting? (e.g., CEO, Marketing Manager)",
        inputType: 'text',
        action: 'target_role',
    },
    {
        id: 4,
        type: 'bot',
        content: "What region are you focusing on?",
        inputType: 'text',
        action: 'target_region',
    },
    {
        id: 5,
        type: 'bot',
        content: "What's your offer? What do you want prospects to do?",
        inputType: 'select',
        options: [
            { value: 'demo', label: '📅 Book a Demo' },
            { value: 'audit', label: '🔍 Free Audit' },
            { value: 'call', label: '📞 Discovery Call' },
        ],
        action: 'offer_type',
    },
    {
        id: 6,
        type: 'bot',
        content: "Choose your safety preference. This controls how cautiously we send emails:",
        inputType: 'select',
        options: [
            { value: 'LOW', label: '🟢 Low - Faster sending (more risk)' },
            { value: 'MEDIUM', label: '🟡 Medium - Balanced (recommended)' },
            { value: 'HIGH', label: '🔴 High - Very cautious (slower)' },
        ],
        action: 'safety_preference',
    },
    {
        id: 7,
        type: 'bot',
        content: "Do you already have a list of leads to reach out to?",
        inputType: 'select',
        options: [
            { value: 'YES', label: '✅ Yes, I have leads' },
            { value: 'NO', label: '❌ No, I need to find leads' },
        ],
        action: 'has_leads',
    },
    {
        id: 8,
        type: 'bot',
        content: "Perfect! Now let's connect your Gmail inbox. Click below to authorize:",
        inputType: 'button',
        action: 'connect_gmail',
    },
];

export default function WizardPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const [token, setToken] = useState<string | null>(null);
    const [workspaceId, setWorkspaceId] = useState<number | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [currentStep, setCurrentStep] = useState(0);
    const [inputValue, setInputValue] = useState('');
    const [setupData, setSetupData] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const init = async () => {
            console.log('DEBUG: Wizard init started');
            const storedToken = localStorage.getItem('token');
            if (!storedToken) {
                console.log('DEBUG: No token found, redirecting');
                router.push('/');
                return;
            }
            setToken(storedToken);

            try {
                // Check if user has workspaces
                console.log('DEBUG: Fetching workspaces...');
                const userWorkspaces = await workspaces.list(storedToken);
                console.log('DEBUG: Found workspaces:', userWorkspaces.length);

                if (userWorkspaces.length > 0) {
                    const wsId = userWorkspaces[0].id;
                    console.log('DEBUG: Using existing workspace:', wsId);
                    setWorkspaceId(wsId);
                } else {
                    // Create workspace
                    console.log('DEBUG: Creating new workspace...');
                    const newWorkspace = await workspaces.create(storedToken, 'My Workspace');
                    console.log('DEBUG: Created workspace:', newWorkspace.id);
                    setWorkspaceId(newWorkspace.id);
                }
            } catch (err: any) {
                console.error('DEBUG: Error in wizard init:', err);
                alert(`Initialization failed: ${err.message || 'Check your connection'}`);
            }
            setLoading(false);
            console.log('DEBUG: Wizard init finished, loading=false');
        };

        init();
    }, [router]);

    // Handle OAuth callback
    useEffect(() => {
        const step = searchParams.get('step');
        const email = searchParams.get('email');
        const error = searchParams.get('error');

        console.log('DEBUG: URL SearchParams:', { step, email, error });

        if (step === 'inbox-connected' && email) {
            console.log('DEBUG: OAuth Success callback detected');
            setMessages(prev => [
                ...prev,
                { id: Date.now(), type: 'bot', content: `✅ Successfully connected ${email}! Your inbox is ready.` },
                { id: Date.now() + 1, type: 'bot', content: "Setup complete! Let's go to your dashboard to start your first campaign.", inputType: 'button', action: 'go_dashboard' },
            ]);
        } else if (step === 'inbox-error') {
            console.log('DEBUG: OAuth Error callback detected:', error);
            setMessages(prev => [
                ...prev,
                { id: Date.now(), type: 'bot', content: `❌ Error connecting email: ${error || 'Unknown error'}. Please try again.` },
                { id: Date.now() + 1, type: 'bot', content: "Try connecting again:", inputType: 'button', action: 'connect_gmail' },
            ]);
        }
    }, [searchParams]);

    // Add initial message
    useEffect(() => {
        if (!loading && messages.length === 0 && currentStep === 0) {
            console.log('DEBUG: Adding first message');
            setMessages([WIZARD_STEPS[0]]);
        }
    }, [loading, messages.length, currentStep]);

    // Scroll to bottom on new message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleUserInput = async (value: string, action?: string, displayValue?: string) => {
        if (!action) return;
        console.log(`DEBUG: [WIZARD] Action=${action}, Value=${value}`);

        // Add user message
        setMessages(prev => [
            ...prev,
            { id: Date.now(), type: 'user', content: displayValue || value },
        ]);

        // Update setup data
        const newSetupData = { ...setupData, [action]: value };
        setSetupData(newSetupData);

        // Handle special actions
        if (action === 'connect_gmail') {
            console.log('DEBUG: [WIZARD] Final step - Connecting Gmail...');

            if (!token || !workspaceId) {
                const msg = `Configuration Error: ${!token ? 'Missing authentication token' : 'Workspace ID not found'}. Please refresh and try again.`;
                console.error(msg);
                alert(msg);
                return;
            }

            try {
                // Fix: Only send fields that the backend expects (WorkspaceSetup schema)
                // Filter out 'connect_gmail' and any other internal UI keys
                const payload = {
                    what_you_sell: newSetupData.what_you_sell || '',
                    target_industry: newSetupData.target_industry || '',
                    target_role: newSetupData.target_role || '',
                    target_region: newSetupData.target_region || '',
                    offer_type: newSetupData.offer_type || '',
                    safety_preference: (newSetupData.safety_preference || 'MEDIUM').toUpperCase(),
                    has_leads: String(newSetupData.has_leads).toUpperCase() === 'YES',
                    meeting_days: [],
                    meeting_time_start: "09:00",
                    meeting_time_end: "17:00"
                };

                console.log('DEBUG: [WIZARD] Saving setup with payload:', payload);
                await workspaces.updateSetup(token, workspaceId, payload);
                console.log('DEBUG: [WIZARD] Setup saved successfully.');

                console.log('DEBUG: [WIZARD] Fetching OAuth URL...');
                const resp = await mailboxes.getOAuthUrl(token, workspaceId);
                console.log('DEBUG: [WIZARD] Authentication URL received:', resp.auth_url);

                if (!resp.auth_url) {
                    throw new Error('The server returned an empty authorization URL. Please contact support.');
                }

                console.log('DEBUG: [WIZARD] REDIRECTING USER TO GOOGLE...');
                window.location.href = resp.auth_url;
                return;
            } catch (err: any) {
                console.error('DEBUG: [WIZARD] Critical failure in setup flow:', err);
                alert(`Wizard error: ${err.message || 'The server encounterd an error while preparing your connection. Please check your internet and try again.'}`);
            }
        }

        if (action === 'go_dashboard') {
            console.log('DEBUG: Redirecting to dashboard');
            router.push('/dashboard');
            return;
        }

        // Move to next step
        const nextStep = currentStep + 1;
        if (nextStep < WIZARD_STEPS.length) {
            console.log('DEBUG: Advancing to step:', nextStep);
            setCurrentStep(nextStep);
            setTimeout(() => {
                setMessages(prev => [...prev, WIZARD_STEPS[nextStep]]);
            }, 500);
        } else {
            console.log('DEBUG: No more steps, awaiting logic');
        }

        setInputValue('');
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        const currentMessage = messages[messages.length - 1];
        if (currentMessage.action) {
            handleUserInput(inputValue, currentMessage.action);
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
                <div className="animate-pulse">Loading...</div>
            </div>
        );
    }

    const currentMessage = messages[messages.length - 1];

    return (
        <div className="chat-container">
            {/* Header */}
            <div style={{
                padding: '16px 24px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
            }}>
                <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'var(--gradient-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                    🤖
                </div>
                <div>
                    <div style={{ fontWeight: '600' }}>Setup Assistant</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                        Step {Math.min(currentStep + 1, WIZARD_STEPS.length)} of {WIZARD_STEPS.length}
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="progress-bar" style={{ borderRadius: 0 }}>
                <div
                    className="progress-fill"
                    style={{
                        width: `${((currentStep + 1) / WIZARD_STEPS.length) * 100}%`,
                        borderRadius: 0,
                    }}
                />
            </div>

            {/* Messages */}
            <div className="chat-messages">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`chat-message ${msg.type}`}
                    >
                        {msg.content}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="chat-input-area">
                {currentMessage?.inputType === 'select' && currentMessage.options && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {currentMessage.options.map((opt) => (
                            <button
                                key={opt.value}
                                className="btn btn-secondary"
                                onClick={() => handleUserInput(opt.value, currentMessage.action, opt.label)}
                                style={{ justifyContent: 'flex-start' }}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                )}

                {currentMessage?.inputType === 'button' && (
                    <button
                        className="btn btn-primary"
                        onClick={() => handleUserInput('Connect Gmail', currentMessage.action)}
                        style={{ width: '100%' }}
                    >
                        {currentMessage.action === 'connect_gmail' ? '🔗 Connect Gmail' : '→ Go to Dashboard'}
                    </button>
                )}

                {currentMessage?.inputType === 'text' && (
                    <form onSubmit={handleSubmit} className="chat-input-form">
                        <input
                            type="text"
                            className="input"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Type your answer..."
                            autoFocus
                        />
                        <button type="submit" className="btn btn-primary">
                            Send
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
