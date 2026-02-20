import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts'
import type { WaterfallItem } from '@/services/model'
import { formatCurrency } from '@/utils/format'

interface WaterfallChartProps {
  data: WaterfallItem[]
}

export default function WaterfallChart({ data }: WaterfallChartProps) {
  // Calculate cumulative values for waterfall effect
  let cumulative = 0
  const chartData = data.map((item) => {
    const start = cumulative
    cumulative += item.impact
    return {
      name: item.assumption_name,
      start,
      impact: item.impact,
      end: cumulative,
      positive: item.impact >= 0,
      value: item.impact,
    }
  })

  // Add final bar
  chartData.push({
    name: 'Total',
    start: 0,
    impact: cumulative,
    end: cumulative,
    positive: cumulative >= 0,
    value: cumulative,
  })

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="name"
            stroke="#64748b"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => formatCurrency(value)}
          />
          <ReferenceLine y={0} stroke="#64748b" strokeWidth={1} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#f1f5f9' }}
            itemStyle={{ color: '#f1f5f9' }}
            formatter={(value: number) => [formatCurrency(value), 'Impact']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  entry.name === 'Total'
                    ? '#6366f1'
                    : entry.positive
                      ? '#22c55e'
                      : '#ef4444'
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
