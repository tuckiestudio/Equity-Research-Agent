import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import type { SentimentSummary } from '@/services/news'

interface SentimentChartProps {
  data: SentimentSummary
}

export default function SentimentChart({ data }: SentimentChartProps) {
  const chartData = [
    { name: 'Bullish', value: data.bullish_count, color: '#22c55e' },
    { name: 'Bearish', value: data.bearish_count, color: '#ef4444' },
    { name: 'Neutral', value: data.neutral_count, color: '#64748b' },
  ].filter((d) => d.value > 0)

  return (
    <div className="relative h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={70}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#f1f5f9' }}
            itemStyle={{ color: '#f1f5f9' }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold text-text-primary">
          {(data.avg_impact_score ?? 0).toFixed(1)}
        </span>
        <span className="text-xs text-text-muted">Avg Impact</span>
      </div>
    </div>
  )
}
