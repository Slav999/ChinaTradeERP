<template>
  <div class="warehouse-analytics">
    <div class="analytics-header">
      <div>
        <h2 class="analytics-title">{{ $t('Warehouse analytics') }}</h2>
        <div class="analytics-subtitle">{{ subtitle }}</div>
      </div>
      <div class="analytics-totals">
        <div v-for="total in quantityTotals" :key="`quantity-${total.unit}`">
          <span>{{ $t('Quantity') }}{{ total.unit ? `, ${total.unit}` : '' }}</span>
          <strong>{{ isLoading ? '…' : `${formatNumber(total.quantity)}${total.unit ? ` ${total.unit}` : ''}` }}</strong>
        </div>
        <div>
          <span>CNY</span>
          <strong>{{ isLoading ? '…' : `¥ ${formatMoney(totals.total_cny)}` }}</strong>
        </div>
        <div>
          <span>{{ localCurrencyLabel }}</span>
          <strong>{{ isLoading ? '…' : formatMoney(totals.total_local) }}</strong>
        </div>
      </div>
    </div>

    <div v-if="metric === 'quantity' && availableUnits.length > 1" class="analytics-unit-selector">
      <span>{{ $t('Unit') }}</span>
      <div class="btn-group btn-group-sm" role="group" aria-label="Quantity unit">
        <button
            v-for="unit in availableUnits"
            :key="unit || 'unspecified'"
            type="button"
            class="btn"
            :class="selectedUnit === unit ? 'btn-primary' : 'btn-outline-secondary'"
            @click="$emit('select-unit', unit)"
        >
          {{ unit || $t('Unspecified') }}
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="analytics-empty">
      {{ $t('Loading analytics...') }}
    </div>
    <div v-else-if="!items.length" class="analytics-empty">
      {{ $t('No data for the selected filters.') }}
    </div>
    <div v-else-if="items.length === 1" class="analytics-single-product">
      <span v-if="items[0].sku" class="text-muted">{{ items[0].sku }} — </span>{{ items[0].product_name }}
    </div>
    <div v-else class="analytics-chart-scroll" tabindex="0" role="region" aria-label="Warehouse product comparison">
      <div class="analytics-chart-wrap" :style="{ height: `${chartHeight}px` }">
        <Bar :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js';

ChartJS.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip);

const METRIC_LABELS = { quantity: 'Quantity', total_cny: 'Total, CNY', total_local: 'Total, local' };

const DEFAULT_BAR_COLOR = '#2e465d';
const DEFAULT_HOVER_COLOR = '#49677f';

