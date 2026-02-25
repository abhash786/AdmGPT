import React, { useState } from 'react';
import { auth, setAuthToken } from '../services/api';
import { Loader2, Rocket } from 'lucide-react';

interface LoginProps {
    onLogin: (token: string, userName: string) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
    const [userName, setUserName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const data = await auth.login(userName);
            setAuthToken(data.access_token);
            onLogin(data.access_token, data.user_name);
        } catch (err) {
            setError('Login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative flex flex-col items-center justify-center min-h-screen p-4 overflow-hidden bg-gray-50 dark:bg-gray-950">
            {/* Gradient mesh background */}
            <div className="absolute inset-0 bg-gradient-mesh dark:bg-gradient-mesh-dark pointer-events-none" />
            <div className="absolute top-1/4 left-1/3 w-72 h-72 bg-accent-400/10 dark:bg-accent-500/5 rounded-full blur-3xl animate-float pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-400/10 dark:bg-purple-500/5 rounded-full blur-3xl animate-float pointer-events-none" style={{ animationDelay: '1.5s' }} />

            {/* Login card */}
            <div className="relative z-10 w-full max-w-md animate-scale-in">
                {/* Branding */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-accent shadow-glow mb-4">
                        <Rocket className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-gradient mb-1">Antigravity AI</h1>
                    <p className="text-gray-500 dark:text-gray-400 text-sm">Your intelligent assistant, ready to defy limits.</p>
                </div>

                {/* Card */}
                <div className="glass-card rounded-2xl shadow-glass dark:shadow-glass-dark p-8">
                    <h2 className="text-xl font-semibold mb-6 text-gray-900 dark:text-white text-center">Welcome Back</h2>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-400">
                                Your Name
                            </label>
                            <input
                                id="username"
                                type="text"
                                value={userName}
                                onChange={(e) => setUserName(e.target.value)}
                                required
                                className="w-full px-4 py-3 input-base"
                                placeholder="Enter your name"
                            />
                        </div>
                        {error && (
                            <p className="text-red-500 dark:text-red-400 text-sm bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">
                                {error}
                            </p>
                        )}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 px-4 btn-accent text-base flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:scale-100"
                        >
                            {loading ? <Loader2 className="animate-spin w-5 h-5" /> : 'Start Chatting'}
                        </button>
                    </form>
                </div>

                <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-6">
                    Powered by advanced AI models
                </p>
            </div>
        </div>
    );
};

export default Login;
