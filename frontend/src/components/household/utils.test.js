import { describe, it, expect } from 'vitest'
import {
  formatDateInput,
  addDays,
  getHouseholdAgendaBuckets,
  getHouseholdReminderSummary,
  formatFrequencyLabel,
  getOccurrenceUrgency,
} from './utils.js'

describe('formatDateInput', () => {
  it('formats date as YYYY-MM-DD', () => {
    expect(formatDateInput(new Date(2026, 4, 22))).toBe('2026-05-22')
  })

  it('pads single-digit month and day with zeros', () => {
    expect(formatDateInput(new Date(2026, 0, 5))).toBe('2026-01-05')
  })

  it('handles December correctly', () => {
    expect(formatDateInput(new Date(2026, 11, 31))).toBe('2026-12-31')
  })
})

describe('addDays', () => {
  it('adds positive days', () => {
    const base = new Date(2026, 4, 20)
    expect(formatDateInput(addDays(base, 5))).toBe('2026-05-25')
  })

  it('subtracts days with negative value', () => {
    const base = new Date(2026, 4, 20)
    expect(formatDateInput(addDays(base, -5))).toBe('2026-05-15')
  })

  it('crosses month boundary correctly', () => {
    const base = new Date(2026, 4, 28)
    expect(formatDateInput(addDays(base, 5))).toBe('2026-06-02')
  })

  it('does not mutate the base date', () => {
    const base = new Date(2026, 4, 20)
    addDays(base, 10)
    expect(formatDateInput(base)).toBe('2026-05-20')
  })
})

// Fixed test date to make assertions deterministic
const TODAY = '2026-05-22'

const OCCURRENCES = [
  { id: 1, due_date: '2026-05-20', status: 'pending' },  // overdue
  { id: 2, due_date: '2026-05-22', status: 'pending' },  // today
  { id: 3, due_date: '2026-05-23', status: 'pending' },  // tomorrow
  { id: 4, due_date: '2026-05-26', status: 'pending' },  // upcoming (within 7 days)
  { id: 5, due_date: '2026-05-30', status: 'pending' },  // beyond 7-day window
  { id: 6, due_date: '2026-05-21', status: 'done' },     // resolved
  { id: 7, due_date: '2026-05-18', status: 'skipped' },  // resolved
]

describe('getHouseholdAgendaBuckets', () => {
  it('puts past pending items in overdue', () => {
    const { overdue } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    expect(overdue).toHaveLength(1)
    expect(overdue[0].id).toBe(1)
  })

  it('puts same-day pending items in today', () => {
    const { today } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    expect(today).toHaveLength(1)
    expect(today[0].id).toBe(2)
  })

  it('puts next-day pending items in tomorrow', () => {
    const { tomorrow } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    expect(tomorrow).toHaveLength(1)
    expect(tomorrow[0].id).toBe(3)
  })

  it('puts items within 7-day window in upcoming', () => {
    const { upcoming } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    // tomorrow (May 23) also qualifies for upcoming per the filter logic
    expect(upcoming.map((i) => i.id)).toContain(4)
  })

  it('excludes items beyond the 7-day window from upcoming', () => {
    const { upcoming } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    expect(upcoming.map((i) => i.id)).not.toContain(5)
  })

  it('puts non-pending items in resolvedRecent', () => {
    const { resolvedRecent } = getHouseholdAgendaBuckets(OCCURRENCES, TODAY)
    expect(resolvedRecent).toHaveLength(2)
    expect(resolvedRecent.map((i) => i.id)).toContain(6)
    expect(resolvedRecent.map((i) => i.id)).toContain(7)
  })

  it('limits resolvedRecent to 8 items', () => {
    const manyDone = Array.from({ length: 12 }, (_, i) => ({
      id: 100 + i,
      due_date: `2026-05-${String(i + 1).padStart(2, '0')}`,
      status: 'done',
      completed_at: null,
    }))
    const { resolvedRecent } = getHouseholdAgendaBuckets(manyDone, TODAY)
    expect(resolvedRecent).toHaveLength(8)
  })

  it('returns empty buckets for empty occurrences list', () => {
    const buckets = getHouseholdAgendaBuckets([], TODAY)
    expect(buckets.overdue).toHaveLength(0)
    expect(buckets.today).toHaveLength(0)
    expect(buckets.tomorrow).toHaveLength(0)
    expect(buckets.upcoming).toHaveLength(0)
    expect(buckets.resolvedRecent).toHaveLength(0)
  })
})

