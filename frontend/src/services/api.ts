import axios from 'axios';
import type { ConversationSummary, ConversationDetail, TokenResponse, UserPreferences, MCPServerInfo, UserMCPConfig } from '../types';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const setAuthToken = (token: string) => {
    if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
        delete api.defaults.headers.common['Authorization'];
    }
};

export const auth = {
    login: async (userName: string) => {
        const response = await api.post<TokenResponse>('/login', { user_name: userName });
        return response.data;
    },
};

export const chat = {
    listConversations: async () => {
        const response = await api.get<ConversationSummary[]>('/conversations');
        return response.data;
    },
    getConversation: async (id: string) => {
        const response = await api.get<ConversationDetail>(`/conversations/${id}`);
        return response.data;
    },
    deleteConversation: async (id: string) => {
        const response = await api.delete<{ status: string; id: string }>(`/conversations/${id}`);
        return response.data;
    },
    start: async () => {
        const response = await api.post<{ conversation_id: string; message: string }>('/chat/start', {});
        return response.data;
    },
};

export const user = {
    getPreferences: async () => {
        const response = await api.get<UserPreferences>('/user/preferences');
        return response.data;
    },
    updatePreferences: async (prefs: UserPreferences) => {
        const response = await api.put<UserPreferences>('/user/preferences', prefs);
        return response.data;
    },
    getMCPServers: async () => {
        const response = await api.get<MCPServerInfo[]>('/mcp/servers');
        return response.data;
    },
    getUserMCPConfigs: async () => {
        const response = await api.get<Record<string, Record<string, string>>>('/user/mcp-configs');
        return response.data;
    },
    updateUserMCPConfig: async (config: UserMCPConfig) => {
        const response = await api.post<{ status: string }>('/user/mcp-configs', config);
        return response.data;
    },
    getToolContexts: async () => {
        const response = await api.get<Record<string, string>>('/user/tool-contexts');
        return response.data;
    },
    submitMCPAuth: async (serverName: string, token: string, tokenName: string) => {
        const response = await api.post<{ status: string }>('/user/mcp-auth', {
            server_name: serverName,
            token,
            token_name: tokenName
        });
        return response.data;
    },
    getOAuthLoginUrl: (serverName: string, userName: string) => {
        return `${BASE_URL}/auth/login/${serverName}?user_name=${encodeURIComponent(userName)}`;
    }
};

export default api;
export const BASE_URL = API_URL;
