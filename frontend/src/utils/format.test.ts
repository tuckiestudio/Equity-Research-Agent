import { describe, it, expect } from 'vitest'
import {
    formatCurrency,
    formatNumber,
    formatPercent,
    formatPercentChange,
    formatDate,
    formatShortDate,
} from '@/utils/format'

describe('formatCurrency', () => {
    it('formats trillions', () => {
        expect(formatCurrency(1.5e12)).toBe('$1.50T')
        expect(formatCurrency(2e12)).toBe('$2.00T')
    })

    it('formats billions', () => {
        expect(formatCurrency(1.23e9)).toBe('$1.23B')
        expect(formatCurrency(500e6)).toBe('$500.0M')
    })

    it('formats millions', () => {
        expect(formatCurrency(5.5e6)).toBe('$5.5M')
    })

    it('formats thousands', () => {
        expect(formatCurrency(1500)).toBe('$1.5K')
        expect(formatCurrency(50000)).toBe('$50.0K')
    })

    it('formats small values with 2 decimals', () => {
        expect(formatCurrency(42.567)).toBe('$42.57')
        expect(formatCurrency(0)).toBe('$0.00')
        expect(formatCurrency(1)).toBe('$1.00')
    })

    it('handles negative values', () => {
        expect(formatCurrency(-1.5e12)).toBe('$-1.50T')
        expect(formatCurrency(-500e6)).toBe('$-500.0M')
        expect(formatCurrency(-42.5)).toBe('$-42.50')
    })
})

describe('formatNumber', () => {
    it('formats trillions without dollar sign', () => {
        expect(formatNumber(2e12)).toBe('2.00T')
    })

    it('formats billions without dollar sign', () => {
        expect(formatNumber(1.5e9)).toBe('1.50B')
    })

    it('formats millions', () => {
        expect(formatNumber(7.8e6)).toBe('7.8M')
    })

    it('formats thousands', () => {
        expect(formatNumber(2500)).toBe('2.5K')
    })

    it('formats small values', () => {
        expect(formatNumber(42.567)).toBe('42.57')
        expect(formatNumber(0)).toBe('0.00')
    })
})

describe('formatPercent', () => {
    it('formats decimal to percentage', () => {
        expect(formatPercent(0.1234)).toBe('12.3%')
        expect(formatPercent(0.5)).toBe('50.0%')
        expect(formatPercent(1)).toBe('100.0%')
    })

    it('formats zero', () => {
        expect(formatPercent(0)).toBe('0.0%')
    })
})

describe('formatPercentChange', () => {
    it('adds + sign for positive values', () => {
        expect(formatPercentChange(0.05)).toBe('+5.0%')
        expect(formatPercentChange(0.125)).toBe('+12.5%')
    })

    it('includes - sign for negative values', () => {
        expect(formatPercentChange(-0.03)).toBe('-3.0%')
    })

    it('formats zero with + sign', () => {
        expect(formatPercentChange(0)).toBe('+0.0%')
    })
})

describe('formatDate', () => {
    it('formats ISO date string', () => {
        const result = formatDate('2024-01-15T00:00:00Z')
        expect(result).toContain('Jan')
        expect(result).toContain('15')
        expect(result).toContain('2024')
    })
})

describe('formatShortDate', () => {
    it('formats date without year', () => {
        const result = formatShortDate('2024-06-20T00:00:00Z')
        expect(result).toContain('Jun')
        expect(result).toContain('20')
        // Should NOT contain year
        expect(result).not.toContain('2024')
    })
})
