import { useState } from 'react';
import type { ConversationSummary } from '../types';
import { MessageSquare, Plus, PanelLeftClose, PanelLeftOpen, LogOut, User, Settings, Trash2 } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import clsx from 'clsx';

interface SidebarProps {
    conversations: ConversationSummary[];
    currentId?: string;
    onSelect: (id: string) => void;
    onNewChat: () => void;
    user?: { name: string };
    onLogout: () => void;
    onOpenSettings: () => void;
    onDelete: (id: string) => void;
}

const Sidebar = ({ conversations, currentId, onSelect, onNewChat, user, onLogout, onOpenSettings, onDelete }: SidebarProps) => {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <div
            className={clsx(
                "flex flex-col h-full transition-all duration-300 ease-out",
                "bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl",
                "border-r border-gray-200/60 dark:border-gray-800/60",
                isCollapsed ? "w-[68px]" : "w-72"
            )}
        >
            {/* Header */}
            <div className="p-3 flex items-center gap-2">
                {!isCollapsed && (
                    <button
                        onClick={onNewChat}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 btn-accent rounded-xl text-sm"
                    >
                        <Plus size={16} strokeWidth={2.5} /> New Chat
                    </button>
                )}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-2.5 rounded-xl hover:bg-gray-200/80 dark:hover:bg-gray-800/60 transition-all duration-200 text-gray-500 dark:text-gray-400 shrink-0"
                >
                    {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
                </button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
                {conversations.map((conv) => (
                    <div
                        key={conv.id}
                        className={clsx(
                            "w-full flex items-center justify-between rounded-xl transition-all duration-200 group cursor-pointer",
                            conv.id === currentId
                                ? "bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300"
                                : "hover:bg-gray-100/80 dark:hover:bg-gray-800/40 text-gray-700 dark:text-gray-300"
                        )}
                        title={conv.title}
                    >
                        <button
                            onClick={() => onSelect(conv.id)}
                            className="flex items-center gap-3 flex-1 truncate text-left px-3 py-2.5"
                        >
                            {/* Active indicator */}
                            <div className={clsx(
                                "w-1 h-5 rounded-full shrink-0 transition-all duration-200",
                                conv.id === currentId
                                    ? "bg-gradient-accent opacity-100"
                                    : "opacity-0"
                            )} />
                            <MessageSquare size={16} className={clsx(
                                "shrink-0 transition-colors",
                                conv.id === currentId ? "text-accent-500" : "text-gray-400 dark:text-gray-500"
                            )} />
                            {!isCollapsed && <span className="truncate text-sm font-medium">{conv.title}</span>}
                        </button>
                        {!isCollapsed && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDelete(conv.id);
                                }}
                                className="p-1.5 mr-2 rounded-lg hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 opacity-0 group-hover:opacity-100 transition-all duration-200"
                                title="Delete Conversation"
                            >
                                <Trash2 size={14} />
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-gray-200/60 dark:border-gray-800/60">
                {!isCollapsed && user && (
                    <div className="mb-3 px-3 py-2 flex items-center gap-2.5 rounded-xl bg-gray-100/60 dark:bg-gray-800/40">
                        <div className="w-7 h-7 rounded-full bg-gradient-accent flex items-center justify-center text-white text-xs font-bold shrink-0">
                            {user.name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{user.name}</span>
                    </div>
                )}
                <div className={clsx("flex items-center gap-1", isCollapsed ? "flex-col" : "justify-between")}>
                    <ThemeToggle />
                    <button
                        onClick={onOpenSettings}
                        className="p-2 rounded-xl hover:bg-gray-200/80 dark:hover:bg-gray-800/60 transition-all duration-200 text-gray-500 dark:text-gray-400"
                        title="Settings"
                    >
                        <Settings size={18} />
                    </button>
                    <button
                        onClick={onLogout}
                        className="p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500 dark:hover:text-red-400 transition-all duration-200 text-gray-500 dark:text-gray-400"
                        title="Logout"
                    >
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
