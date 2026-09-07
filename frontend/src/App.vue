<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  cancelScanJob,
  fetchDashboard,
  fetchFxRates,
  fetchScanJob,
  retryFailedScanTasks,
  runQuickSearch,
  startScanJob,
  type DashboardData,
  type FlightOffer,
  type FxRates,
  type QuickSearchResult,
  type ScanJobStatus,
} from './api/client'
import {
  FALLBACK_CURRENCIES,
  formatMoney,
  loadSavedCurrency,
  saveCurrency,
} from './utils/currency'

type SortKey = 'score' | 'price' | 'duration'
type TabKey = 'quick' | 'monitor'

const tab = ref<TabKey>('quick')
const data = ref<DashboardData | null>(null)
const loading = ref(false)
const error = ref('')
const sort = ref<SortKey>('score')
const selectedDate = ref<string | null>(null)
const airlineOnly = ref(false)

const quickOrigin = ref('BNE')
const quickDest = ref('PVG')
const quickDate = ref('2026-12-18')
const quickMaxStops = ref(1)
const quickLoading = ref(false)
const quickError = ref('')
const quickResult = ref<QuickSearchResult | null>(null)

const fx = ref<FxRates | null>(null)
const fxError = ref('')
const displayCurrency = ref(loadSavedCurrency('AUD'))
const scanJob = ref<ScanJobStatus | null>(null)
let scanPollTimer: number | null = null

const currencyOptions = computed(() => fx.value?.currencies?.length
  ? fx.value.currencies
  : FALLBACK_CURRENCIES)

const scanRunning = computed(() =>
  !!scanJob.value && ['pending', 'running'].includes(scanJob.value.status),
)

watch(displayCurrency, (code) => saveCurrency(code))

function stopScanPoll() {
  if (scanPollTimer != null) {
    window.clearInterval(scanPollTimer)
    scanPollTimer = null
  }
}

function isTerminalScan(status: string) {
  return ['completed', 'cancelled', 'failed'].includes(status)
}

async function refreshScanJob(jobId: number) {
  scanJob.value = await fetchScanJob(jobId)
  if (isTerminalScan(scanJob.value.status)) {
    stopScanPoll()
    loading.value = false
    await load()
  }
}

function startScanPoll(jobId: number) {
  stopScanPoll()
  scanPollTimer = window.setInterval(() => {
    refreshScanJob(jobId).catch((err) => {
      error.value = err instanceof Error ? err.message : String(err)
      stopScanPoll()
      loading.value = false
    })
  }, 1200)
}

