import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings as SettingsIcon, Save } from 'lucide-react'
import clsx from 'clsx'
import { settingsService } from '@/services/settings'
import { UserSettingsUpdate } from '@/services/types'

export default function Settings() {
    const queryClient = useQueryClient()
    const [formData, setFormData] = useState<UserSettingsUpdate>({
        fundamentals_provider: 'fmp',
        price_provider: 'finnhub',
        profile_provider: 'fmp',
        news_provider: 'finnhub',
        fmp_api_key: '',
        finnhub_api_key: '',
        eodhd_api_key: '',
        polygon_api_key: '',
        alpha_vantage_api_key: '',
        openai_api_key: '',
        anthropic_api_key: '',
    })

    // Fetch current settings
    const { data: currentSettings, isLoading } = useQuery({
        queryKey: ['settings'],
        queryFn: settingsService.getSettings,
    })

    // Update formData when settings load
    useEffect(() => {
        if (currentSettings) {
            setFormData({
                fundamentals_provider: currentSettings.fundamentals_provider || 'fmp',
                price_provider: currentSettings.price_provider || 'finnhub',
                profile_provider: currentSettings.profile_provider || 'fmp',
                news_provider: currentSettings.news_provider || 'finnhub',
                fmp_api_key: currentSettings.fmp_api_key || '',
                finnhub_api_key: currentSettings.finnhub_api_key || '',
                eodhd_api_key: currentSettings.eodhd_api_key || '',
                polygon_api_key: currentSettings.polygon_api_key || '',
                alpha_vantage_api_key: currentSettings.alpha_vantage_api_key || '',
                openai_api_key: currentSettings.openai_api_key || '',
                anthropic_api_key: currentSettings.anthropic_api_key || '',
            })
        }
    }, [currentSettings])

    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    const updateMutation = useMutation({
        mutationFn: (newSettings: UserSettingsUpdate) => settingsService.updateSettings(newSettings),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings'] })
            setMessage({ type: 'success', text: 'Settings updated successfully' })
            setTimeout(() => setMessage(null), 3000)
        },
        onError: (error: any) => {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to update settings' })
        },
    })

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setFormData((prev) => ({ ...prev, [name]: value }))
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        updateMutation.mutate(formData)
    }

    if (isLoading) {
        return (
            <div className="flex-1 p-8 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            </div>
        )
    }

    return (
        <div className="flex-1 p-8 overflow-y-auto">
            <div className="max-w-3xl mx-auto space-y-8 animate-fade-in">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-text-primary mb-2 flex items-center gap-3">
                        <SettingsIcon className="w-8 h-8 text-accent" />
                        Settings
                    </h1>
                    <p className="text-text-secondary">
                        Manage your API keys and data providers
                    </p>
                </div>

                {/* Status Message */}
                {message && (
                    <div
                        className={clsx(
                            'p-4 rounded-lg border',
                            message.type === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-500' : 'bg-danger/10 border-danger/30 text-danger'
                        )}
                    >
                        {message.text}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="glass-card p-6 space-y-6">
                        <h2 className="text-xl font-semibold text-text-primary border-b border-border pb-2">
                            Data Providers
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">Fundamentals Provider</label>
                                <select
                                    name="fundamentals_provider"
                                    value={formData.fundamentals_provider || 'fmp'}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                >
                                    <option value="fmp">Financial Modeling Prep</option>
                                    <option value="finnhub">Finnhub</option>
                                    <option value="eodhd">EODHD</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">Price Provider</label>
                                <select
                                    name="price_provider"
                                    value={formData.price_provider || 'finnhub'}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                >
                                    <option value="finnhub">Finnhub</option>
                                    <option value="fmp">Financial Modeling Prep</option>
                                    <option value="eodhd">EODHD</option>
                                    <option value="polygon">Polygon</option>
                                    <option value="alpha_vantage">Alpha Vantage</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">Profile Provider</label>
                                <select
                                    name="profile_provider"
                                    value={formData.profile_provider || 'fmp'}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                >
                                    <option value="fmp">Financial Modeling Prep</option>
                                    <option value="finnhub">Finnhub</option>
                                    <option value="eodhd">EODHD</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">News Provider</label>
                                <select
                                    name="news_provider"
                                    value={formData.news_provider || 'finnhub'}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                >
                                    <option value="finnhub">Finnhub</option>
                                    <option value="polygon">Polygon</option>
                                    <option value="alpha_vantage">Alpha Vantage</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-6 space-y-6">
                        <h2 className="text-xl font-semibold text-text-primary border-b border-border pb-2">
                            API Keys
                        </h2>
                        <p className="text-sm text-text-secondary">
                            Leave blank to use system defaults. Your API keys are stored securely.
                        </p>

                        <div className="space-y-4">
                            {[
                                { label: 'Financial Modeling Prep', name: 'fmp_api_key' },
                                { label: 'Finnhub', name: 'finnhub_api_key' },
                                { label: 'EODHD', name: 'eodhd_api_key' },
                                { label: 'Polygon', name: 'polygon_api_key' },
                                { label: 'Alpha Vantage', name: 'alpha_vantage_api_key' },
                                { label: 'OpenAI (Must be GPT-4o)', name: 'openai_api_key' },
                                { label: 'Anthropic (Must be Claude 3.5 Sonnet)', name: 'anthropic_api_key' },
                            ].map((field) => (
                                <div key={field.name}>
                                    <label htmlFor={field.name} className="block text-sm font-medium text-text-secondary mb-2">
                                        {field.label} API Key
                                    </label>
                                    <input
                                        type="password"
                                        id={field.name}
                                        name={field.name}
                                        value={(formData as any)[field.name] || ''}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-all duration-200"
                                        placeholder="Enter API key or leave blank for default"
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-end pt-4">
                        <button
                            type="submit"
                            disabled={updateMutation.isPending}
                            className={clsx(
                                'flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-white',
                                'bg-accent hover:bg-accent-hover transition-colors',
                                'disabled:opacity-50 disabled:cursor-not-allowed'
                            )}
                        >
                            <Save className="w-5 h-5" />
                            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
