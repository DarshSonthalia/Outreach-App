import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Email Outreach Platform',
    description: 'Safety-first email outreach with Gmail integration',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
