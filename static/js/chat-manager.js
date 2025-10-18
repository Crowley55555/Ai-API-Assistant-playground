/**
 * Менеджер чатов для единообразной работы с разными чатами.
 * Реализует принципы SOLID и DRY.
 */

class ChatSettings {
    constructor(model, temperature, top_p, max_tokens, system_prompt = "", web_search = false, functions = []) {
        this.model = model;
        this.temperature = temperature;
        this.top_p = top_p;
        this.max_tokens = max_tokens;
        this.system_prompt = system_prompt;
        this.web_search = web_search;
        this.functions = functions;
    }
}

class ChatMessage {
    constructor(id, role, content, timestamp, token_stats = null) {
        this.id = id;
        this.role = role;
        this.content = content;
        this.timestamp = timestamp;
        this.token_stats = token_stats;
    }
}

class ChatSession {
    constructor(session_id, settings, messages = [], stats = null) {
        this.session_id = session_id;
        this.settings = settings;
        this.messages = messages;
        this.stats = stats;
    }
}

class ChatAPI {
    constructor(csrf_token) {
        this.csrf_token = csrf_token;
        this.base_url = '/playground/api';
    }

    async createSession(settings) {
        const response = await fetch(`${this.base_url}/create-session/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrf_token
            },
            body: JSON.stringify({
                model: settings.model,
                temperature: settings.temperature,
                top_p: settings.top_p,
                max_tokens: settings.max_tokens,
                system_prompt: settings.system_prompt,
                web_search: settings.web_search,
                functions: settings.functions
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                return data.session_id;
            }
        }

        throw new Error(`Failed to create session: ${response.statusText}`);
    }

    async sendMessage(session_id, message, functions) {
        const response = await fetch(`${this.base_url}/send-message/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrf_token
            },
            body: JSON.stringify({
                session_id: session_id,
                message: message,
                functions: functions
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                return data;
            }
        }

        throw new Error(`Failed to send message: ${response.statusText}`);
    }

    async updateSessionSettings(session_id, settings) {
        const response = await fetch(`${this.base_url}/update-session/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrf_token
            },
            body: JSON.stringify({
                session_id: session_id,
                model: settings.model,
                temperature: settings.temperature,
                top_p: settings.top_p,
                max_tokens: settings.max_tokens,
                system_prompt: settings.system_prompt,
                web_search: settings.web_search
            })
        });

        if (response.ok) {
            const data = await response.json();
            return data.success || false;
        }

        return false;
    }
}

class ChatManager {
    constructor(csrf_token) {
        this.api = new ChatAPI(csrf_token);
        this.sessions = new Map();
    }

    createChatSession(chat_id, settings) {
        const session = new ChatSession("", settings, []);
        this.sessions.set(chat_id, session);
        return session;
    }

    async initializeSession(chat_id) {
        if (!this.sessions.has(chat_id)) {
            throw new Error(`Chat session ${chat_id} not found`);
        }

        const session = this.sessions.get(chat_id);
        const session_id = await this.api.createSession(session.settings);
        session.session_id = session_id;

        console.log(`Session initialized for chat ${chat_id}: ${session_id}`);
        return session_id;
    }

    async sendMessage(chat_id, message) {
        if (!this.sessions.has(chat_id)) {
            throw new Error(`Chat session ${chat_id} not found`);
        }

        const session = this.sessions.get(chat_id);

        // Если нет session_id, инициализируем сессию
        if (!session.session_id) {
            await this.initializeSession(chat_id);
        }

        // Добавляем сообщение пользователя
        const user_message = new ChatMessage(
            Date.now().toString(),
            'user',
            message,
            new Date().toISOString()
        );
        session.messages.push(user_message);

        // Отправляем сообщение через API
        const response = await this.api.sendMessage(
            session.session_id,
            message,
            session.settings.functions
        );

        // Добавляем ответ ассистента
        const assistant_message = new ChatMessage(
            (Date.now() + 1).toString(),
            'assistant',
            response.assistant_message.content,
            response.assistant_message.timestamp,
            response.assistant_message.token_stats
        );
        session.messages.push(assistant_message);

        // Обновляем статистику
        if (response.session_stats) {
            session.stats = response.session_stats;
        }

        console.log(`Message sent to chat ${chat_id}, response length: ${assistant_message.content.length}`);
        console.log(`Session settings for ${chat_id}:`, {
            model: session.settings.model,
            web_search: session.settings.web_search
        });
        return assistant_message;
    }

    async updateSettings(chat_id, settings) {
        if (!this.sessions.has(chat_id)) {
            throw new Error(`Chat session ${chat_id} not found`);
        }

        const session = this.sessions.get(chat_id);
        
        // Обновляем локальные настройки
        session.settings = settings;

        // Если есть session_id, обновляем настройки на сервере
        if (session.session_id) {
            const success = await this.api.updateSessionSettings(session.session_id, settings);
            if (success) {
                console.log(`Settings updated for chat ${chat_id}:`, {
                    model: settings.model,
                    web_search: settings.web_search
                });
            }
            return success;
        }

        console.log(`Local settings updated for chat ${chat_id}:`, {
            model: settings.model,
            web_search: settings.web_search
        });
        return true;
    }

    getSession(chat_id) {
        return this.sessions.get(chat_id);
    }

    clearMessages(chat_id) {
        if (this.sessions.has(chat_id)) {
            this.sessions.get(chat_id).messages = [];
            console.log(`Messages cleared for chat ${chat_id}`);
        }
    }

    hasSession(chat_id) {
        return this.sessions.has(chat_id);
    }

    getSessionId(chat_id) {
        const session = this.sessions.get(chat_id);
        return session ? session.session_id : null;
    }

    async forceUpdateSessionSettings(chat_id) {
        if (!this.sessions.has(chat_id)) {
            throw new Error(`Chat session ${chat_id} not found`);
        }

        const session = this.sessions.get(chat_id);
        
        if (session.session_id) {
            const success = await this.api.updateSessionSettings(session.session_id, session.settings);
            if (success) {
                console.log(`Force updated settings for chat ${chat_id}:`, {
                    model: session.settings.model,
                    web_search: session.settings.web_search,
                    system_prompt: session.settings.system_prompt ? 'present' : 'empty',
                    functions: session.settings.functions.length
                });
            }
            return success;
        }
        
        return false;
    }

    async updateAllSessions() {
        const results = {};
        
        for (const [chat_id, session] of this.sessions) {
            if (session.session_id) {
                try {
                    const success = await this.api.updateSessionSettings(session.session_id, session.settings);
                    results[chat_id] = success;
                    if (success) {
                        console.log(`Updated session ${chat_id}:`, {
                            model: session.settings.model,
                            web_search: session.settings.web_search,
                            system_prompt: session.settings.system_prompt ? 'present' : 'empty',
                            functions: session.settings.functions.length
                        });
                    }
                } catch (error) {
                    console.error(`Error updating session ${chat_id}:`, error);
                    results[chat_id] = false;
                }
            } else {
                results[chat_id] = true; // No session to update
            }
        }
        
        return results;
    }
}

class ChatFactory {
    static createChatManager(csrf_token) {
        return new ChatManager(csrf_token);
    }

    static createSettings(model, temperature, top_p, max_tokens, system_prompt = "", web_search = false, functions = []) {
        return new ChatSettings(model, temperature, top_p, max_tokens, system_prompt, web_search, functions);
    }
}

// Экспортируем классы для использования в других модулях
window.ChatManager = ChatManager;
window.ChatFactory = ChatFactory;
window.ChatSettings = ChatSettings;
window.ChatMessage = ChatMessage;
window.ChatSession = ChatSession;
