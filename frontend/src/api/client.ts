export interface BookingOption {
  book_with?: string
  price?: number | null
  airline?: boolean
  url: string
}

export interface Segment {
  origin: string
  dest: string
  depart: string
  arrive: string
  airline: string
  flight_no: string
}

export interface FlightOffer {
  offer_id: string
  origin: string
  dest: string
  depart_date: string
  price: number
  currency: string
  stops: number
  duration_min: number
  airlines: string[]
  segments: Segment[]
  provider: string
  booking_url: string
  booking_options: BookingOption[]
  score: number
  badges: string[]
}

export interface CalendarCell {
  date: string
  min_price: number | null
  offer_id?: string | null
  origin?: string | null
  dest?: string | null
  stops?: number | null
}

export interface DashboardData {
  config: {
    origins: string[]
    destinations: string[]
    date_from: string
    date_to: string
    budget: number
    currency: string
    cabin: string
    max_stops: number
    provider: string
  }
  snapshot: {
    id: number
    scanned_at: string
    provider: string
    offer_count: number
  } | null
  calendar: CalendarCell[]
  offers: FlightOffer[]
  cheapest: FlightOffer | null
  best: FlightOffer | null
  alerts: Array<{
    created_at: string
    kind: string
    message: string
    offer_id?: string | null
    price?: number | null
  }>
}

export interface QuickSearchRequest {
  origin: string
  dest: string
  depart_date: string
  max_stops: number
  connecting_limit?: number
  currency?: string
}

export interface QuickSearchResult {
  query: {
    origin: string
    dest: string
    depart_date: string
    max_stops: number
    connecting_limit: number
    currency: string
    provider: string
  }
  summary: {
    total: number
    direct_count: number
    connecting_count: number
  }
  cheapest_direct: FlightOffer | null
  cheapest_connecting: FlightOffer[]
}

export interface FxRates {
  base: string
  date: string
  source: string
  provider_url?: string
  currencies: string[]
  rates: Record<string, number>
  fetched_at?: string
}

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch('/api/dashboard')
  if (!res.ok) throw new Error(`dashboard ${res.status}`)
  return res.json()
}

export async function triggerScan(): Promise<DashboardData> {
  const res = await fetch('/api/scan', { method: 'POST' })
  if (!res.ok) throw new Error(`scan ${res.status}`)
  return res.json()
}

export async function runQuickSearch(body: QuickSearchRequest): Promise<QuickSearchResult> {
  const res = await fetch('/api/quick-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(payload.detail || `quick-search ${res.status}`)
  }
  return payload
}

export async function fetchFxRates(refresh = false): Promise<FxRates> {
  const q = refresh ? '?refresh=1' : ''
  const res = await fetch(`/api/fx-rates${q}`)
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(payload.detail || `fx-rates ${res.status}`)
  }
  return payload
}
