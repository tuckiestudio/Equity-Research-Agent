import api from './api'
import { UserSettings, UserSettingsUpdate } from './types'

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
}
