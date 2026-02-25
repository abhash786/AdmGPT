import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';
import { Bot, User, ChevronDown, Target, ClipboardList, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

interface MessageBubbleProps {
    message: Message;
}

import ChartRenderer from './ChartRenderer';
import AuthPrompt from './AuthPrompt';

const MessageBubble: React.FC<MessageBubbleProps> = React.memo(({ message }) => {
    const isUser = message.role === 'user';
    const isThought = message.role === 'thought' || message.type === 'thought';
    const isAuth = message.role === 'auth_required' || message.type === 'auth_required';
    const isIntent = message.role === 'intent' || message.type === 'intent';
    const isPlan = message.role === 'plan' || message.type === 'plan';
    const isError = message.role === 'error' || message.type === 'error';
    const [isExpanded, setIsExpanded] = React.useState(isIntent || isPlan || isError);

    if (isAuth && message.auth_config) {
        return (
            <div className="flex w-full mb-6 justify-start animate-fade-in pl-11">
                <div className="max-w-[90%] md:max-w-[600px] w-full">
                    <AuthPrompt
                        serverName={message.auth_config.server_name}
                        authUrl={message.auth_config.auth_url || ''}
                        instructions={message.auth_config.instructions}
                        targetEnvVar={message.auth_config.target_env_var || ''}
                        authType={message.auth_config.type}
                        buttonText={message.auth_config.button_text}
                    />
                </div>
            </div>
        );
    }

    if (isThought || isIntent || isPlan || isError) {
        const title = isIntent ? 'Intent Analysis' : isPlan ? 'Technical Plan' : isError ? 'Tool Execution Failed' : 'Thinking';
        const Icon = isIntent ? Target : isPlan ? ClipboardList : isError ? AlertCircle : ChevronDown;

        const colorClass = isIntent ? "text-blue-500" :
            isPlan ? "text-purple-500" :
                isError ? "text-red-500" :
                    "text-accent-500";

        const bgClass = isIntent ? "bg-blue-100 dark:bg-blue-900/30" :
            isPlan ? "bg-purple-100 dark:bg-purple-900/30" :
                isError ? "bg-red-100 dark:bg-red-900/30" :
                    "bg-accent-100 dark:bg-accent-900/30";

        return (
            <div className="flex w-full mb-2 justify-start animate-fade-in">
                <div className="flex max-w-[85%] md:max-w-[75%] gap-3 ml-12">
                    <div className="flex flex-col gap-1 min-w-0 w-full">
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className={clsx(
                                "flex items-center gap-2 text-xs font-medium transition-colors w-full text-left group py-1",
                                isError ? "text-red-400 hover:text-red-500" : "text-gray-400 dark:text-gray-500 hover:text-accent-500 dark:hover:text-accent-400"
                            )}
                        >
                            <div className={clsx("w-4 h-4 rounded-full flex items-center justify-center shrink-0", bgClass)}>
                                <Icon size={10} className={clsx(
                                    colorClass,
                                    "transition-transform duration-200",
                                    isExpanded && !isIntent && !isPlan && !isError ? "rotate-180" : ""
                                )} />
                            </div>
                            <span className="uppercase tracking-wider text-[11px]">{title}</span>
                            <div className={clsx("flex-1 h-px ml-2", isError ? "bg-red-200 dark:bg-red-900/30" : "bg-gray-200 dark:bg-gray-800")} />
                        </button>

                        <div className={clsx(
                            "overflow-hidden transition-all duration-300 ease-out",
                            isExpanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
                        )}>
                            <div className={clsx(
                                "p-3 rounded-xl text-sm border-l-2 mt-1",
                                isIntent ? "bg-blue-50 dark:bg-blue-900/10 border-blue-300/50 dark:border-blue-700/30 text-gray-600 dark:text-gray-400" :
                                    isPlan ? "bg-purple-50 dark:bg-purple-900/10 border-purple-300/50 dark:border-purple-700/30 text-gray-600 dark:text-gray-400" :
                                        isError ? "bg-red-50 dark:bg-red-900/10 border-red-300/50 dark:border-red-700/30 text-red-600 dark:text-red-400 font-mono" :
                                            "bg-gray-50 dark:bg-gray-800/30 border-accent-300/50 dark:border-accent-700/30 font-mono text-gray-600 dark:text-gray-400"
                            )}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={clsx(
            "flex w-full mb-5 animate-fade-in",
            isUser ? "justify-end" : "justify-start"
        )}>
            <div className={clsx(
                "flex max-w-[80%] md:max-w-[70%] gap-3",
                isUser ? "flex-row-reverse" : "flex-row"
            )}>
                {/* Avatar */}
                <div className={clsx(
                    "w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-sm",
                    isUser
                        ? "bg-gradient-accent text-white"
                        : "bg-emerald-500 dark:bg-emerald-600 text-white"
                )}>
                    {isUser ? <User size={16} /> : <Bot size={16} />}
                </div>

                {/* Content */}
                <div className="flex flex-col gap-1.5 min-w-0 w-full">
                    {/* Name label */}
                    <div className={clsx(
                        "text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500",
                        isUser ? "text-right" : "text-left"
                    )}>
                        {isUser ? "You" : "Antigravity AI"}
                    </div>

                    {/* Bubble */}
                    <div className={clsx(
                        "p-4 rounded-2xl prose dark:prose-invert max-w-none break-words text-[15px] leading-relaxed",
                        "prose-p:my-2 prose-pre:p-0 prose-headings:mt-3 prose-headings:mb-2",
                        isUser
                            ? "bg-gradient-accent text-white prose-invert rounded-tr-md shadow-md"
                            : "glass-surface rounded-tl-md shadow-card"
                    )}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                code({ node, inline, className, children, ...props }: any) {
                                    const match = /language-(\w+)/.exec(className || '');
                                    const language = match ? match[1] : '';

                                    if (!inline && language === 'chart') {
                                        return <ChartRenderer content={String(children).replace(/\n$/, '')} />;
                                    }

                                    return (
                                        <code className={className} {...props}>
                                            {children}
                                        </code>
                                    );
                                }
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
});

MessageBubble.displayName = 'MessageBubble';

export default MessageBubble;