async function scanNow() {
  loading.value = true
  error.value = ''
  try {
    scanJob.value = await startScanJob()
    startScanPoll(scanJob.value.id)
    await refreshScanJob(scanJob.value.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    loading.value = false
  }
}

async function cancelScan() {
  if (!scanJob.value) return
  error.value = ''
  try {
    scanJob.value = await cancelScanJob(scanJob.value.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function retryFailed() {
  if (!scanJob.value) return
  loading.value = true
  error.value = ''
  try {
    scanJob.value = await retryFailedScanTasks(scanJob.value.id)
    startScanPoll(scanJob.value.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    loading.value = false
  }
}

function taskStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '等待',
    running: '进行中',
    succeeded: '成功',
    failed: '失败',
    cancelled: '取消',
  }
  return map[status] || status
}

function money(
  amount: number | null | undefined,
  fromCurrency: string | undefined | null,
) {
  return formatMoney(amount, fromCurrency || 'AUD', displayCurrency.value, fx.value)
}

async function loadFx() {
  fxError.value = ''
  try {
    fx.value = await fetchFxRates()
    if (!currencyOptions.value.includes(displayCurrency.value)) {
      displayCurrency.value = 'AUD'
    }
  } catch (err) {
    fxError.value = err instanceof Error ? err.message : String(err)
  }
}

async function load() {
  error.value = ''
  try {
    data.value = await fetchDashboard()
    if (data.value.latest_job && !scanJob.value) {
      scanJob.value = data.value.latest_job
      if (['pending', 'running'].includes(data.value.latest_job.status)) {
        loading.value = true
        startScanPoll(data.value.latest_job.id)
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function submitQuickSearch() {
  quickLoading.value = true
  quickError.value = ''
  try {
    quickResult.value = await runQuickSearch({
      origin: quickOrigin.value.trim().toUpperCase(),
      dest: quickDest.value.trim().toUpperCase(),
      depart_date: quickDate.value,
      max_stops: Number(quickMaxStops.value),
      connecting_limit: 3,
    })
  } catch (err) {
    quickError.value = err instanceof Error ? err.message : String(err)
  } finally {
    quickLoading.value = false
  }
}

function toggleDate(date: string) {
  selectedDate.value = selectedDate.value === date ? null : date
}

const visibleOffers = computed(() => {
  let rows = data.value?.offers ?? []
  if (selectedDate.value) {
    rows = rows.filter((item) => item.depart_date === selectedDate.value)
  }
  rows = [...rows].sort((a, b) => {
    if (sort.value === 'price') {
      const pa = money(a.price, a.currency).value ?? a.price
      const pb = money(b.price, b.currency).value ?? b.price
      return pa - pb
    }
    if (sort.value === 'duration') return a.duration_min - b.duration_min
    return b.score - a.score
  })
  return rows.slice(0, 30)
})

function bookingLinks(offer: FlightOffer) {
  const options = offer.booking_options ?? []
  const filtered = airlineOnly.value ? options.filter((item) => item.airline) : options
  if (filtered.length) return filtered.slice(0, 3)
  if (offer.booking_url) {
    return [{ book_with: 'Google Flights', price: offer.price, airline: false, url: offer.booking_url }]
  }
  return []
}

function fmtTime(value?: string | null) {
  if (!value) return '尚未扫描'
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return value
  }
}

const priceBounds = computed(() => {
  const prices = (data.value?.calendar ?? [])
    .map((cell) => {
      if (cell.min_price == null) return null
      const from = data.value?.offers.find((o) => o.offer_id === cell.offer_id)?.currency
        || data.value?.config.currency
        || 'AUD'
      return money(cell.min_price, from).value
    })
    .filter((value): value is number => value != null)
  if (!prices.length) return { min: 0, max: 1 }
  return { min: Math.min(...prices), max: Math.max(...prices) }
})

function dayStyle(minPrice: number | null) {
  if (minPrice == null) return undefined
  const from = data.value?.config.currency || 'AUD'
  const converted = money(minPrice, from).value
  if (converted == null) return undefined
  const { min, max } = priceBounds.value
  const t = (converted - min) / Math.max(max - min, 1)
  return { background: `rgba(232, 184, 109, ${0.12 + (1 - t) * 0.45})` }
}

function durationLabel(mins: number) {
  return `${Math.floor(mins / 60)}h${String(mins % 60).padStart(2, '0')}m`
}

function viaLabel(offer: FlightOffer) {
  const vias = offer.segments.slice(0, -1).map((s) => s.dest)
  return vias.length ? vias.join(' / ') : '直飞'
}

onMounted(async () => {
  await Promise.all([loadFx(), load()])
})
</script>

<template>
  <div class="sky">
    <header class="topbar">
      <div>
        <p class="kicker">Return flight radar</p>
        <h1>回国机票雷达</h1>
      </div>
      <div class="top-controls">
        <label class="currency-switch">
          显示货币
          <select v-model="displayCurrency">
            <option v-for="code in currencyOptions" :key="code" :value="code">{{ code }}</option>
          </select>
        </label>
        <div class="tabs">
          <button type="button" class="chip" :class="{ active: tab === 'quick' }" @click="tab = 'quick'">快捷查询</button>
          <button type="button" class="chip" :class="{ active: tab === 'monitor' }" @click="tab = 'monitor'">监测看板</button>
        </div>
      </div>
    </header>

    <p v-if="fx" class="fx-note">
      汇率 {{ fx.date }} · {{ fx.source }}
      <template v-if="fxError"> · {{ fxError }}</template>
    </p>
    <p v-else-if="fxError" class="error">汇率加载失败：{{ fxError }}（暂按原币种显示）</p>

    <section v-if="tab === 'quick'" class="panel">
      <div class="panel-head">
        <div>
          <h2>快捷查询</h2>
          <p>按出发/到达/日期查：最便宜直飞 1 班 + 转机最便宜前 3 班。价格可切换显示货币。</p>
        </div>
      </div>

      <form class="quick-form" @submit.prevent="submitQuickSearch">
        <label>
          出发
          <input v-model="quickOrigin" maxlength="3" placeholder="BNE" required />
        </label>
        <label>
          到达
          <input v-model="quickDest" maxlength="3" placeholder="PVG" required />
        </label>
        <label>
          日期
          <input v-model="quickDate" type="date" required />
        </label>
        <label>
          最多中转
          <select v-model.number="quickMaxStops">
            <option :value="0">只要直飞</option>
            <option :value="1">直飞 + 1 次转机</option>
            <option :value="2">最多 2 次转机</option>
          </select>
        </label>
        <button type="submit" :disabled="quickLoading">
          {{ quickLoading ? '查询中…' : '查询' }}
        </button>
      </form>

      <p v-if="quickError" class="error">{{ quickError }}</p>

      <div v-if="quickResult" class="quick-results">
        <p class="sub">
          {{ quickResult.query.origin }} → {{ quickResult.query.dest }} ·
          {{ quickResult.query.depart_date }} · {{ quickResult.query.provider }} ·
          共 {{ quickResult.summary.total }} 条
          （直飞 {{ quickResult.summary.direct_count }} /
          转机 {{ quickResult.summary.connecting_count }}）
        </p>

        <h3>最便宜直飞</h3>
        <article v-if="quickResult.cheapest_direct" class="ticket">
          <div>
            <div class="price">
              {{ money(quickResult.cheapest_direct.price, quickResult.cheapest_direct.currency).primary }}
            </div>
            <div v-if="money(quickResult.cheapest_direct.price, quickResult.cheapest_direct.currency).secondary" class="sub">
              {{ money(quickResult.cheapest_direct.price, quickResult.cheapest_direct.currency).secondary }}
            </div>
            <div class="sub">直飞 · {{ durationLabel(quickResult.cheapest_direct.duration_min) }}</div>
          </div>
          <div>
            <p class="route">{{ quickResult.cheapest_direct.origin }} → {{ quickResult.cheapest_direct.dest }}</p>
            <div class="sub">
              {{ quickResult.cheapest_direct.segments.map((s) => s.flight_no).join('+') }}
            </div>
          </div>
          <div class="links">
            <a
              v-for="(opt, i) in bookingLinks(quickResult.cheapest_direct)"
              :key="i"
              class="book"
              :href="opt.url"
              target="_blank"
              rel="noreferrer"
            >
              {{ opt.airline ? '航司' : '渠道' }} · {{ opt.book_with }}
              <template v-if="opt.price != null">
                · {{ money(opt.price, quickResult.cheapest_direct.currency).primary }}
              </template>
            </a>
          </div>
        </article>
        <p v-else class="empty-note">这一天没有直飞（或已售罄）。</p>

        <template v-if="quickMaxStops >= 1">
          <h3>最便宜转机 TOP3（最多 {{ quickMaxStops }} 停）</h3>
          <article
            v-for="offer in quickResult.cheapest_connecting"
            :key="offer.offer_id"
            class="ticket"
          >
            <div>
              <div class="price">{{ money(offer.price, offer.currency).primary }}</div>
              <div v-if="money(offer.price, offer.currency).secondary" class="sub">
                {{ money(offer.price, offer.currency).secondary }}
              </div>
              <div class="sub">{{ offer.stops }} 停 · {{ durationLabel(offer.duration_min) }}</div>
            </div>
            <div>
              <p class="route">{{ offer.origin }} → {{ offer.dest }}</p>
              <div class="sub">
                经 {{ viaLabel(offer) }} · {{ offer.segments.map((s) => s.flight_no).join('+') }}
              </div>
            </div>
            <div class="links">
              <a
                v-for="(opt, i) in bookingLinks(offer)"
                :key="i"
                class="book"
                :href="opt.url"
                target="_blank"
                rel="noreferrer"
              >
                {{ opt.airline ? '航司' : '渠道' }} · {{ opt.book_with }}
                <template v-if="opt.price != null">
                  · {{ money(opt.price, offer.currency).primary }}
                </template>
              </a>
            </div>
          </article>
          <p v-if="!quickResult.cheapest_connecting.length" class="empty-note">没有符合中转次数的航班。</p>
        </template>
      </div>
    </section>

    <template v-else>
      <div v-if="!data" class="panel">
        <p class="empty-note">{{ error || '加载监测数据中…' }}</p>
      </div>
      <template v-else>
        <div class="top-actions monitor-bar">
          <p class="meta">
            {{ fmtTime(data.snapshot?.scanned_at) }} · {{ data.config.provider }} ·
            {{ data.snapshot?.offer_count ?? 0 }} 条
          </p>
          <div class="monitor-actions">
            <button
              v-if="scanRunning"
              type="button"
              class="chip"
              @click="cancelScan"
            >
              取消扫票
            </button>
            <button
              v-if="scanJob && scanJob.progress.failed > 0 && !scanRunning"
              type="button"
              class="chip"
              @click="retryFailed"
            >
              重试失败（{{ scanJob.progress.failed }}）
            </button>
            <button type="button" :disabled="loading || scanRunning" @click="scanNow">
              {{ scanRunning ? '扫描中…' : '立刻扫票' }}
            </button>
          </div>
        </div>

        <section v-if="scanJob" class="panel scan-progress">
          <div class="panel-head">
            <div>
              <h2>扫票进度 #{{ scanJob.id }}</h2>
              <p>
                {{ scanJob.status }} · {{ scanJob.progress.done }}/{{ scanJob.progress.total }}
                （成功 {{ scanJob.progress.succeeded }} / 失败 {{ scanJob.progress.failed }}）
                <template v-if="scanJob.error_message"> · {{ scanJob.error_message }}</template>
              </p>
            </div>
            <strong>{{ scanJob.progress.percent }}%</strong>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${scanJob.progress.percent}%` }" />
          </div>
          <div class="task-list">
            <div
              v-for="task in scanJob.tasks"
              :key="task.id"
              class="task-row"
              :class="task.status"
            >
              <span>{{ task.origin }}→{{ task.dest }} {{ task.depart_date }}</span>
              <span>{{ taskStatusLabel(task.status) }} · {{ task.offer_count }} 条</span>
              <span v-if="task.error_message" class="error">{{ task.error_message }}</span>
            </div>
          </div>
        </section>

        <p v-if="error" class="error">{{ error }}</p>

        <section class="stats">
          <article class="stat">
            <span>预算</span>
            <strong>{{ money(data.config.budget, data.config.currency).primary }}</strong>
            <div v-if="money(data.config.budget, data.config.currency).secondary" class="sub">
              {{ money(data.config.budget, data.config.currency).secondary }}
            </div>
          </article>
          <article class="stat">
            <span>日期</span>
            <strong>{{ data.config.date_from }} → {{ data.config.date_to }}</strong>
          </article>
          <article class="stat">
            <span>最合适</span>
            <strong v-if="data.best">
              {{ data.best.origin }}→{{ data.best.dest }}
              {{ money(data.best.price, data.best.currency).primary }}
            </strong>
            <strong v-else>暂无</strong>
          </article>
          <article class="stat">
            <span>最便宜</span>
            <strong v-if="data.cheapest">
              {{ data.cheapest.origin }}→{{ data.cheapest.dest }}
              {{ money(data.cheapest.price, data.cheapest.currency).primary }}
            </strong>
            <strong v-else>暂无</strong>
          </article>
        </section>

        <section v-if="data.alerts.length" class="alerts">
          <div v-for="(alert, idx) in data.alerts.slice(0, 5)" :key="idx" class="alert-card">
            {{ alert.message }}
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>价格日历</h2>
              <p>颜色越暖越便宜。点某一天可筛航班。金额按当前显示货币换算。</p>
            </div>
          </div>
          <div class="calendar">
            <button
              v-for="cell in data.calendar"
              :key="cell.date"
              type="button"
              class="day"
              :class="{ active: selectedDate === cell.date, empty: cell.min_price == null }"
              :disabled="cell.min_price == null"
              :style="dayStyle(cell.min_price)"
              @click="cell.min_price != null && toggleDate(cell.date)"
            >
              <span>{{ cell.date.slice(8) }}<template v-if="cell.origin"> · {{ cell.origin }}→{{ cell.dest }}</template></span>
              <b>
                {{
                  cell.min_price == null
                    ? '—'
                    : Math.round(money(cell.min_price, data.config.currency).value ?? cell.min_price)
                }}
              </b>
            </button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>合适航班</h2>
              <label class="toggle">
                <input v-model="airlineOnly" type="checkbox" />
                只显示航司购买渠道
              </label>
            </div>
            <div class="sorts">
              <button type="button" class="chip" :class="{ active: sort === 'score' }" @click="sort = 'score'">性价比</button>
              <button type="button" class="chip" :class="{ active: sort === 'price' }" @click="sort = 'price'">最便宜</button>
              <button type="button" class="chip" :class="{ active: sort === 'duration' }" @click="sort = 'duration'">最快</button>
            </div>
          </div>

          <div v-if="!visibleOffers.length" class="empty-note">还没有航班。点右上角扫描，或换一天看看。</div>
          <article v-for="offer in visibleOffers" :key="offer.offer_id" class="ticket">
            <div>
              <div class="price">{{ money(offer.price, offer.currency).primary }}</div>
              <div v-if="money(offer.price, offer.currency).secondary" class="sub">
                {{ money(offer.price, offer.currency).secondary }}
              </div>
              <div class="sub">得分 {{ offer.score }}</div>
            </div>
            <div>
              <p class="route">{{ offer.origin }} → {{ offer.dest }}</p>
              <div class="sub">
                {{ offer.depart_date }} · {{ offer.stops }} 停 · {{ durationLabel(offer.duration_min) }} ·
                经 {{ viaLabel(offer) }}
              </div>
              <div class="badges">
                <span
                  v-for="badge in offer.badges"
                  :key="badge"
                  class="badge"
                  :class="{ good: badge === '低于预算' || badge === '性价比高' }"
                >{{ badge }}</span>
              </div>
            </div>
            <div class="links">
              <a
                v-for="(opt, i) in bookingLinks(offer)"
                :key="i"
                class="book"
                :href="opt.url"
                target="_blank"
                rel="noreferrer"
              >
                {{ opt.airline ? '航司' : '渠道' }} · {{ opt.book_with }}
                <template v-if="opt.price != null">
                  · {{ money(opt.price, offer.currency).primary }}
                </template>
              </a>
            </div>
          </article>
        </section>
      </template>
    </template>
  </div>
</template>
