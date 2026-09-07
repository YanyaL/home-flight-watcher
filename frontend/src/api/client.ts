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

export interface ScanTaskStatus {
  id: number
  origin: string
  dest: string
  depart_date: string
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled' | string
  offer_count: number
  error_message: string
  started_at?: string | null
  finished_at?: string | null
}

export interface ScanJobStatus {
  id: number
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed' | string
  provider: string
  cancel_requested: boolean
  attach_bookings: boolean
  offer_count: number
  error_message: string
  created_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  snapshot_id?: number | null
  progress: {
    total: number
    done: number
    percent: number
    pending: number
    running: number
    succeeded: number
    failed: number
    cancelled: number
  }
  tasks: ScanTaskStatus[]
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
  latest_job?: ScanJobStatus | null
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

export async function startScanJob(): Promise<ScanJobStatus> {
  const res = await fetch('/api/scan', { method: 'POST' })
  const payload = await res.json().catch(() => ({}))
  if (!res.ok && res.status !== 202) {
    throw new Error(payload.detail || `scan ${res.status}`)
  }
  return payload
}

export async function fetchScanJob(jobId: number): Promise<ScanJobStatus> {
  const res = await fetch(`/api/scan/${jobId}`)
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(payload.detail || `scan ${res.status}`)
  return payload
}

export async function cancelScanJob(jobId: number): Promise<ScanJobStatus> {
  const res = await fetch(`/api/scan/${jobId}/cancel`, { method: 'POST' })
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(payload.detail || `cancel ${res.status}`)
  return payload
}

export async function retryFailedScanTasks(jobId: number): Promise<ScanJobStatus> {
  const res = await fetch(`/api/scan/${jobId}/retry`, { method: 'POST' })
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(payload.detail || `retry ${res.status}`)
  return payload
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
