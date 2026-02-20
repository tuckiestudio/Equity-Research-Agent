import { Download, TrendingUp, TrendingDown, Building2, Coins } from 'lucide-react'
import type { DCFResult, ScenarioSummary } from '@/services/model'
import { formatCurrency, formatPercentChange } from '@/utils/format'
import { exportModel } from '@/services/model'

interface ValuationSummaryProps {
  dcfResult: DCFResult | null
  scenarioSummary: ScenarioSummary | null
  ticker: string
}

export default function ValuationSummary({
  dcfResult,
  scenarioSummary,
  ticker,
}: ValuationSummaryProps) {
  const handleExport = async () => {
    try {
      const response = await exportModel(ticker)
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${ticker}_model.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  if (!dcfResult) {
    return (
      <div className="bg-surface-card rounded-lg p-6 text-center">
        <p className="text-text-secondary">Compute the model to see valuation results</p>
      </div>
    )
  }

  const isPositive = dcfResult.upside_pct >= 0

  return (
    <div className="bg-surface-card rounded-lg p-6 space-y-6">
      {/* Main Value */}
      <div className="text-center pb-6 border-b border-border">
        <p className="text-sm text-text-secondary mb-1">Implied Value per Share</p>
        <p className="text-4xl font-bold text-text-primary">
          {formatCurrency(dcfResult.per_share_value)}
        </p>
        <div className={`flex items-center justify-center gap-1 mt-2 ${isPositive ? 'text-success' : 'text-danger'}`}>
          {isPositive ? (
            <TrendingUp className="w-5 h-5" />
          ) : (
            <TrendingDown className="w-5 h-5" />
          )}
          <span className="text-lg font-semibold">
            {formatPercentChange(dcfResult.upside_pct)}
          </span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface/50 rounded p-3">
          <div className="flex items-center gap-2 text-text-muted mb-1">
            <Building2 className="w-4 h-4" />
            <span className="text-xs">Enterprise Value</span>
          </div>
          <p className="text-text-primary font-semibold">{formatCurrency(dcfResult.enterprise_value)}</p>
        </div>
        <div className="bg-surface/50 rounded p-3">
          <div className="flex items-center gap-2 text-text-muted mb-1">
            <Coins className="w-4 h-4" />
            <span className="text-xs">Equity Value</span>
          </div>
          <p className="text-text-primary font-semibold">{formatCurrency(dcfResult.equity_value)}</p>
        </div>
        <div className="bg-surface/50 rounded p-3">
          <span className="text-xs text-text-muted">WACC</span>
          <p className="text-text-primary font-semibold">{formatPercentChange(dcfResult.wacc)}</p>
        </div>
        <div className="bg-surface/50 rounded p-3">
          <span className="text-xs text-text-muted">Terminal Growth</span>
          <p className="text-text-primary font-semibold">{formatPercentChange(dcfResult.terminal_growth_rate)}</p>
        </div>
      </div>

      {/* Scenario Summary */}
      {scenarioSummary && (
        <div className="pt-4 border-t border-border">
          <p className="text-sm text-text-secondary mb-2">Scenario-Weighted Target Price</p>
          <p className="text-2xl font-bold text-accent">{formatCurrency(scenarioSummary.target_price)}</p>
          <div className="flex gap-2 mt-3">
            {scenarioSummary.scenarios.map((scenario) => (
              <div
                key={scenario.id}
                className={`flex-1 text-center p-2 rounded ${
                  scenario.case_type === 'bull'
                    ? 'bg-success/10'
                    : scenario.case_type === 'bear'
                    ? 'bg-danger/10'
                    : 'bg-accent/10'
                }`}
              >
                <p className="text-xs text-text-muted capitalize">{scenario.case_type}</p>
                <p className={`text-sm font-semibold ${
                  scenario.case_type === 'bull'
                    ? 'text-success'
                    : scenario.case_type === 'bear'
                    ? 'text-danger'
                    : 'text-accent'
                }`}>
                  {scenario.dcf_per_share ? formatCurrency(scenario.dcf_per_share) : '-'}
                </p>
                <p className="text-xs text-text-muted">{Math.round(scenario.probability * 100)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Button */}
      <button
        onClick={handleExport}
        className="w-full flex items-center justify-center gap-2 bg-surface-elevated hover:bg-surface-card text-text-primary py-2 rounded border border-border transition-colors"
      >
        <Download className="w-4 h-4" />
        Export to Excel
      </button>
    </div>
  )
}
