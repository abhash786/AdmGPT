import { useEffect, useState } from 'react';
import { user } from '../services/api';
import type { MCPServerInfo } from '../types';
import { Save, Server, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';

const IntegrationsSettings = () => {
    const [servers, setServers] = useState<MCPServerInfo[]>([]);
    const [userConfigs, setUserConfigs] = useState<Record<string, Record<string, string>>>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [serversData, configsData] = await Promise.all([
                    user.getMCPServers(),
                    user.getUserMCPConfigs()
                ]);
                setServers(serversData);
                setUserConfigs(configsData);
            } catch (error) {
                console.error("Failed to load integrations data", error);
                setMessage({ type: 'error', text: "Failed to load integrations data." });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleConfigChange = (serverName: string, key: string, value: string) => {
        setUserConfigs(prev => ({
            ...prev,
            [serverName]: {
                ...(prev[serverName] || {}),
                [key]: value
            }
        }));
    };

    const toggleVisibility = (serverName: string, envVar: string) => {
        const id = `${serverName}:${envVar}`;
        setVisibleFields(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const handleSave = async (serverName: string) => {
        setSaving(serverName);
        setMessage(null);
        try {
            const config = userConfigs[serverName] || {};
            await user.updateUserMCPConfig({
                server_name: serverName,
                env_vars: config
            });
            setMessage({ type: 'success', text: `Configuration for ${serverName} saved successfully.` });
        } catch (error) {
            console.error(`Failed to save config for ${serverName}`, error);
            setMessage({ type: 'error', text: `Failed to save configuration for ${serverName}.` });
        } finally {
            setSaving(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="w-6 h-6 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-5">
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-accent-100 dark:bg-accent-900/30 flex items-center justify-center">
                    <Server className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                </div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">MCP Integrations</h3>
            </div>

            {message && (
                <div className={`p-3 rounded-xl flex items-center gap-2.5 text-sm ${message.type === 'success'
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40'
                        : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 border border-red-200/60 dark:border-red-800/40'
                    }`}>
                    {message.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                    {message.text}
                </div>
            )}

            <div className="space-y-3">
                {servers.map(server => (
                    <div key={server.name} className="glass-surface rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                                {server.name}
                                {server.required_env.length === 0 && (
                                    <span className="text-[10px] font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-200/60 dark:border-emerald-800/40">
                                        Ready
                                    </span>
                                )}
                            </h4>
                            {server.required_env.length > 0 && (
                                <button
                                    onClick={() => handleSave(server.name)}
                                    disabled={saving === server.name}
                                    className="flex items-center gap-1.5 px-3 py-1.5 btn-accent text-xs rounded-lg disabled:opacity-50"
                                >
                                    <Save size={12} />
                                    {saving === server.name ? 'Saving...' : 'Save'}
                                </button>
                            )}
                        </div>

                        {server.required_env.length > 0 ? (
                            <div className="space-y-3">
                                <p className="text-xs text-gray-400 dark:text-gray-500">
                                    Configure the following environment variables:
                                </p>
                                {server.required_env.map(envVar => {
                                    const isVisible = visibleFields.has(`${server.name}:${envVar}`);
                                    return (
                                        <div key={envVar} className="space-y-1.5">
                                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">
                                                {envVar}
                                            </label>
                                            <div className="relative">
                                                <input
                                                    type={isVisible ? "text" : "password"}
                                                    value={userConfigs[server.name]?.[envVar] || ''}
                                                    onChange={(e) => handleConfigChange(server.name, envVar, e.target.value)}
                                                    className="w-full px-3.5 py-2.5 pr-10 text-sm input-base"
                                                    placeholder={`Enter ${envVar}`}
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => toggleVisibility(server.name, envVar)}
                                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                                    title={isVisible ? "Hide" : "Show"}
                                                >
                                                    {isVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-sm text-gray-400 dark:text-gray-500">
                                This integration works out of the box.
                            </p>
                        )}
                    </div>
                ))}

                {servers.length === 0 && (
                    <div className="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
                        No MCP servers found. Check backend configuration.
                    </div>
                )}
            </div>
        </div>
    );
};

export default IntegrationsSettings;
