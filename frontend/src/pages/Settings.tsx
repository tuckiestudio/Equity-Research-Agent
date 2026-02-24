import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings as SettingsIcon, Save, Database, Key, Cpu, RefreshCcw } from 'lucide-react'
import clsx from 'clsx'
import { settingsService } from '@/services/settings'
import { UserSettingsUpdate, ModelRoute } from '@/services/types'

type SettingsTab = 'data-providers' | 'api-keys' | 'llm-routing'

export default function Settings() {
    const queryClient = useQueryClient()
    const [activeTab, setActiveTab] = useState<SettingsTab>('data-providers')
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

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
        glm_api_key: '',
        kimi_api_key: '',
        openrouter_api_key: '',
        chutes_api_key: '',
    })

    // Fetch current settings
    const { data: currentSettings, isLoading } = useQuery({
        queryKey: ['settings'],
        queryFn: settingsService.getSettings,
    })

    // Fetch available LLM providers
    const { data: llmProviders } = useQuery({
        queryKey: ['llm-providers'],
        queryFn: settingsService.getLLMProviders,
        refetchInterval: 5000, // Re-fetch every 5s to detect when API keys are added
    })

    // Fetch task types
    const { data: taskTypes } = useQuery({
        queryKey: ['llm-task-types'],
        queryFn: settingsService.getTaskTypes,
    })

    // Fetch current routing preferences
    const { data: currentRouting } = useQuery({
        queryKey: ['llm-routing'],
        queryFn: async () => {
            const settings = await settingsService.getSettings()
            return settings.llm_routing_preferences
        },
        enabled: !!currentSettings,
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
                glm_api_key: currentSettings.glm_api_key || '',
                kimi_api_key: currentSettings.kimi_api_key || '',
                openrouter_api_key: currentSettings.openrouter_api_key || '',
                chutes_api_key: currentSettings.chutes_api_key || '',
            })
        }
    }, [currentSettings])

    const updateMutation = useMutation({
        mutationFn: (newSettings: UserSettingsUpdate) => settingsService.updateSettings(newSettings),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings'] })
            queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
            setMessage({ type: 'success', text: 'Settings updated successfully' })
            setTimeout(() => setMessage(null), 3000)
        },
        onError: (error: any) => {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to update settings' })
        },
    })

    // Mutation for updating individual task routes
    const updateRouteMutation = useMutation({
        mutationFn: ({ taskType, route }: { taskType: string; route: ModelRoute }) =>
            settingsService.updateLLMRoute(taskType, route),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['llm-routing'] })
            queryClient.invalidateQueries({ queryKey: ['settings'] })
            setMessage({ type: 'success', text: 'Model route updated' })
            setTimeout(() => setMessage(null), 2000)
        },
        onError: (error: any) => {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to update route' })
        },
    })

    // Mutation for resetting routes
    const resetRoutesMutation = useMutation({
        mutationFn: () => settingsService.resetLLMRoutes(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['llm-routing'] })
            queryClient.invalidateQueries({ queryKey: ['settings'] })
            setMessage({ type: 'success', text: 'Routes reset to defaults' })
            setTimeout(() => setMessage(null), 2000)
        },
        onError: (error: any) => {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to reset routes' })
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

    const handleRouteChange = (taskType: string, provider: string, model: string) => {
        updateRouteMutation.mutate({ taskType, route: { provider, model } })
    }

    const getModelsForProvider = (providerName: string): string[] => {
        const provider = llmProviders?.find(p => p.name === providerName)
        return provider?.models || []
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
            <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-text-primary mb-2 flex items-center gap-3">
                        <SettingsIcon className="w-8 h-8 text-accent" />
                        Settings
                    </h1>
                    <p className="text-text-secondary">
                        Manage your API keys, data providers, and AI model preferences
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

                {/* Tabs */}
                <div className="flex gap-2 border-b border-border">
                    <button
                        onClick={() => setActiveTab('data-providers')}
                        className={clsx(
                            'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                            activeTab === 'data-providers'
                                ? 'border-accent text-accent'
                                : 'border-transparent text-text-secondary hover:text-text-primary'
                        )}
                    >
                        <Database className="w-4 h-4 inline-block mr-2 -mt-0.5" />
                        Data Providers
                    </button>
                    <button
                        onClick={() => setActiveTab('api-keys')}
                        className={clsx(
                            'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                            activeTab === 'api-keys'
                                ? 'border-accent text-accent'
                                : 'border-transparent text-text-secondary hover:text-text-primary'
                        )}
                    >
                        <Key className="w-4 h-4 inline-block mr-2 -mt-0.5" />
                        API Keys
                    </button>
                    <button
                        onClick={() => setActiveTab('llm-routing')}
                        className={clsx(
                            'px-4 py-2 text-sm font-medium transition-colors border-b-2',
                            activeTab === 'llm-routing'
                                ? 'border-accent text-accent'
                                : 'border-transparent text-text-secondary hover:text-text-primary'
                        )}
                    >
                        <Cpu className="w-4 h-4 inline-block mr-2 -mt-0.5" />
                        AI Model Routing
                    </button>
                </div>

                {/* Data Providers Tab */}
                {activeTab === 'data-providers' && (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="glass-card p-6 space-y-6">
                            <h2 className="text-xl font-semibold text-text-primary border-b border-border pb-2">
                                Data Provider Selection
                            </h2>
                            <p className="text-sm text-text-secondary">
                                Select which providers to use for different types of financial data.
                            </p>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">
                                        Fundamentals Provider
                                    </label>
                                    <select
                                        name="fundamentals_provider"
                                        value={formData.fundamentals_provider || 'fmp'}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                    >
                                        <option value="fmp">Financial Modeling Prep</option>
                                        <option value="finnhub">Finnhub</option>
                                        <option value="eodhd">EODHD</option>
                                        <option value="yfinance">Yahoo Finance (Free)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">
                                        Price Provider
                                    </label>
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
                                        <option value="yfinance">Yahoo Finance (Free)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-text-secondary mb-2">
                                        Profile Provider
                                    </label>
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
                                    <label className="block text-sm font-medium text-text-secondary mb-2">
                                        News Provider
                                    </label>
                                    <select
                                        name="news_provider"
                                        value={formData.news_provider || 'finnhub'}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                    >
                                        <option value="yfinance">Yahoo Finance (Free, no API key)</option>
                                        <option value="finnhub">Finnhub (API key required)</option>
                                        <option value="polygon">Polygon (API key required)</option>
                                        <option value="alpha_vantage">Alpha Vantage (API key required)</option>
                                    </select>
                                </div>
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
                )}

                {/* API Keys Tab */}
                {activeTab === 'api-keys' && (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="glass-card p-6 space-y-6">
                            <h2 className="text-xl font-semibold text-text-primary border-b border-border pb-2">
                                Financial Data API Keys
                            </h2>
                            <p className="text-sm text-text-secondary">
                                Leave blank to use system defaults. Your API keys are stored securely.
                            </p>

                            <div className="space-y-4">
                                {[
                                    { label: 'Financial Modeling Prep', name: 'fmp_api_key', hint: 'For fundamentals, profiles, and price data' },
                                    { label: 'Finnhub', name: 'finnhub_api_key', hint: 'For price data and news' },
                                    { label: 'EODHD', name: 'eodhd_api_key', hint: 'For fundamentals and historical data' },
                                    { label: 'Polygon', name: 'polygon_api_key', hint: 'For real-time price data' },
                                    { label: 'Alpha Vantage', name: 'alpha_vantage_api_key', hint: 'For price data and technical indicators' },
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
                                        {field.hint && (
                                            <p className="text-xs text-text-muted mt-1">{field.hint}</p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="glass-card p-6 space-y-6">
                            <h2 className="text-xl font-semibold text-text-primary border-b border-border pb-2">
                                AI/LLM API Keys
                            </h2>
                            <p className="text-sm text-text-secondary mb-4">
                                Add API keys for AI-powered news analysis, thesis generation, and note extraction.
                            </p>

                            <div className="space-y-4">
                                {[
                                    {
                                        name: 'openai_api_key',
                                        label: 'OpenAI',
                                        hint: 'GPT-4o, GPT-4 Turbo, GPT-4o-mini',
                                        models: ['gpt-4o', 'gpt-4-turbo', 'gpt-4o-mini']
                                    },
                                    {
                                        name: 'anthropic_api_key',
                                        label: 'Anthropic',
                                        hint: 'Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku',
                                        models: ['claude-sonnet-4-20250514', 'claude-3-opus', 'claude-3-haiku']
                                    },
                                    {
                                        name: 'openrouter_api_key',
                                        label: 'OpenRouter',
                                        hint: '100+ models: Claude, GPT-4, Llama, Mistral, Gemini & more',
                                        models: ['anthropic/claude-3-opus', 'openai/gpt-4o', 'meta-llama/llama-3-70b-instruct']
                                    },
                                    {
                                        name: 'glm_api_key',
                                        label: 'Z.ai (GLM)',
                                        hint: 'GLM-4 models from Zhipu AI',
                                        models: ['glm-4.7', 'glm-4.5', 'glm-4-flash']
                                    },
                                    {
                                        name: 'kimi_api_key',
                                        label: 'Moonshot (Kimi)',
                                        hint: 'Kimi-K2.5 models - strong at long context',
                                        models: ['kimi-k2.5', 'kimi-flash']
                                    },
                                    {
                                        name: 'chutes_api_key',
                                        label: 'Chutes.ai',
                                        hint: 'Fast Llama, Mistral, Qwen inference',
                                        models: ['llama-3-70b-instruct', 'llama-3-8b-instruct', 'mixtral-8x7b-instruct']
                                    },
                                ].map((field) => {
                                    const provider = llmProviders?.find(p => p.name === field.name.replace('_api_key', ''))
                                    return (
                                        <div key={field.name}>
                                            <label htmlFor={field.name} className="block text-sm font-medium text-text-secondary mb-2">
                                                {field.label}
                                                {provider?.has_api_key && (
                                                    <span className="ml-2 text-xs text-green-500">● Connected</span>
                                                )}
                                            </label>
                                            <input
                                                type="password"
                                                id={field.name}
                                                name={field.name}
                                                value={(formData as any)[field.name] || ''}
                                                onChange={handleChange}
                                                className="w-full px-4 py-2 bg-surface rounded-lg border border-border text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-all duration-200"
                                                placeholder="Enter API key"
                                            />
                                            <p className="text-xs text-text-muted mt-1">{field.hint}</p>
                                        </div>
                                    )
                                })}
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
                )}

                {/* LLM Routing Tab */}
                {activeTab === 'llm-routing' && (
                    <div className="space-y-6">
                        <div className="glass-card p-6 space-y-6">
                            <div className="flex items-center justify-between border-b border-border pb-4">
                                <div>
                                    <h2 className="text-xl font-semibold text-text-primary">
                                        AI Model Routing
                                    </h2>
                                    <p className="text-sm text-text-secondary mt-1">
                                        Select which AI model to use for each type of task.
                                    </p>
                                </div>
                                <button
                                    onClick={() => resetRoutesMutation.mutate()}
                                    disabled={resetRoutesMutation.isPending}
                                    className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary border border-border rounded-lg hover:bg-surface transition-colors disabled:opacity-50"
                                >
                                    <RefreshCcw className="w-4 h-4" />
                                    Reset to Defaults
                                </button>
                            </div>

                            {/* Available Providers Summary */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {llmProviders?.map((provider) => (
                                    <div
                                        key={provider.name}
                                        className={clsx(
                                            'p-3 rounded-lg border',
                                            provider.has_api_key
                                                ? 'bg-green-500/10 border-green-500/30'
                                                : 'bg-surface border-border opacity-60'
                                        )}
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-text-primary">
                                                {provider.display_name}
                                            </span>
                                            {provider.has_api_key ? (
                                                <span className="w-2 h-2 rounded-full bg-green-500" />
                                            ) : (
                                                <span className="w-2 h-2 rounded-full bg-border" />
                                            )}
                                        </div>
                                        <p className="text-xs text-text-secondary mt-1">
                                            {provider.models.length} models
                                        </p>
                                    </div>
                                ))}
                                {(!llmProviders || llmProviders.length === 0) && (
                                    <div className="col-span-full p-4 text-center text-text-secondary border border-border rounded-lg">
                                        No AI providers configured. Add API keys in the API Keys tab.
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Task Type Routing */}
                        <div className="glass-card p-6 space-y-4">
                            <h3 className="text-lg font-medium text-text-primary border-b border-border pb-2">
                                Task-Specific Model Selection
                            </h3>

                            {taskTypes?.map((taskType) => {
                                const currentRoute = currentRouting?.[taskType.type]
                                const selectedProvider = currentRoute?.provider || taskType.default_provider
                                const selectedModel = currentRoute?.model || taskType.default_model

                                return (
                                    <div key={taskType.type} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center py-3 border-b border-border last:border-0">
                                        <div className="md:col-span-4">
                                            <p className="text-sm font-medium text-text-primary">{taskType.name}</p>
                                            <p className="text-xs text-text-secondary">{taskType.description}</p>
                                        </div>
                                        <div className="md:col-span-4">
                                            <select
                                                value={selectedProvider}
                                                onChange={(e) => {
                                                    const newProvider = e.target.value
                                                    const models = getModelsForProvider(newProvider)
                                                    handleRouteChange(taskType.type, newProvider, models[0] || '')
                                                }}
                                                className="w-full px-3 py-2 bg-surface rounded-lg border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                            >
                                                {llmProviders?.filter(p => p.has_api_key).map((provider) => (
                                                    <option key={provider.name} value={provider.name}>
                                                        {provider.display_name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="md:col-span-4">
                                            <select
                                                value={selectedModel}
                                                onChange={(e) => {
                                                    handleRouteChange(taskType.type, selectedProvider, e.target.value)
                                                }}
                                                className="w-full px-3 py-2 bg-surface rounded-lg border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                                            >
                                                {getModelsForProvider(selectedProvider).map((model) => (
                                                    <option key={model} value={model}>
                                                        {model}
                                                    </option>
                                                ))}
                                                {getModelsForProvider(selectedProvider).length === 0 && (
                                                    <option value="">Select model...</option>
                                                )}
                                            </select>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
