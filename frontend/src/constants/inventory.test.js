import { describe, it, expect } from 'vitest'
import {
  DEFAULT_INVENTORY_SETTINGS,
  normalizeInventorySettings,
  getCategoryOptions,
  getCategoryLabel,
  isHomeInventoryCategory,
  getTypeForCategory,
  getTypeLabel,
  getBudgetBucketForCategory,
  getBudgetBucketOptions,
  getBudgetBucketLabels,
  requiresExactQuantity,
  getCategoryFallbackUnitCost,
  getUsageFrequencyWeight,
  formatCurrency,
} from './inventory.js'

const S = DEFAULT_INVENTORY_SETTINGS

describe('normalizeInventorySettings', () => {
  it('returns defaults when called with nothing', () => {
    const result = normalizeInventorySettings()
    expect(result.categories).toEqual(S.categories)
    expect(result.currency.code).toBe('PYG')
  })

  it('merges partial payload over defaults', () => {
    const result = normalizeInventorySettings({ currency: { code: 'USD' } })
    expect(result.currency.code).toBe('USD')
    expect(result.currency.locale).toBe(S.currency.locale)
  })

  it('unwraps payload.config', () => {
    const result = normalizeInventorySettings({ config: { monthly_close_day: 10 } })
    expect(result.monthly_close_day).toBe(10)
  })

  it('handles null gracefully', () => {
    const result = normalizeInventorySettings(null)
    expect(result.categories).toEqual(S.categories)
  })

  it('preserves all default top-level keys', () => {
    const result = normalizeInventorySettings({})
    expect(result).toHaveProperty('units')
    expect(result).toHaveProperty('budget_buckets')
    expect(result).toHaveProperty('thresholds')
    expect(result).toHaveProperty('alerts')
  })
})

describe('getCategoryOptions', () => {
  it('returns only inventory-scoped categories', () => {
    const options = getCategoryOptions('inventory', S)
    expect(options.every((c) => c.scope === 'inventory')).toBe(true)
    expect(options.length).toBeGreaterThan(0)
  })

  it('returns only fixed_expense-scoped categories', () => {
    const options = getCategoryOptions('fixed_expense', S)
    expect(options.every((c) => c.scope === 'fixed_expense')).toBe(true)
  })

  it('returns empty array for unknown scope', () => {
    expect(getCategoryOptions('unknown', S)).toHaveLength(0)
  })
})

describe('getCategoryLabel', () => {
  it('returns Spanish label for known category', () => {
    expect(getCategoryLabel('food', S)).toBe('Alimentos')
    expect(getCategoryLabel('cleaning', S)).toBe('Limpieza')
    expect(getCategoryLabel('leisure', S)).toBe('Ocio')
  })

  it('falls back to value for unknown category', () => {
    expect(getCategoryLabel('xyz', S)).toBe('xyz')
  })
})

describe('isHomeInventoryCategory', () => {
  it('returns true for inventory-scoped categories', () => {
    expect(isHomeInventoryCategory('food', S)).toBe(true)
    expect(isHomeInventoryCategory('hygiene', S)).toBe(true)
  })

  it('returns false for non-inventory categories', () => {
    expect(isHomeInventoryCategory('home', S)).toBe(false)
    expect(isHomeInventoryCategory('mobility', S)).toBe(false)
  })
})

describe('getTypeForCategory', () => {
  it('returns correct type for known categories', () => {
    expect(getTypeForCategory('food', S)).toBe('consumable')
    expect(getTypeForCategory('assets', S)).toBe('asset')
    expect(getTypeForCategory('home', S)).toBe('service')
    expect(getTypeForCategory('subscription', S)).toBe('subscription')
  })

  it('defaults to consumable for unknown category', () => {
    expect(getTypeForCategory('unknown', S)).toBe('consumable')
  })
})

