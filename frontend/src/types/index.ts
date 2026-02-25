export interface Message {
    role: 'user' | 'assistant' | 'system' | 'thought' | 'auth_required' | 'intent' | 'plan' | 'error';
    content: string;
    type?: 'message' | 'thought' | 'auth_required' | 'intent' | 'plan' | 'error';
    id?: string;
    timestamp?: string;
    thoughts?: string;
    auth_config?: InteractiveAuthConfig;
}

export interface InteractiveAuthConfig {
    server_name: string;
    type: 'browser' | 'oauth';
    instructions: string;
    target_env_var: string;
    auth_url?: string;
    button_text?: string;
    // OAuth specific
    authorize_url?: string;
    token_url?: string;
    scope?: string;
    client_id_env?: string;
    client_secret_env?: string;
    redirect_uri_env?: string;
}

export interface ConversationSummary {
    id: string;
    title: string;
    created_at: string;
    updated_at?: string;
}

export interface ConversationDetail {
    id: string;
    title: string;
    created_at: string;
    updated_at?: string;
    messages: any[]; // The backend returns a list of raw messages, we map them
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    user_name: string;
}

export interface User {
    name: string;
    token: string;
}

export interface UserPreferences {
    model: string;
    fontFamily: string;
    fontSize: string;
}

export interface MCPServerInfo {
    name: string;
    required_env: string[];
    interactive_auth?: {
        type: string;
        auth_url: string;
        instructions: string;
        target_env_var: string;
    };
}

export interface UserMCPConfig {
    server_name: string;
    env_vars: Record<string, string>;
    tool_context?: string;
}
