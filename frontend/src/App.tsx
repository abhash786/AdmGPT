import { useState, useEffect } from 'react';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import PreferencesModal from './components/PreferencesModal';
import { chat, user, setAuthToken } from './services/api';
import type { ConversationSummary, Message, UserPreferences } from './types';
import { Rocket } from 'lucide-react';

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [userName, setUserName] = useState<string>(localStorage.getItem('userName') || '');
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences>({
    model: 'gpt-4o',
    fontFamily: 'Inter',
    fontSize: 'Medium'
  });

  useEffect(() => {
    if (token) {
      setAuthToken(token);
      loadConversations();
      loadPreferences();
    }
  }, [token]);

  useEffect(() => {
    applyPreferences(preferences);
  }, [preferences]);

  const loadPreferences = async () => {
    try {
      const prefs = await user.getPreferences();
      setPreferences(prefs);
    } catch (error) {
      console.error("Failed to load preferences", error);
    }
  };

  const applyPreferences = (prefs: UserPreferences) => {
    // Apply Font Family — quote multi-word names for CSS
    const fontValue = prefs.fontFamily === 'JetBrains Mono'
      ? `'JetBrains Mono', monospace`
      : `'${prefs.fontFamily}', system-ui, sans-serif`;
    document.body.style.fontFamily = fontValue;
    const sizeMap: Record<string, string> = {
      'Extra Small': '12px',
      'Small': '14px',
      'Medium': '16px',
      'Large': '18px',
      'Extra Large': '20px'
    };
    document.documentElement.style.fontSize = sizeMap[prefs.fontSize] || '16px';
  };

  const loadConversations = async () => {
    try {
      const data = await chat.listConversations();
      const sorted = data.sort((a, b) => {
        const timeA = new Date(a.updated_at || a.created_at).getTime();
        const timeB = new Date(b.updated_at || b.created_at).getTime();

        const validA = !isNaN(timeA) ? timeA : 0;
        const validB = !isNaN(timeB) ? timeB : 0;

        return validB - validA;
      });
      setConversations(sorted || []);
    } catch (err: any) {
      console.error('Failed to load conversations', err);
      if (err.response && err.response.status === 401) {
        handleLogout();
      }
    }
  };

  const loadConversationHistory = async (id: string) => {
    setIsLoadingHistory(true);
    try {
      const detail = await chat.getConversation(id);
      const formattedMessages: Message[] = [];

      detail.messages.forEach((m: any) => {
        if (m.thoughts && Array.isArray(m.thoughts) && m.thoughts.length > 0) {
          formattedMessages.push({
            role: 'assistant',
            content: m.thoughts.join('\n'),
            type: 'thought'
          });
        }

        if (!m.content && m.role === 'assistant') {
          return;
        }

        if (m.role === 'tool') {
          formattedMessages.push({
            role: 'assistant',
            content: m.content || "Tool executed successfully.",
            type: 'thought'
          });
        } else if (m.role === 'intent' || m.role === 'plan' || m.role === 'error') {
          formattedMessages.push({
            role: m.role,
            content: m.content || "",
            type: m.role as any
          });
        } else {
          formattedMessages.push({
            role: m.role,
            content: m.content || "",
            type: 'message'
          });
        }
      });
      setMessages(formattedMessages);
    } catch (error) {
      console.error("Failed to load history", error);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  useEffect(() => {
    if (currentConversationId) {
      loadConversationHistory(currentConversationId);
    } else {
      setMessages([]);
    }
  }, [currentConversationId]);

  const handleLogin = (newToken: string, name: string) => {
    // Reset conversation state when a new user logs in
    setCurrentConversationId(null);
    setMessages([]);
    setConversations([]);

    localStorage.setItem('token', newToken);
    localStorage.setItem('userName', name);
    setToken(newToken);
    setUserName(name);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
    setToken(null);
    setUserName('');
    setConversations([]);
    setCurrentConversationId(null);
    setMessages([]);
  };

  const handleNewChat = async () => {
    try {
      const data = await chat.start();
      setCurrentConversationId(data.conversation_id);
      setMessages([{ role: 'assistant', content: data.message }]);
      await loadConversations();
    } catch (error) {
      console.error("Failed to start chat", error);
    }
  };

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id);
  };

  const handleTitleUpdate = (id: string, newTitle: string) => {
    setConversations(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
  };

  const handleDeleteConversation = async (id: string) => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await chat.deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));

      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete conversation", error);
    }
  };

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300">
      <Sidebar
        conversations={conversations}
        currentId={currentConversationId || undefined}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        user={{ name: userName }}
        onLogout={handleLogout}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onDelete={handleDeleteConversation}
      />
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {currentConversationId ? (
          isLoadingHistory ? (
            <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-950">
              <div className="flex flex-col items-center gap-3 animate-fade-in">
                <div className="w-8 h-8 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
                <span className="text-sm text-gray-400 dark:text-gray-500">Loading conversation...</span>
              </div>
            </div>
          ) : (
            <ChatArea
              conversationId={currentConversationId}
              token={token}
              initialMessages={messages}
              onTitleUpdate={handleTitleUpdate}
            />
          )
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-gray-50 dark:bg-gray-950 relative">
            {/* Background decoration */}
            <div className="absolute inset-0 bg-gradient-mesh dark:bg-gradient-mesh-dark opacity-50 pointer-events-none" />

            <div className="relative z-10 animate-fade-in">
              <div className="animate-float mb-6 inline-block">
                <div className="w-20 h-20 rounded-3xl bg-gradient-accent shadow-glow flex items-center justify-center">
                  <Rocket className="w-10 h-10 text-white" />
                </div>
              </div>
              <h1 className="text-4xl md:text-5xl font-bold text-gradient mb-3">Antigravity AI</h1>
              <p className="text-gray-400 dark:text-gray-500 mb-8 max-w-md mx-auto">
                Select a conversation or start a new one to begin exploring.
              </p>
              <button
                onClick={handleNewChat}
                className="px-8 py-3.5 btn-accent text-base shadow-lg"
              >
                Start New Chat
              </button>
            </div>
          </div>
        )}
      </main>

      <PreferencesModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSave={(model, fontFamily, fontSize) => setPreferences({ model, fontFamily, fontSize })}
        currentModel={preferences.model}
        currentFontFamily={preferences.fontFamily}
        currentFontSize={preferences.fontSize}
      />
    </div>
  );
}

export default App;
