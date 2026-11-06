<template>
  <div ref="modal" class="modal" tabindex="-1" aria-labelledby="analytics-modal-title">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="download">
        <div class="modal-header">
          <h5 id="analytics-modal-title" class="modal-title">{{ title }}</h5>
          <button type="button" class="btn-close" aria-label="Close" @click="close"></button>
        </div>
        <div class="modal-body">
          <label for="analytics-party" class="form-label">{{ isSupplier ? 'Supplier' : 'Customer' }}</label>
          <select id="analytics-party" v-model="counterparty" class="form-select mb-3">
            <option value="">{{ isSupplier ? 'All suppliers' : 'All customers' }}</option>
            <option v-for="option in options" :key="option.id" :value="option.id">{{ option.name }}</option>
          </select>
          <div v-if="!counterparty" class="mb-3">
            <label for="analytics-ranking-limit" class="form-label">Ranking size</label>
            <select id="analytics-ranking-limit" v-model="rankingLimit" class="form-select">
              <option value="10">Top 10</option>
              <option v-if="!isSupplier" value="20">Top 20</option>
              <option v-if="!isSupplier" value="30">Top 30</option>
              <option value="all">All</option>
            </select>
          </div>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <label for="analytics-from" class="form-label">Order date from</label>
              <input id="analytics-from" v-model="dateFrom" type="date" class="form-control" :max="dateTo || undefined" />
            </div>
            <div class="col-6">
              <label for="analytics-to" class="form-label">To</label>
              <input id="analytics-to" v-model="dateTo" type="date" class="form-control" :min="dateFrom || undefined" />
            </div>
          </div>
          <div class="d-flex flex-wrap gap-2 mb-3">
            <button v-for="period in periods" :key="period.label" type="button" class="btn btn-outline-secondary btn-sm" @click="setPeriod(period)">{{ period.label }}</button>
          </div>
          <p class="small text-muted mb-0">Blank dates mean all time. Cancelled orders are excluded. Search and status filters on the page do not affect this report.</p>
          <div v-if="error" class="alert alert-danger mt-3 mb-0" role="alert">{{ error }}</div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="close">Close</button>
          <button type="submit" class="btn btn-primary" :disabled="loading">{{ loading ? 'Downloading...' : 'Download report' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import Modal from 'bootstrap/js/dist/modal';
import axios from '../axios';

export default {
  name: 'OrderAnalyticsModal',
  props: {
    kind: { type: String, required: true },
    options: { type: Array, default: () => [] },
    initialQuery: { type: String, default: '' },
  },
  emits: ['close'],
  data() {
    return {
      counterparty: '', rankingLimit: '10', dateFrom: '', dateTo: '', loading: false, error: '',
      periods: [{ label: '7 days', days: 7 }, { label: '30 days', days: 30 },
        { label: '6 months', months: 6 }, { label: '1 year', months: 12 }, { label: 'All time' }],
    };
  },
  computed: {
    isSupplier() { return this.kind === 'supplier'; },
    title() { return this.isSupplier ? 'Supplier report' : 'Customer report'; },
  },
  mounted() {
    const matches = this.options.filter(o => o.name.toLowerCase() === this.initialQuery.trim().toLowerCase());
    if (matches.length === 1) this.counterparty = matches[0].id;
    this.$refs.modal.addEventListener('hidden.bs.modal', this.onHidden);
    Modal.getOrCreateInstance(this.$refs.modal).show();
  },
  beforeUnmount() {
    this.$refs.modal.removeEventListener('hidden.bs.modal', this.onHidden);
    const modal = Modal.getInstance(this.$refs.modal);
    modal?.hide();
    modal?.dispose();
  },
  methods: {
    onHidden() { this.$emit('close'); },
    close() { Modal.getInstance(this.$refs.modal)?.hide(); },
    dateValue(date) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    },
    setPeriod(period) {
      if (!period.days && !period.months) { this.dateFrom = ''; this.dateTo = ''; return; }
      const end = new Date();
      const start = new Date(end);
      if (period.days) start.setDate(start.getDate() - period.days + 1);
      else {
        const day = start.getDate();
        start.setDate(1);
        start.setMonth(start.getMonth() - period.months);
        start.setDate(Math.min(day, new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate()));
      }
      this.dateFrom = this.dateValue(start);
      this.dateTo = this.dateValue(end);
    },
    async download() {
      if (this.loading) return;
      this.error = '';
      if (this.dateFrom && this.dateTo && this.dateFrom > this.dateTo) {
        this.error = 'End date must be on or after start date.'; return;
      }
      this.loading = true;
      try {
        const { data } = await axios.get(`/api/${this.kind}-order/analytics/`, {
          params: { date_from: this.dateFrom || undefined, date_to: this.dateTo || undefined,
            counterparty: this.counterparty || undefined,
            ranking_limit: this.counterparty ? undefined : this.rankingLimit }, responseType: 'blob',
        });
        const url = URL.createObjectURL(data);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${this.kind}_analytics.xlsx`;
        document.body.appendChild(link);
        link.click(); link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (error) {
        this.error = 'Unable to download report. Please try again.';
      } finally { this.loading = false; }
    },
  },
};
</script>
