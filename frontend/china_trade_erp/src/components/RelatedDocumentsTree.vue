<template>
  <div class="related-docs">
    <div v-if="root" class="related-docs__root">
      <button
          type="button"
          class="doc-card text-start"
          :class="{ 'doc-card--highlight': isHighlighted(root) }"
          @click="openDoc(root)"
      >
        <div class="doc-card__body">
          <div class="fw-semibold">
            <span class="doc-card__check" :style="{ color: statusColor(root) }">✓</span>
            {{ typeLabel(root) }}
          </div>
          <div v-if="root.supplier_name" class="small text-muted">{{ root.supplier_name }}</div>
          <div>№{{ root.order_number }}</div>
          <div class="small text-muted">{{ formatDate(root.created_at) }}</div>
          <div class="fw-semibold">{{ root.total_amount || '0.00' }} rub</div>
        </div>
        <div class="doc-card__status" :style="{ backgroundColor: statusColor(root) }">
          {{ root.status?.name || '-' }}
        </div>
      </button>
    </div>

    <div v-if="root && children.length" class="related-docs__lines" aria-hidden="true"></div>

    <div class="related-docs__children">
      <button
          v-for="child in children"
          :key="`${child.doc_type}-${child.id}`"
          type="button"
          class="doc-card text-start"
          :class="{ 'doc-card--highlight': isHighlighted(child) }"
          @click="openDoc(child)"
      >
        <div class="doc-card__body">
          <div class="fw-semibold">
            <span class="doc-card__check" :style="{ color: statusColor(child) }">✓</span>
            {{ typeLabel(child) }}
          </div>
          <div v-if="child.supplier_name" class="small text-muted">{{ child.supplier_name }}</div>
          <div>№{{ child.order_number }}</div>
          <div class="small text-muted">{{ formatDate(child.created_at) }}</div>
          <div class="fw-semibold">{{ child.total_amount || '0.00' }} rub</div>
        </div>
        <div class="doc-card__status" :style="{ backgroundColor: statusColor(child) }">
          {{ child.status?.name || '-' }}
        </div>
      </button>
      <div v-if="!children.length" class="text-muted py-3">
        {{ emptyText }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RelatedDocumentsTree',
  props: {
    root: {type: Object, default: null},
    children: {type: Array, default: () => []},
    highlightId: {type: Number, default: null},
    emptyText: {type: String, default: 'No related documents yet.'},
  },
  methods: {
    typeLabel(doc) {
      return doc.doc_type === 'customer_order' ? 'Customer order' : 'Supplier order';
    },
    statusColor(doc) {
      return doc.status?.color || '#6c757d';
    },
    formatDate(value) {
      if (!value) return '-';
      const date = new Date(value);
      return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    },
    isHighlighted(doc) {
      return this.highlightId !== null && Number(doc.id) === Number(this.highlightId);
    },
    openDoc(doc) {
      const path = doc.doc_type === 'customer_order'
          ? `/customer-orders/${doc.id}`
          : `/supplier-orders/${doc.id}`;
      this.$router.push(path);
    },
  },
};
</script>

<style scoped>
.related-docs {
  display: flex;
  align-items: center;
  gap: 26px;
  overflow-x: auto;
  padding: 18px 0;
}

.related-docs__root,
.related-docs__children {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 220px;
}

.related-docs__lines {
  position: relative;
  width: 54px;
  align-self: stretch;
  min-height: 120px;
}

.related-docs__lines::before {
  content: "";
  position: absolute;
  left: 26px;
  top: 18px;
  bottom: 18px;
  border-left: 1px solid #adb5bd;
}

.related-docs__lines::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  border-top: 1px solid #adb5bd;
}

.doc-card {
  width: 220px;
  min-height: 112px;
  padding: 0;
  border: 1px solid #adb5bd;
  background: #fff;
  box-shadow: 0 2px 5px rgba(0, 0, 0, .12);
  cursor: pointer;
}

.doc-card--highlight {
  background: #343a40;
  color: #fff;
}

.doc-card--highlight .text-muted {
  color: #ced4da !important;
}

.doc-card__body {
  padding: 10px 12px 8px;
}

.doc-card__check {
  font-weight: 700;
}

.doc-card__status {
  min-height: 22px;
  padding: 2px 8px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}

@media (max-width: 767.98px) {
  .related-docs {
    align-items: flex-start;
    flex-direction: column;
  }

  .related-docs__lines {
    display: none;
  }
}
</style>
