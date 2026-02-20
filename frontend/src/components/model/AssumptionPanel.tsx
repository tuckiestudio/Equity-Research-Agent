import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Sparkles, Loader2, Save } from 'lucide-react'
import type { AssumptionSet } from '@/services/model'
import {
  getAssumptions,
  generateAssumptions,
  updateAssumption,
  computeModel,
  computeDCF,
} from '@/services/model'


interface AssumptionPanelProps {
  ticker: string
  assumptionSet: AssumptionSet | null
  onAssumptionSetChange: (set: AssumptionSet | null) => void
  onModelComputed: () => void
}

export default function AssumptionPanel({
  ticker,
  assumptionSet,
  onAssumptionSetChange,
  onModelComputed,
}: AssumptionPanelProps) {
  const [editedAssumptions, setEditedAssumptions] = useState<Partial<AssumptionSet>>({})

  const { data: assumptions, isLoading } = useQuery({
    queryKey: ['assumptions', ticker],
    queryFn: () => getAssumptions(ticker).then((res) => res.data),
  })

  const generateMutation = useMutation({
    mutationFn: () => generateAssumptions(ticker),
    onSuccess: (res) => {
      onAssumptionSetChange(res.data)
      setEditedAssumptions(res.data)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<AssumptionSet>) => {
      if (!assumptionSet) throw new Error('No assumption set selected')
      return updateAssumption(assumptionSet.id, data)
    },
    onSuccess: (res) => {
      onAssumptionSetChange(res.data)
      setEditedAssumptions({})
    },
  })

  const computeMutation = useMutation({
    mutationFn: () => {
      if (!assumptionSet) throw new Error('No assumption set selected')
      return Promise.all([
        computeModel(ticker, assumptionSet.id),
        computeDCF(ticker, assumptionSet.id),
      ])
    },
    onSuccess: () => {
      onModelComputed()
    },
  })

  const handleFieldChange = (field: keyof AssumptionSet, value: number) => {
    setEditedAssumptions((prev) => ({ ...prev, [field]: value }))
  }

  const handleSave = () => {
    if (Object.keys(editedAssumptions).length > 0) {
      updateMutation.mutate(editedAssumptions)
    }
  }

  const activeAssumption = assumptionSet || assumptions?.[0]
  const hasChanges = Object.keys(editedAssumptions).length > 0

  const renderInput = (
    label: string,
    field: keyof AssumptionSet,
    value?: number,
    suffix: string = ''
  ) => {
    const rawValue = editedAssumptions[field] ?? value ?? 0
    const displayValue = typeof rawValue === 'number' ? rawValue : 0
    const isPercent = field !== 'projection_years'

    return (
      <div className="space-y-1">
        <label className="text-xs text-text-secondary">{label}</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={isPercent ? displayValue * 100 : displayValue}
            onChange={(e) => {
              const val = parseFloat(e.target.value)
              handleFieldChange(field, isPercent ? val / 100 : val)
            }}
            className="flex-1 bg-surface-card border border-border rounded px-2 py-1 text-sm text-text-primary focus:border-accent outline-none"
            step={isPercent ? 0.1 : 1}
          />
          <span className="text-sm text-text-muted w-8">{suffix || (isPercent ? '%' : '')}</span>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-accent animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Assumptions</h3>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center gap-1.5 text-xs bg-accent/10 hover:bg-accent/20 text-accent px-2 py-1 rounded transition-colors disabled:opacity-50"
        >
          {generateMutation.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Sparkles className="w-3 h-3" />
          )}
          AI Generate
        </button>
      </div>

      {activeAssumption ? (
        <>
          {/* Revenue Growth Rates */}
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Revenue Growth Rates</label>
            <div className="grid grid-cols-3 gap-2">
              {activeAssumption.revenue_growth_rates.slice(0, 5).map((rate, idx) => (
                <div key={idx} className="flex items-center gap-1">
                  <span className="text-xs text-text-muted">Y{idx + 1}</span>
                  <input
                    type="number"
                    value={((editedAssumptions.revenue_growth_rates?.[idx] ?? rate) * 100)}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) / 100
                      const newRates = [...(editedAssumptions.revenue_growth_rates ?? activeAssumption.revenue_growth_rates)]
                      newRates[idx] = val
                      handleFieldChange('revenue_growth_rates', newRates as never)
                    }}
                    className="flex-1 bg-surface-card border border-border rounded px-1 py-0.5 text-xs text-text-primary focus:border-accent outline-none"
                    step={0.1}
                  />
                  <span className="text-xs text-text-muted">%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Key Assumptions */}
          <div className="space-y-3 pt-2 border-t border-border">
            {renderInput('Gross Margin', 'gross_margin', activeAssumption.gross_margin)}
            {renderInput('Operating Margin', 'operating_margin', activeAssumption.operating_margin)}
            {renderInput('WACC', 'wacc', activeAssumption.wacc)}
            {renderInput('Terminal Growth', 'terminal_growth_rate', activeAssumption.terminal_growth_rate)}
            {renderInput('Tax Rate', 'tax_rate', activeAssumption.tax_rate)}
            {renderInput('Capex % Revenue', 'capex_as_pct_revenue', activeAssumption.capex_as_pct_revenue)}
            {renderInput('D&A % Revenue', 'da_as_pct_revenue', activeAssumption.da_as_pct_revenue)}
            {renderInput('Projection Years', 'projection_years', activeAssumption.projection_years, 'yrs')}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleSave}
              disabled={!hasChanges || updateMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 bg-surface-elevated hover:bg-surface-card text-text-primary text-xs py-2 rounded transition-colors disabled:opacity-50"
            >
              <Save className="w-3 h-3" />
              Save
            </button>
            <button
              onClick={() => computeMutation.mutate()}
              disabled={computeMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 bg-accent hover:bg-accent-hover text-white text-xs py-2 rounded transition-colors disabled:opacity-50"
            >
              {computeMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : null}
              Compute Model
            </button>
          </div>
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary mb-2">No assumptions yet</p>
          <p className="text-xs text-text-muted">
            Generate AI assumptions or create manually
          </p>
        </div>
      )}
    </div>
  )
}