export default {
  name: 'WarehouseAnalyticsChart',
  components: { Bar },
  emits: ['select-unit'],
  props: {
    summary: {
      type: Object,
      default: () => ({ items: [], totals: {} }),
    },
    metric: {
      type: String,
      default: 'quantity',
    },
    selectedUnit: {
      type: String,
      default: '',
    },
    selectedCount: {
      type: Number,
      default: 0,
    },
    limit: {
      type: Number,
      default: 20,
    },
    isLoading: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    items() {
      return this.summary?.items || [];
    },
    totals() {
      return this.summary?.totals || {};
    },
    availableUnits() {
      return this.summary?.available_units || [];
    },
    quantityTotals() {
      const totals = this.totals.quantity_totals || [];
      if (totals.length) return totals;
      return [{ unit: this.items[0]?.unit || '', quantity: this.totals.quantity || 0 }];
    },
    chartHeight() {
      return Math.max(180, this.items.length * 44 + 60);
    },
    localCurrencyLabel() {
      return this.totals.currency_code || this.items[0]?.currency_code || 'Local';
    },
    subtitle() {
      if (this.selectedCount) {
        return `${this.$t('Selected products')}: ${this.selectedCount}`;
      }
      const count = this.totals.products_count || this.items.length;
      return count > this.limit
        ? `${this.$t('Top')} ${this.limit} ${this.$t('of')} ${count}`
        : `${this.$t('Products')}: ${count}`;
    },
    chartData() {
      return {
        labels: this.items.map(item => this.itemLabel(item)),
        datasets: [
          {
            label: this.metricLabel(this.metric),
            data: this.items.map(item => Number(item[this.metric] || 0)),
            backgroundColor: DEFAULT_BAR_COLOR,
            hoverBackgroundColor: DEFAULT_HOVER_COLOR,
            borderColor: DEFAULT_BAR_COLOR,
            hoverBorderColor: DEFAULT_HOVER_COLOR,
            borderWidth: 1,
            borderRadius: 4,
            maxBarThickness: 26,
          },
        ],
      };
    },
    chartOptions() {
      return {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              title: contexts => {
                const item = this.items[contexts[0]?.dataIndex] || {};
                const title = [item.sku, item.product_name].filter(Boolean).join(' — ');
                return title.match(/.{1,28}(?:\s|$)|.{1,28}/g) || [];
              },
              label: context => {
                const item = this.items[context.dataIndex] || {};
                const lines = [`${this.metricLabel(this.metric)}: ${this.formatTooltip(context.raw, item)}`];
                if (item.breakdown) {
                  lines.push(`${this.$t('Received')}: ${this.formatTooltip(item.breakdown.received?.[this.metric], item)}`);
                  lines.push(`${this.$t('Expected')}: ${this.formatTooltip(item.breakdown.expected?.[this.metric], item)}`);
                }
                return lines;
              },
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: '#edf2f7',
            },
            ticks: {
              maxTicksLimit: 4,
              maxRotation: 0,
              callback: value => this.formatAxisTick(value),
            },
          },
          y: {
            grid: {
              display: false,
            },
            ticks: {
              autoSkip: false,
              callback: function (value) {
                const label = this.getLabelForValue(value);
                const limit = this.chart.width < 480 ? 16 : 38;
                return label.length > limit ? `${label.slice(0, limit - 1)}…` : label;
              },
            },
          },
        },
      };
    },
  },
  methods: {
    metricLabel(metric) {
      return this.$t(METRIC_LABELS[metric] || 'Value');
    },
    itemLabel(item) {
      const name = item.product_name || '';
      const sku = item.sku || '';
      const shortName = name.length > 34 ? `${name.slice(0, 34)}...` : name;
      return sku ? `${sku} - ${shortName}` : shortName;
    },
    formatNumber(value) {
      const numberValue = Number(value || 0);
      return Number.isFinite(numberValue)
        ? numberValue.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
        : '0';
    },
    formatMoney(value) {
      const numberValue = Number(value || 0);
      return Number.isFinite(numberValue)
        ? numberValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : '0,00';
    },
    formatTooltip(value, item) {
      if (this.metric === 'quantity') {
        const unit = item.unit ? ` ${item.unit}` : '';
        return `${this.formatNumber(value)}${unit}`;
      }
      if (this.metric === 'total_cny') {
        return `¥ ${this.formatMoney(value)}`;
      }
      return `${this.formatMoney(value)} ${item.currency_code || this.localCurrencyLabel}`;
    },
    formatAxisTick(value) {
      if (this.metric === 'quantity') {
        const unit = this.items[0]?.unit ? ` ${this.items[0].unit}` : '';
        return `${this.formatNumber(value)}${unit}`;
      }
      if (this.metric === 'total_cny') {
        return `¥ ${this.formatNumber(value)}`;
      }
      return `${this.formatNumber(value)} ${this.localCurrencyLabel}`;
    },
  },
};
</script>

<style scoped>
.warehouse-analytics {
  margin-bottom: 1rem;
  padding: 1rem;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  background: #fff;
}

.analytics-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
}

.analytics-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}

.analytics-subtitle {
  color: #6c757d;
  font-size: 0.875rem;
}

.analytics-totals {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}

.analytics-totals div {
  min-width: 84px;
  padding: 0.4rem 0.55rem;
  border: 1px solid #e9ecef;
  border-radius: 0.375rem;
  background: #f8f9fa;
  text-align: right;
}

.analytics-totals span {
  display: block;
  color: #6c757d;
  font-size: 0.74rem;
}

.analytics-totals strong {
  display: block;
  color: #212529;
  font-size: 0.9rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.analytics-chart-scroll {
  max-height: 560px;
  max-height: min(560px, 65vh);
  overflow-y: auto;
  min-width: 0;
}

.analytics-unit-selector {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
  color: #6c757d;
  font-size: 0.8rem;
}

.analytics-chart-wrap {
  position: relative;
  width: 100%;
  min-width: 0;
}

.analytics-single-product {
  overflow-wrap: anywhere;
  font-size: 0.875rem;
}

.analytics-empty {
  padding: 2rem 1rem;
  color: #6c757d;
  text-align: center;
}

@media (max-width: 768px) {
  .analytics-header {
    display: block;
  }

  .analytics-totals {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    margin-top: 0.75rem;
  }

  .analytics-totals div {
    min-width: 0;
  }

  .warehouse-analytics {
    padding: 0.75rem;
  }
}
</style>
