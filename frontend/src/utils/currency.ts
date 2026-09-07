import type { FxRates } from '../api/client'

const STORAGE_KEY = 'hfw_display_currency'

export const FALLBACK_CURRENCIES = [
  'AUD',
  'CNY',
  'USD',
  'EUR',
  'GBP',
  'HKD',
  'SGD',
  'JPY',
  'NZD',
  'CAD',
]

export function loadSavedCurrency(fallback = 'AUD'): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && /^[A-Z]{3}$/.test(saved)) return saved
  } catch {
    /* ignore */
  }
  return fallback
}

export function saveCurrency(code: string) {
  try {
    localStorage.setItem(STORAGE_KEY, code.toUpperCase())
  } catch {
    /* ignore */
  }
}

/** Convert using EUR-pivot rates from Frankfurter/ECB. */
export function convertAmount(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  fx: FxRates | null,
): number | null {
  const from = fromCurrency.toUpperCase()
  const to = toCurrency.toUpperCase()
  if (from === to) return amount
  if (!fx?.rates) return null
  const fromRate = fx.rates[from]
  const toRate = fx.rates[to]
  if (!fromRate || !toRate) return null
  return (amount / fromRate) * toRate
}

export function formatMoney(
  amount: number | null | undefined,
  fromCurrency: string,
  displayCurrency: string,
  fx: FxRates | null,
): { primary: string; secondary: string | null; value: number | null } {
  if (amount == null || Number.isNaN(Number(amount))) {
    return { primary: '—', secondary: null, value: null }
  }
  const from = fromCurrency.toUpperCase()
  const to = displayCurrency.toUpperCase()
  const converted = convertAmount(Number(amount), from, to, fx)
  if (converted == null) {
    return {
      primary: `${Math.round(Number(amount))} ${from}`,
      secondary: null,
      value: Number(amount),
    }
  }
  const primary = `${Math.round(converted)} ${to}`
  const secondary = from === to ? null : `原价 ${Math.round(Number(amount))} ${from}`
  return { primary, secondary, value: converted }
}
