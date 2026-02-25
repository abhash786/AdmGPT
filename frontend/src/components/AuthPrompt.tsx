import React, { useState } from 'react';
import { ExternalLink, Key, Loader2, CheckCircle } from 'lucide-react';
import { user } from '../services/api';

interface AuthPromptProps {
    serverName: string;
    authUrl: string;
    instructions: string;
    targetEnvVar: string;
    authType?: 'browser' | 'oauth';
    buttonText?: string;
}

const AuthPrompt: React.FC<AuthPromptProps> = ({
    serverName, authUrl, instructions, targetEnvVar, authType = 'browser', buttonText
}) => {
    const [token, setToken] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const userName = localStorage.getItem('userName') || 'unknown';

    const handleOAuthClick = () => {
        // Construct full URL using api helper
        const loginUrl = user.getOAuthLoginUrl(serverName, userName);
        const popup = window.open(loginUrl, 'mcp-auth-popup', 'width=600,height=700');

        const messageHandler = (event: MessageEvent) => {
            // In production, we should check event.origin for security
            if (event.data === 'oauth-success') {
                setIsSuccess(true);
                window.removeEventListener('message', messageHandler);
            }
        };

        window.addEventListener('message', messageHandler);

        // Clean up listener if popup is closed manually without success
        const timer = setInterval(() => {
            if (popup?.closed) {
                clearInterval(timer);
                window.removeEventListener('message', messageHandler);
            }
        }, 1000);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token.trim()) return;

        setIsSubmitting(true);
        setError(null);
        try {
            await user.submitMCPAuth(serverName, token.trim(), targetEnvVar);
            setIsSuccess(true);
        } catch (err: any) {
            console.error('Failed to submit auth token', err);
            setError('Failed to save token. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (isSuccess) {
        return (
            <div className="flex flex-col items-center gap-3 p-6 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-200/60 dark:border-emerald-800/40 animate-fade-in">
                <CheckCircle className="text-emerald-500 w-8 h-8" />
                <div className="text-center">
                    <p className="font-semibold text-emerald-700 dark:text-emerald-300">Authenticated Successfully!</p>
                    <p className="text-sm text-emerald-600/80 dark:text-emerald-400/80 mt-1">
                        Your connection to {serverName} is now active. You can retry your request.
                    </p>
                </div>
            </div>
        );
    }

    if (authType === 'oauth') {
        return (
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden animate-fade-in">
                <div className="p-4 bg-accent-50/50 dark:bg-accent-900/10 border-b border-gray-200 dark:border-gray-800 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                        <Key className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                    </div>
                    <div>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Authentication Required</h4>
                        <p className="text-[11px] text-gray-500 uppercase tracking-wider">{serverName} Integration</p>
                    </div>
                </div>

                <div className="p-5 space-y-4 text-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                        {instructions}
                    </p>

                    <button
                        onClick={handleOAuthClick}
                        className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-gradient-accent text-white font-semibold rounded-xl shadow-lg hover:shadow-glow transition-all duration-200 group"
                    >
                        <span>{buttonText || `Connect to ${serverName}`}</span>
                        <ExternalLink size={16} />
                    </button>

                    <p className="text-[11px] text-gray-400 dark:text-gray-500">
                        A secure login window will open for you to authorize this access.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden animate-fade-in">
            <div className="p-4 bg-accent-50/50 dark:bg-accent-900/10 border-b border-gray-200 dark:border-gray-800 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                    <Key className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                </div>
                <div>
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Authentication Required</h4>
                    <p className="text-[11px] text-gray-500 uppercase tracking-wider">{serverName} Integration</p>
                </div>
            </div>

            <div className="p-5 space-y-4">
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    {instructions}
                </p>

                <a
                    href={authUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl border-2 border-accent-200 dark:border-accent-800/50 text-accent-600 dark:text-accent-400 font-medium hover:bg-accent-50 dark:hover:bg-accent-900/20 transition-all duration-200 group"
                >
                    <span>Open {serverName} Auth Page</span>
                    <ExternalLink size={14} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </a>

                <form onSubmit={handleSubmit} className="space-y-3 pt-2">
                    <div className="space-y-1.5">
                        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 ml-1">
                            Paste Token
                        </label>
                        <input
                            type="password"
                            value={token}
                            onChange={(e) => setToken(e.target.value)}
                            placeholder={`Paste your ${serverName} token here...`}
                            className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-500 transition-all"
                            disabled={isSubmitting}
                            autoFocus
                        />
                    </div>

                    {error && (
                        <p className="text-xs text-red-500 font-medium ml-1">
                            {error}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={isSubmitting || !token.trim()}
                        className="w-full py-3 px-4 bg-gradient-accent text-white font-semibold rounded-xl shadow-lg hover:shadow-glow transition-all duration-200 disabled:opacity-50 disabled:shadow-none flex items-center justify-center gap-2"
                    >
                        {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : 'Complete Setup'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default AuthPrompt;
