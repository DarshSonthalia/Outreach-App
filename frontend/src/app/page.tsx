'use client';

import { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { auth } from '@/lib/api';

export default function HomePage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isLogin) {
                const { access_token } = await auth.login(email, password);
                localStorage.setItem('token', access_token);
                router.push('/dashboard');
            } else {
                await auth.register(email, password);
                const { access_token } = await auth.login(email, password);
                localStorage.setItem('token', access_token);
                router.push('/wizard');
            }
        } catch (err: any) {
            setError(err.message || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%)',
        }}>
            <div style={{
                width: '100%',
                maxWidth: '420px',
                padding: '0 24px',
            }}>
                {/* Logo/Brand */}
                <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                    <Image
                        src="/intently-logo.png"
                        alt="intently-ai logo"
                        width={64}
                        height={64}
                        priority
                        style={{ margin: '0 auto 16px', borderRadius: '12px' }}
                    />
                    <h1 style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        background: 'linear-gradient(135deg, #ffffff 0%, #a0a0b0 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}>
                        Email Outreach
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
                        Safety-first email campaigns
                    </p>
                </div>

                {/* Auth Card */}
                <div className="card" style={{ background: 'rgba(22, 22, 31, 0.8)', backdropFilter: 'blur(10px)' }}>
                    {/* Tabs */}
                    <div style={{
                        display: 'flex',
                        gap: '8px',
                        marginBottom: '24px',
                        padding: '4px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                    }}>
                        <button
                            onClick={() => setIsLogin(true)}
                            style={{
                                flex: 1,
                                padding: '10px',
                                border: 'none',
                                borderRadius: 'var(--radius-sm)',
                                background: isLogin ? 'var(--bg-card)' : 'transparent',
                                color: isLogin ? 'var(--text-primary)' : 'var(--text-muted)',
                                fontWeight: '500',
                            }}
                        >
                            Sign In
                        </button>
                        <button
                            onClick={() => setIsLogin(false)}
                            style={{
                                flex: 1,
                                padding: '10px',
                                border: 'none',
                                borderRadius: 'var(--radius-sm)',
                                background: !isLogin ? 'var(--bg-card)' : 'transparent',
                                color: !isLogin ? 'var(--text-primary)' : 'var(--text-muted)',
                                fontWeight: '500',
                            }}
                        >
                            Sign Up
                        </button>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '16px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                marginBottom: '6px',
                            }}>
                                Email
                            </label>
                            <input
                                type="email"
                                className="input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@company.com"
                                required
                            />
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                marginBottom: '6px',
                            }}>
                                Password
                            </label>
                            <input
                                type="password"
                                className="input"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        {error && (
                            <div className="alert alert-danger" style={{ marginBottom: '16px' }}>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                            style={{ width: '100%' }}
                        >
                            {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
                        </button>
                    </form>
                </div>

                <p style={{
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                    marginTop: '24px',
                }}>
                    Built with safety-first principles
                </p>
            </div>
        </div>
    );
}
