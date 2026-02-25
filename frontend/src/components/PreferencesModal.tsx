import { useState, useEffect } from 'react';
import { X, Type, Cpu, Server, Save, Eye, EyeOff, CheckCircle, AlertCircle, FileText } from 'lucide-react';
import { user } from '../services/api';
import type { MCPServerInfo } from '../types';

interface PreferencesModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (model: string, fontFamily: string, fontSize: string) => void;
    currentModel?: string;
    currentFontFamily?: string;
    currentFontSize?: string;
}

const MODELS = [
    { id: 'gpt-4o', name: 'GPT-4o' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
    { id: 'claude-3-opus', name: 'Claude 3 Opus' },
    { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet' },
];

const FONTS = [
    { id: 'Inter', name: 'Inter (Default)' },
    { id: 'Poppins', name: 'Poppins' },
    { id: 'Outfit', name: 'Outfit' },
    { id: 'Source Sans 3', name: 'Source Sans 3' },
    { id: 'DM Sans', name: 'DM Sans' },
    { id: 'Nunito', name: 'Nunito' },
    { id: 'Roboto', name: 'Roboto' },
    { id: 'Lato', name: 'Lato' },
    { id: 'JetBrains Mono', name: 'JetBrains Mono' },
    { id: 'Georgia', name: 'Georgia (Serif)' },
];

const SIZES = [
    { id: 'text-xs', name: 'Extra Small' },
    { id: 'text-sm', name: 'Small' },
    { id: 'text-base', name: 'Medium (Default)' },
    { id: 'text-lg', name: 'Large' },
    { id: 'text-xl', name: 'Extra Large' },
];

// ─── General Settings Page ───────────────────────────────────
const GeneralPage = ({ currentModel, currentFontFamily, currentFontSize, onSave, onClose }: {
    currentModel: string;
    currentFontFamily: string;
    currentFontSize: string;
    onSave: (model: string, fontFamily: string, fontSize: string) => void;
    onClose: () => void;
}) => {
    const [model, setModel] = useState(currentModel);
    const [fontFamily, setFontFamily] = useState(currentFontFamily);
    const [fontSize, setFontSize] = useState(currentFontSize);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        setModel(currentModel);
        setFontFamily(currentFontFamily);
        setFontSize(currentFontSize);
    }, [currentModel, currentFontFamily, currentFontSize]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await user.updatePreferences({ model, fontFamily, fontSize });
            onSave(model, fontFamily, fontSize);
            onClose();
        } catch (error) {
            console.error("Failed to save preferences", error);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* AI Model */}
                <div className="space-y-2.5">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                        <Cpu size={15} /> AI Model
                    </label>
                    <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full px-3.5 py-2.5 input-base">
                        {MODELS.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                    <p className="text-xs text-gray-400 dark:text-gray-500">Choose the AI model that powers your chat experience.</p>
                </div>

                <hr className="border-gray-200/60 dark:border-gray-700/40" />

                {/* Appearance */}
                <div className="space-y-4">
                    <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Appearance</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                                <Type size={15} /> Font Family
                            </label>
                            <select value={fontFamily} onChange={(e) => setFontFamily(e.target.value)} className="w-full px-3.5 py-2.5 input-base">
                                {FONTS.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                                <Type size={15} /> Font Size
                            </label>
                            <select value={fontSize} onChange={(e) => setFontSize(e.target.value)} className="w-full px-3.5 py-2.5 input-base">
                                {SIZES.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200/60 dark:border-gray-700/40 flex justify-end gap-3 bg-gray-50/50 dark:bg-gray-900/30">
                <button onClick={onClose} className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 rounded-xl transition-all duration-200">
                    Cancel
                </button>
                <button onClick={handleSave} disabled={saving} className="px-5 py-2.5 text-sm btn-accent disabled:opacity-50 flex items-center gap-2">
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
};

// ─── Tool Settings Page ──────────────────────────────────────
const ToolPage = ({ server, configs, toolContext, onClose }: {
    server: MCPServerInfo;
    configs: Record<string, string>;
    toolContext: string;
    onClose: () => void;
}) => {
    const [envVars, setEnvVars] = useState<Record<string, string>>(configs);
    const [context, setContext] = useState(toolContext);
    const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        setEnvVars(configs);
        setContext(toolContext);
    }, [configs, toolContext]);

    const toggleVisibility = (envVar: string) => {
        setVisibleFields(prev => {
            const next = new Set(prev);
            next.has(envVar) ? next.delete(envVar) : next.add(envVar);
            return next;
        });
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage(null);
        try {
            await user.updateUserMCPConfig({
                server_name: server.name,
                env_vars: envVars,
                tool_context: context || undefined,
            });
            setMessage({ type: 'success', text: 'Configuration saved successfully.' });
        } catch (error) {
            console.error(`Failed to save config for ${server.name}`, error);
            setMessage({ type: 'error', text: 'Failed to save configuration.' });
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                        <Server className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">{server.name}</h3>
                        {server.required_env.length === 0 && (
                            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">No credentials required</span>
                        )}
                    </div>
                </div>

                {/* Status message */}
                {message && (
                    <div className={`p-3 rounded-xl flex items-center gap-2.5 text-sm ${message.type === 'success'
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40'
                            : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 border border-red-200/60 dark:border-red-800/40'
                        }`}>
                        {message.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                        {message.text}
                    </div>
                )}

                {/* Environment Variables */}
                {server.required_env.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Credentials</h4>
                        {server.required_env.map(envVar => {
                            const isVisible = visibleFields.has(envVar);
                            return (
                                <div key={envVar} className="space-y-1.5">
                                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">{envVar}</label>
                                    <div className="relative">
                                        <input
                                            type={isVisible ? "text" : "password"}
                                            value={envVars[envVar] || ''}
                                            onChange={(e) => setEnvVars(prev => ({ ...prev, [envVar]: e.target.value }))}
                                            className="w-full px-3.5 py-2.5 pr-10 text-sm input-base"
                                            placeholder={`Enter ${envVar}`}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => toggleVisibility(envVar)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                        >
                                            {isVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Divider */}
                {server.required_env.length > 0 && <hr className="border-gray-200/60 dark:border-gray-700/40" />}

                {/* Additional Context */}
                <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                        <FileText size={15} className="text-gray-500 dark:text-gray-400" />
                        <h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Additional Context</h4>
                    </div>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                        Provide any additional instructions or context for the AI when using this tool. This will be sent with every request.
                    </p>
                    <textarea
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        rows={5}
                        className="w-full px-3.5 py-2.5 text-sm input-base resize-y min-h-[100px]"
                        placeholder={`e.g., "The default project is MyProject. Always use the main branch unless specified."`}
                    />
                </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200/60 dark:border-gray-700/40 flex justify-end gap-3 bg-gray-50/50 dark:bg-gray-900/30">
                <button onClick={onClose} className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 rounded-xl transition-all duration-200">
                    Cancel
                </button>
                <button onClick={handleSave} disabled={saving} className="px-5 py-2.5 text-sm btn-accent disabled:opacity-50 flex items-center gap-2">
                    <Save size={14} />
                    {saving ? 'Saving...' : 'Save Config'}
                </button>
            </div>
        </div>
    );
};

// ─── Main Modal ──────────────────────────────────────────────
const PreferencesModal = ({ isOpen, onClose, onSave, currentModel, currentFontFamily, currentFontSize }: PreferencesModalProps) => {
    const [activePage, setActivePage] = useState<string>('general');
    const [servers, setServers] = useState<MCPServerInfo[]>([]);
    const [userConfigs, setUserConfigs] = useState<Record<string, Record<string, string>>>({});
    const [toolContexts, setToolContexts] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            setActivePage('general');
            setLoading(true);
            const fetchData = async () => {
                try {
                    const [serversData, configsData, contextsData] = await Promise.all([
                        user.getMCPServers(),
                        user.getUserMCPConfigs(),
                        user.getToolContexts(),
                    ]);
                    setServers(serversData);
                    setUserConfigs(configsData);
                    setToolContexts(contextsData);
                } catch (error) {
                    console.error("Failed to load settings data", error);
                } finally {
                    setLoading(false);
                }
            };
            fetchData();
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const navItems = [
        { id: 'general', label: 'General', icon: Cpu },
        ...servers.map(s => ({ id: s.name, label: s.name, icon: Server })),
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
            <div className="w-full max-w-3xl h-[85vh] max-h-[700px] glass-card rounded-2xl shadow-2xl flex overflow-hidden animate-scale-in">

                {/* Left Sidebar */}
                <div className="w-52 shrink-0 bg-gray-50/80 dark:bg-gray-900/50 border-r border-gray-200/60 dark:border-gray-700/40 flex flex-col">
                    {/* Sidebar Header */}
                    <div className="px-5 py-5 border-b border-gray-200/60 dark:border-gray-700/40">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Settings</h2>
                    </div>

                    {/* Nav Items */}
                    <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
                        {loading ? (
                            <div className="flex items-center justify-center py-8">
                                <div className="w-5 h-5 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
                            </div>
                        ) : (
                            navItems.map(item => (
                                <button
                                    key={item.id}
                                    onClick={() => setActivePage(item.id)}
                                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 text-left ${activePage === item.id
                                            ? 'bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300'
                                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100/80 dark:hover:bg-gray-800/40'
                                        }`}
                                >
                                    <item.icon size={15} className={activePage === item.id ? 'text-accent-500' : 'text-gray-400 dark:text-gray-500'} />
                                    <span className="truncate">{item.label}</span>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Right Content */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Content Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200/60 dark:border-gray-700/40">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                            {activePage === 'general' ? 'General Settings' : activePage}
                        </h3>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800/60 transition-all duration-200 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {/* Page Content */}
                    {loading ? (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="w-6 h-6 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
                        </div>
                    ) : activePage === 'general' ? (
                        <GeneralPage
                            currentModel={currentModel || 'gpt-4o'}
                            currentFontFamily={currentFontFamily || 'Inter'}
                            currentFontSize={currentFontSize || 'Medium'}
                            onSave={onSave}
                            onClose={onClose}
                        />
                    ) : (
                        (() => {
                            const server = servers.find(s => s.name === activePage);
                            if (!server) return <div className="flex-1 flex items-center justify-center text-gray-400">Server not found</div>;
                            return (
                                <ToolPage
                                    server={server}
                                    configs={userConfigs[server.name] || {}}
                                    toolContext={toolContexts[server.name] || ''}
                                    onClose={onClose}
                                />
                            );
                        })()
                    )}
                </div>
            </div>
        </div>
    );
};

export default PreferencesModal;