describe('getTypeLabel', () => {
  it('returns Spanish label for known types', () => {
    expect(getTypeLabel('consumable')).toBe('Consumible')
    expect(getTypeLabel('service')).toBe('Servicio')
    expect(getTypeLabel('subscription')).toBe('Suscripcion')
    expect(getTypeLabel('asset')).toBe('Activo')
  })

  it('returns value for unknown type', () => {
    expect(getTypeLabel('other')).toBe('other')
  })
})

describe('getBudgetBucketForCategory', () => {
  it('returns correct bucket for known categories', () => {
    expect(getBudgetBucketForCategory('food', S)).toBe('needs')
    expect(getBudgetBucketForCategory('subscription', S)).toBe('wants')
    expect(getBudgetBucketForCategory('leisure', S)).toBe('wants')
  })

  it('defaults to needs for unknown category', () => {
    expect(getBudgetBucketForCategory('unknown', S)).toBe('needs')
  })
})

describe('getBudgetBucketOptions', () => {
  it('formats target_ratio as integer percentage', () => {
    const options = getBudgetBucketOptions(S)
    const needs = options.find((o) => o.value === 'needs')
    const wants = options.find((o) => o.value === 'wants')
    const savings = options.find((o) => o.value === 'savings')
    expect(needs.label).toContain('50%')
    expect(wants.label).toContain('30%')
    expect(savings.label).toContain('20%')
  })

  it('returns one entry per bucket', () => {
    expect(getBudgetBucketOptions(S)).toHaveLength(S.budget_buckets.length)
  })

  it('includes value and label fields', () => {
    const options = getBudgetBucketOptions(S)
    options.forEach((o) => {
      expect(o).toHaveProperty('value')
      expect(o).toHaveProperty('label')
    })
  })
})

describe('getBudgetBucketLabels', () => {
  it('reduces buckets to value→label dict', () => {
    const labels = getBudgetBucketLabels(S)
    expect(labels.needs).toBe('Necesidades')
    expect(labels.wants).toBe('Deseos')
    expect(labels.savings).toBe('Ahorro / deuda')
  })
})

describe('requiresExactQuantity', () => {
  it.each(['kg', 'g', 'l', 'ml'])('returns true for continuous unit "%s"', (unit) => {
    expect(requiresExactQuantity(unit)).toBe(true)
  })

  it.each(['unidad', 'paquete', 'caja', 'botella'])('returns false for discrete unit "%s"', (unit) => {
    expect(requiresExactQuantity(unit)).toBe(false)
  })
})

describe('getCategoryFallbackUnitCost', () => {
  it('returns configured cost as number', () => {
    expect(getCategoryFallbackUnitCost('food', S)).toBe(4.8)
    expect(getCategoryFallbackUnitCost('cleaning', S)).toBe(6.2)
  })

  it('returns 4 for unknown category', () => {
    expect(getCategoryFallbackUnitCost('unknown', S)).toBe(4)
  })
})

describe('getUsageFrequencyWeight', () => {
  it('returns correct weights', () => {
    expect(getUsageFrequencyWeight('high', S)).toBe(1.5)
    expect(getUsageFrequencyWeight('medium', S)).toBe(1)
    expect(getUsageFrequencyWeight('low', S)).toBe(0.65)
  })

  it('defaults to 1 for unknown frequency', () => {
    expect(getUsageFrequencyWeight('other', S)).toBe(1)
  })
})

describe('formatCurrency', () => {
  it('returns a non-empty string', () => {
    const result = formatCurrency(1000, S)
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })

  it('includes the numeric value in output', () => {
    const result = formatCurrency(1000, S)
    // Strip separators to check the number is present regardless of locale grouping
    expect(result.replace(/[\s.,]/g, '')).toContain('1000')
  })

  it('formats 0 for null input', () => {
    const result = formatCurrency(null, S)
    expect(result).toMatch(/\b0\b/)
  })

  it('formats 0 for NaN input', () => {
    const result = formatCurrency(NaN, S)
    expect(result).toMatch(/\b0\b/)
  })

  it('produces same output for null and NaN', () => {
    expect(formatCurrency(null, S)).toBe(formatCurrency(NaN, S))
  })
})
