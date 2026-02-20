import { formatCurrency } from '@/utils/format'
import type { ProjectedFinancials } from '@/services/model'

interface ProjectionTableProps {
  projections: ProjectedFinancials[]
  baseYear?: number
}

export default function ProjectionTable({ projections }: ProjectionTableProps) {
  if (!projections || projections.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        Run model computation to see projections
      </div>
    )
  }

  const rows = [
    { key: 'revenue', label: 'Revenue', format: formatCurrency },
    { key: 'gross_profit', label: 'Gross Profit', format: formatCurrency },
    { key: 'operating_income', label: 'Operating Income', format: formatCurrency },
    { key: 'ebitda', label: 'EBITDA', format: formatCurrency },
    { key: 'net_income', label: 'Net Income', format: formatCurrency },
    { key: 'free_cash_flow', label: 'Free Cash Flow', format: formatCurrency },
    { key: 'eps', label: 'EPS', format: (v: number) => `$${v.toFixed(2)}` },
  ] as const

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-2 px-3 text-text-secondary font-medium">Line Item</th>
            {projections.map((_, idx) => (
              <th key={idx} className="text-right py-2 px-3 text-text-secondary font-medium">
                Year {idx + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr
              key={row.key}
              className={rowIdx % 2 === 0 ? 'bg-surface-card/50' : 'bg-transparent'}
            >
              <td className="py-2.5 px-3 text-text-primary font-medium">{row.label}</td>
              {projections.map((proj, colIdx) => (
                <td key={colIdx} className="text-right py-2.5 px-3 text-text-secondary font-mono">
                  {row.format(proj[row.key as keyof ProjectedFinancials] as number)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
