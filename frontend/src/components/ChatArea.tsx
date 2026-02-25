import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, StopCircle, Rocket } from 'lucide-react';
import MessageBubble from './MessageBubble';
import type { Message } from '../types';
import { BASE_URL } from '../services/api';

interface ChatAreaProps {
    conversationId: string | null;
    token: string;
    initialMessages?: Message[];
    onNewMessage?: (msg: Message) => void;
    onTitleUpdate?: (id: string, title: string) => void;
}

const ChatArea: React.FC<ChatAreaProps> = ({ conversationId, token, initialMessages = [], onNewMessage, onTitleUpdate }) => {
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const abortControllerRef = useRef<AbortController | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        setMessages(initialMessages);
    }, [initialMessages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isStreaming]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
        }
    }, [input]);

    const handleSend = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || !conversationId) return;

        const userMsg: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        onNewMessage?.(userMsg);
        setInput('');
        setIsLoading(true);
        setIsStreaming(true);

        abortControllerRef.current = new AbortController();

        let aiContent = '';

        try {
            const response = await fetch(`${BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    message: userMsg.content,
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok || !response.body) {
                throw new Error(response.statusText);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.replace('data: ', '').trim();
                        if (dataStr === '[DONE]') break;

                        try {
                            const event = JSON.parse(dataStr);

                            if (event.type === 'token') {
                                aiContent += event.content;
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    const lastMsg = newMsgs[newMsgs.length - 1];

                                    // If last message is a thought or user message, push a new AI message
                                    if (!lastMsg || lastMsg.role === 'user' || lastMsg.type === 'thought') {
                                        newMsgs.push({ role: 'assistant', content: aiContent, type: 'message' });
                                    } else {
                                        // Create NEW object so React.memo detects the change
                                        newMsgs[newMsgs.length - 1] = { ...lastMsg, content: aiContent, type: 'message' };
                                    }
                                    return newMsgs;
                                });
                            } else if (event.type === 'thought') {
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    // Always push thought as a new message
                                    newMsgs.push({ role: 'assistant', content: event.content, type: 'thought' });
                                    return newMsgs;
                                });
                            } else if (event.type === 'question') {
                                // Handle ask_user tool — show the question as a regular AI message
                                setMessages(prev => [
                                    ...prev,
                                    { role: 'assistant', content: event.content, type: 'message' }
                                ]);
                            } else if (event.type === 'auth_required') {
                                setMessages(prev => [
                                    ...prev,
                                    {
                                        role: 'assistant',
                                        content: event.auth_config.instructions,
                                        type: 'auth_required',
                                        auth_config: {
                                            server_name: event.server_name,
                                            ...event.auth_config
                                        }
                                    }
                                ]);
                                // Stop streaming since we need user action
                                break;
                            } else if (event.type === 'intent') {
                                setMessages(prev => [
                                    ...prev,
                                    { role: 'intent', content: event.content, type: 'intent' }
                                ]);
                            } else if (event.type === 'plan') {
                                setMessages(prev => [
                                    ...prev,
                                    { role: 'plan', content: event.content, type: 'plan' }
                                ]);
                            } else if (event.type === 'error') {
                                setMessages(prev => [
                                    ...prev,
                                    { role: 'error', content: event.content, type: 'error' }
                                ]);
                            } else if (event.type === 'title') {
                                onTitleUpdate?.(conversationId, event.content);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE event:', e);
                        }
                    }
                }
            }
        } catch (error: any) {
            if (error.name !== 'AbortError') {
                console.error('Error sending message:', error);
                setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
            }
        } finally {
            setIsLoading(false);
            setIsStreaming(false);
            abortControllerRef.current = null;
        }
    };

    const handleStop = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setIsStreaming(false);
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full relative bg-gray-50 dark:bg-gray-950">
            {/* Subtle background pattern */}
            <div className="absolute inset-0 bg-gradient-mesh dark:bg-gradient-mesh-dark opacity-50 pointer-events-none" />

            {/* Messages Area */}
            <div className="relative flex-1 overflow-y-auto px-4 md:px-8 py-6">
                <div className="max-w-4xl mx-auto">
                    {messages.length === 0 ? (
                        <div className="h-full min-h-[60vh] flex flex-col items-center justify-center text-center">
                            <div className="animate-float mb-6">
                                <div className="w-16 h-16 rounded-2xl bg-gradient-accent shadow-glow flex items-center justify-center">
                                    <Rocket className="w-8 h-8 text-white" />
                                </div>
                            </div>
                            <h2 className="text-2xl md:text-3xl font-bold text-gradient mb-3">
                                How can I help you defy gravity?
                            </h2>
                            <p className="text-gray-400 dark:text-gray-500 text-sm max-w-md">
                                Ask me anything — I can analyze data, write code, search across your tools, and much more.
                            </p>
                        </div>
                    ) : (
                        messages.map((msg, index) => (
                            <MessageBubble key={index} message={msg} />
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="relative px-4 pb-4 pt-2">
                <div className="max-w-4xl mx-auto">
                    <form
                        onSubmit={handleSend}
                        className="relative glass-card rounded-2xl shadow-card transition-shadow duration-200 focus-within:shadow-card-hover"
                    >
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Message Antigravity AI..."
                            disabled={isLoading && !isStreaming}
                            rows={1}
                            style={{ minHeight: '52px', maxHeight: '200px' }}
                            className="w-full py-3.5 pl-4 pr-14 bg-transparent text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none resize-none text-[15px] leading-relaxed"
                        />

                        <div className="absolute right-2 bottom-2">
                            {isStreaming ? (
                                <button
                                    type="button"
                                    onClick={handleStop}
                                    className="p-2.5 rounded-xl bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all duration-200"
                                >
                                    <StopCircle size={18} />
                                </button>
                            ) : (
                                <button
                                    type="submit"
                                    disabled={!input.trim() || isLoading}
                                    className="p-2.5 rounded-xl bg-gradient-accent text-white shadow-md disabled:opacity-30 disabled:shadow-none hover:shadow-glow transition-all duration-200 disabled:hover:shadow-none"
                                >
                                    {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                                </button>
                            )}
                        </div>
                    </form>
                    <div className="text-center text-[11px] text-gray-400 dark:text-gray-600 mt-2">
                        AI can make mistakes. Consider checking important information.
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatArea;
