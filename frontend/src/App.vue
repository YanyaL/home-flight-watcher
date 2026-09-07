<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDashboard,
  runQuickSearch,
  triggerScan,
  type DashboardData,
  type FlightOffer,
  type QuickSearchResult,
} from './api/client'

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

async function load() {
  error.value = ''
  try {
    data.value = await fetchDashboard()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function scanNow() {
  loading.value = true
  error.value = ''
  try {
    data.value = await triggerScan()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
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
    if (sort.value === 'price') return a.price - b.price
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
    .map((cell) => cell.min_price)
    .filter((value): value is number => value != null)
  if (!prices.length) return { min: 0, max: 1 }
  return { min: Math.min(...prices), max: Math.max(...prices) }
})

function dayStyle(minPrice: number | null) {
  if (minPrice == null) return undefined
  const { min, max } = priceBounds.value
  const t = (minPrice - min) / Math.max(max - min, 1)
  return { background: `rgba(232, 184, 109, ${0.12 + (1 - t) * 0.45})` }
}

function durationLabel(mins: number) {
  return `${Math.floor(mins / 60)}h${String(mins % 60).padStart(2, '0')}m`
}

function viaLabel(offer: FlightOffer) {
  const vias = offer.segments.slice(0, -1).map((s) => s.dest)
  return vias.length ? vias.join(' / ') : '直飞'
}

onMounted(load)
</script>

<template>
  <div class="sky">
    <header class="topbar">
      <div>
        <p class="kicker">Return flight radar</p>
        <h1>回国机票雷达</h1>
      </div>
      <div class="tabs">
        <button type="button" class="chip" :class="{ active: tab === 'quick' }" @click="tab = 'quick'">快捷查询</button>
        <button type="button" class="chip" :class="{ active: tab === 'monitor' }" @click="tab = 'monitor'">监测看板</button>
      </div>
    </header>

    <section v-if="tab === 'quick'" class="panel">
      <div class="panel-head">
        <div>
          <h2>快捷查询</h2>
          <p>按出发/到达/日期查：最便宜直飞 1 班 + 转机最便宜前 3 班。</p>
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
              {{ Math.round(quickResult.cheapest_direct.price) }}
              <span class="sub">{{ quickResult.cheapest_direct.currency }}</span>
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
              <template v-if="opt.price != null"> · {{ opt.price }}</template>
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
              <div class="price">
                {{ Math.round(offer.price) }}
                <span class="sub">{{ offer.currency }}</span>
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
                <template v-if="opt.price != null"> · {{ opt.price }}</template>
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
          <button type="button" :disabled="loading" @click="scanNow">
            {{ loading ? '扫描中…' : '立刻扫票' }}
          </button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <section class="stats">
          <article class="stat">
            <span>预算</span>
            <strong>{{ data.config.currency }} {{ data.config.budget }}</strong>
          </article>
          <article class="stat">
            <span>日期</span>
            <strong>{{ data.config.date_from }} → {{ data.config.date_to }}</strong>
          </article>
          <article class="stat">
            <span>最合适</span>
            <strong v-if="data.best">{{ data.best.origin }}→{{ data.best.dest }} {{ Math.round(data.best.price) }}</strong>
            <strong v-else>暂无</strong>
          </article>
          <article class="stat">
            <span>最便宜</span>
            <strong v-if="data.cheapest">{{ data.cheapest.origin }}→{{ data.cheapest.dest }} {{ Math.round(data.cheapest.price) }}</strong>
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
              <p>颜色越暖越便宜。点某一天可筛航班。</p>
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
              <b>{{ cell.min_price == null ? '—' : Math.round(cell.min_price) }}</b>
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
              <div class="price">{{ Math.round(offer.price) }} <span class="sub">{{ offer.currency }}</span></div>
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
                <template v-if="opt.price != null"> · {{ opt.price }}</template>
              </a>
            </div>
          </article>
        </section>
      </template>
    </template>
  </div>
</template>
