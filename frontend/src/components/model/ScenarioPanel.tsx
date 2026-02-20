import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, Target } from 'lucide-react'
import { getScenarios, getScenarioSummary } from '@/services/model'
import { formatCurrency } from '@/utils/format'

interface ScenarioPanelProps {
  ticker: string
}

export default function ScenarioPanel({ ticker }: ScenarioPanelProps) {
  const { data: scenarios } = useQuery({
    queryKey: ['scenarios', ticker],
    queryFn: () => getScenarios(ticker).then((res) => res.data),
  })

  const { data: summary } = useQuery({
    queryKey: ['scenario-summary', ticker],
    queryFn: () => getScenarioSummary(ticker).then((res) => res.data),
  })

  const getScenarioIcon = (caseType: string) => {
    switch (caseType) {
      case 'bull':
        return <TrendingUp className="w-5 h-5 text-success" />
      case 'bear':
        return <TrendingDown className="w-5 h-5 text-danger" />
      default:
        return <Minus className="w-5 h-5 text-accent" />
    }
  }

  const getScenarioColor = (caseType: string) => {
    switch (caseType) {
      case 'bull':
        return 'border-success/30 bg-success/5'
      case 'bear':
        return 'border-danger/30 bg-danger/5'
      default:
        return 'border-accent/30 bg-accent/5'
    }
  }

  const getScenarioTitleColor = (caseType: string) => {
    switch (caseType) {
      case 'bull':
        return 'text-success'
      case 'bear':
        return 'text-danger'
      default:
        return 'text-accent'
    }
  }

  const sortedScenarios = scenarios
    ? [...scenarios].sort((a, b) => {
      const order = { bull: 0, base: 1, bear: 2 }
      return (order[a.case_type as keyof typeof order] ?? 1) - (order[b.case_type as keyof typeof order] ?? 1)
    })
    : []

  return (
    <div className="space-y-4">
      {/* Weighted Target */}
      {summary && (
        <div className="bg-surface-card rounded-lg p-4 border border-border">
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-5 h-5 text-accent" />
            <span className="text-sm text-text-secondary">Weighted Target Price</span>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatCurrency(summary.target_price)}</p>
        </div>
      )}

      {/* Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {sortedScenarios.map((scenario) => (
          <div
            key={scenario.id}
            className={`rounded-lg p-4 border ${getScenarioColor(scenario.case_type)}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {getScenarioIcon(scenario.case_type)}
                <span className={`font-semibold capitalize ${getScenarioTitleColor(scenario.case_type)}`}>
                  {scenario.case_type}
                </span>
              </div>
              <span className="text-sm text-text-muted">{Math.round(scenario.probability * 100)}%</span>
            </div>

            <div className="space-y-2">
              <div>
                <p className="text-xs text-text-muted">Implied Value</p>
                <p className="text-xl font-bold text-text-primary">
                  {scenario.dcf_per_share ? formatCurrency(scenario.dcf_per_share) : '—'}
                </p>
              </div>

              <div className="pt-2 border-t border-border/30">
                <p className="text-xs text-text-muted mb-1">{scenario.name}</p>
              </div>
            </div>
          </div>
        ))}

        {/* Empty State */}
        {!scenarios || scenarios.length === 0 ? (
          <div className="col-span-3 text-center py-8 text-text-secondary bg-surface-card rounded-lg">
            No scenarios configured yet
          </div>
        ) : null}
      </div>

      {/* Probability Distribution Bar */}
      {scenarios && scenarios.length > 0 && (
        <div className="bg-surface-card rounded-lg p-4 border border-border">
          <p className="text-sm text-text-secondary mb-3">Probability Distribution</p>
          <div className="h-4 w-full rounded-full overflow-hidden flex">
            {scenarios
              .sort((a, b) => {
                const order = { bull: 0, base: 1, bear: 2 }
                return (order[a.case_type as keyof typeof order] ?? 1) - (order[b.case_type as keyof typeof order] ?? 1)
              })
              .map((scenario) => (
                <div
                  key={scenario.id}
                  className={`h-full ${scenario.case_type === 'bull'
                      ? 'bg-success'
                      : scenario.case_type === 'bear'
                        ? 'bg-danger'
                        : 'bg-accent'
                    }`}
                  style={{ width: `${scenario.probability * 100}%` }}
                  title={`${scenario.case_type}: ${Math.round(scenario.probability * 100)}%`}
                />
              ))}
          </div>
          <div className="flex justify-between mt-2 text-xs">
            <span className="text-success">Bullish</span>
            <span className="text-accent">Base</span>
            <span className="text-danger">Bearish</span>
          </div>
        </div>
      )}
    </div>
  )
}