describe('getHouseholdReminderSummary', () => {
  it('counts urgentCount as overdue + today + tomorrow', () => {
    const { urgentCount } = getHouseholdReminderSummary(OCCURRENCES, TODAY)
    expect(urgentCount).toBe(3) // id:1 (overdue) + id:2 (today) + id:3 (tomorrow)
  })

  it('caps urgentItems at 3 entries', () => {
    const { urgentItems } = getHouseholdReminderSummary(OCCURRENCES, TODAY)
    expect(urgentItems.length).toBeLessThanOrEqual(3)
  })

  it('excludes tomorrow from weekUpcoming', () => {
    const { weekUpcoming } = getHouseholdReminderSummary(OCCURRENCES, TODAY)
    expect(weekUpcoming.some((i) => i.due_date === '2026-05-23')).toBe(false)
  })

  it('includes upcoming-but-not-tomorrow items in weekUpcoming', () => {
    const { weekUpcoming } = getHouseholdReminderSummary(OCCURRENCES, TODAY)
    expect(weekUpcoming.map((i) => i.id)).toContain(4)
  })
})

describe('formatFrequencyLabel', () => {
  it('returns "Diaria" for daily interval 1', () => {
    expect(formatFrequencyLabel({ frequency_type: 'daily', interval: 1 })).toBe('Diaria')
  })

  it('returns "Cada N dias" for daily interval > 1', () => {
    expect(formatFrequencyLabel({ frequency_type: 'daily', interval: 3 })).toBe('Cada 3 dias')
  })

  it('returns "Semanal" for weekly interval 1', () => {
    expect(formatFrequencyLabel({ frequency_type: 'weekly', interval: 1 })).toBe('Semanal')
  })

  it('returns "Cada N semanas" for weekly interval > 1', () => {
    expect(formatFrequencyLabel({ frequency_type: 'weekly', interval: 2 })).toBe('Cada 2 semanas')
  })

  it('returns "Mensual, dia N" for monthly with day_of_month', () => {
    expect(formatFrequencyLabel({ frequency_type: 'monthly', interval: 1, day_of_month: 15 }))
      .toBe('Mensual, dia 15')
  })

  it('returns "Cada N meses, dia M" for multi-month with day_of_month', () => {
    expect(formatFrequencyLabel({ frequency_type: 'monthly', interval: 3, day_of_month: 10 }))
      .toBe('Cada 3 meses, dia 10')
  })

  it('returns "Mensual" for monthly interval 1 without day_of_month', () => {
    expect(formatFrequencyLabel({ frequency_type: 'monthly', interval: 1 })).toBe('Mensual')
  })

  it('returns "Cada N meses" for monthly interval > 1 without day_of_month', () => {
    expect(formatFrequencyLabel({ frequency_type: 'monthly', interval: 2 })).toBe('Cada 2 meses')
  })
})

describe('getOccurrenceUrgency', () => {
  it('returns "done" for done status', () => {
    expect(getOccurrenceUrgency({ status: 'done', due_date: '2026-05-20' }, TODAY)).toBe('done')
  })

  it('returns "skipped" for skipped status', () => {
    expect(getOccurrenceUrgency({ status: 'skipped', due_date: '2026-05-20' }, TODAY)).toBe('skipped')
  })

  it('returns "overdue" for pending past due_date', () => {
    expect(getOccurrenceUrgency({ status: 'pending', due_date: '2026-05-20' }, TODAY)).toBe('overdue')
  })

  it('returns "today" for pending due today', () => {
    expect(getOccurrenceUrgency({ status: 'pending', due_date: '2026-05-22' }, TODAY)).toBe('today')
  })

  it('returns "upcoming" for pending future due_date', () => {
    expect(getOccurrenceUrgency({ status: 'pending', due_date: '2026-05-25' }, TODAY)).toBe('upcoming')
  })
})
