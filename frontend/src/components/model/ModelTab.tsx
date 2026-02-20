import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calculator, Table2, BarChart3, GitCompare } from 'lucide-react'
import type { AssumptionSet, ModelOutput, DCFResult } from '@/services/model'
import { computeModel, computeDCF, getScenarioSummary } from '@/services/model'
import AssumptionPanel from './AssumptionPanel'
import ProjectionTable from './ProjectionTable'
import ValuationSummary from './ValuationSummary'
import ScenarioPanel from './ScenarioPanel'
import RevenueChart from '@/components/charts/RevenueChart'
import MarginChart from '@/components/charts/MarginChart'
import WaterfallChart from '@/components/charts/WaterfallChart'
import { getWaterfall } from '@/services/model'

interface ModelTabProps {
  ticker: string
}

export default function ModelTab({ ticker }: ModelTabProps) {
  const [activeAssumptionSet, setActiveAssumptionSet] = useState<AssumptionSet | null>(null)
  const [modelOutput, setModelOutput] = useState<ModelOutput | null>(null)
  const [dcfResult, setDcfResult] = useState<DCFResult | null>(null)

  const { data: waterfallData } = useQuery({
    queryKey: ['waterfall', ticker],
    queryFn: () => getWaterfall(ticker).then((res) => res.data),
    enabled: !!modelOutput,
  })

  const { data: scenarioSummary } = useQuery({
    queryKey: ['scenario-summary', ticker],
    queryFn: () => getScenarioSummary(ticker).then((res) => res.data),
  })

  const handleModelComputed = async () => {
    if (!activeAssumptionSet) return
    try {
      const [modelRes, dcfRes] = await Promise.all([
        computeModel(ticker, activeAssumptionSet.id),
        computeDCF(ticker, activeAssumptionSet.id),
      ])
      setModelOutput(modelRes.data)
      setDcfResult(dcfRes.data)
    } catch (error) {
      console.error('Failed to compute model:', error)
    }
  }

  const marginData = modelOutput?.projections.map((p) => ({
    year: p.year,
    gross_margin: activeAssumptionSet?.gross_margin ?? 0,
    operating_margin: activeAssumptionSet?.operating_margin ?? 0,
  })) ?? []

  return (
    <div className="space-y-6">
      {/* Top Section: Assumptions + Valuation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Assumption Panel */}
        <div className="lg:col-span-1 bg-surface-card rounded-lg p-4 border border-border">
          <AssumptionPanel
            ticker={ticker}
            assumptionSet={activeAssumptionSet}
            onAssumptionSetChange={setActiveAssumptionSet}
            onModelComputed={handleModelComputed}
          />
        </div>

        {/* Right: Valuation Summary */}
        <div className="lg:col-span-2">
          <ValuationSummary
            dcfResult={dcfResult}
            scenarioSummary={scenarioSummary ?? null}
            ticker={ticker}
          />
        </div>
      </div>

      {/* Projection Table */}
      <div className="bg-surface-card rounded-lg p-4 border border-border">
        <div className="flex items-center gap-2 mb-4">
          <Table2 className="w-5 h-5 text-accent" />
          <h3 className="text-lg font-semibold text-text-primary">Financial Projections</h3>
        </div>
        <ProjectionTable projections={modelOutput?.projections ?? []} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {modelOutput && (
          <>
            <div className="bg-surface-card rounded-lg p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-accent" />
                <h3 className="text-sm font-semibold text-text-primary">Revenue Projection</h3>
              </div>
              <RevenueChart
                data={modelOutput.projections.map((p) => ({
                  year: p.year,
                  revenue: p.revenue,
                }))}
              />
            </div>

            <div className="bg-surface-card rounded-lg p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <Calculator className="w-5 h-5 text-accent" />
                <h3 className="text-sm font-semibold text-text-primary">Margin Analysis</h3>
              </div>
              <MarginChart data={marginData} />
            </div>
          </>
        )}
      </div>

      {/* Waterfall Chart */}
      {waterfallData && (
        <div className="bg-surface-card rounded-lg p-4 border border-border">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-accent" />
            <h3 className="text-sm font-semibold text-text-primary">Sensitivity Analysis</h3>
          </div>
          <WaterfallChart data={waterfallData.items} />
        </div>
      )}

      {/* Scenarios */}
      <div className="bg-surface-card rounded-lg p-4 border border-border">
        <div className="flex items-center gap-2 mb-4">
          <GitCompare className="w-5 h-5 text-accent" />
          <h3 className="text-lg font-semibold text-text-primary">Scenario Analysis</h3>
        </div>
        <ScenarioPanel ticker={ticker} />
      </div>
    </div>
  )
}
