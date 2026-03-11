import api from './api'
import { UserSettings, UserSettingsUpdate, LLMProviderInfo, LLMTaskTypeInfo, ModelRoute } from './types'

export const settingsService = {
    /**
     * Get the current user's settings.
     */
    getSettings: async (): Promise<UserSettings> => {
        const { data } = await api.get<UserSettings>('/v1/settings')
        return data
    },

    /**
     * Update the current user's settings.
     */
    updateSettings: async (settings: UserSettingsUpdate): Promise<UserSettings> => {
        const { data } = await api.put<UserSettings>('/v1/settings', settings)
        return data
    },

    /**
     * Get available LLM providers and their models.
     */
    getLLMProviders: async (): Promise<LLMProviderInfo[]> => {
        const { data } = await api.get<LLMProviderInfo[]>('/v1/settings/llm-providers')
        return data
    },

    /**
     * Get all task types with their default routing.
     */
    getTaskTypes: async (): Promise<LLMTaskTypeInfo[]> => {
        const { data } = await api.get<LLMTaskTypeInfo[]>('/v1/settings/llm-task-types')
        return data
    },

    /**
     * Update the LLM route for a specific task type.
     */
    updateLLMRoute: async (taskType: string, route: ModelRoute): Promise<{ success: boolean; task_type: string; route: ModelRoute }> => {
        const { data } = await api.put(`/v1/settings/llm-route/${taskType}`, route)
        return data
    },

    /**
     * Reset all LLM routes to defaults.
     */
    resetLLMRoutes: async (): Promise<{ success: boolean; message: string }> => {
        const { data } = await api.post('/v1/settings/llm-route/reset')
        return data
    },
}
