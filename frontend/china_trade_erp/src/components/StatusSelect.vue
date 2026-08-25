<template>
  <div ref="root" class="status-select" :class="{ 'status-select-sm': size === 'sm' }">
    <button
      type="button"
      class="status-select-toggle"
      :class="{ 'is-placeholder': !selectedStatus }"
      :style="selectedButtonStyle"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="status-select-label">
        <span
          v-if="selectedStatus"
          class="status-select-dot selected-dot"
          :style="{ backgroundColor: selectedStatus.color || fallbackColor }"
        ></span>
        <span>{{ selectedStatus ? selectedStatus.name : placeholder }}</span>
      </span>
      <span class="status-select-caret"></span>
    </button>

    <div v-if="isOpen" class="status-select-menu">
      <button
        v-if="clearable"
        type="button"
        class="status-select-item text-muted"
        @click="selectStatus('')"
      >
        {{ placeholder }}
      </button>
      <button
        v-for="status in statuses"
        :key="status.id"
        type="button"
        class="status-select-item"
        :class="{ active: String(status.id) === String(modelValue) }"
        @click="selectStatus(status.id)"
      >
        <span
          class="status-select-dot"
          :style="{ backgroundColor: status.color || fallbackColor }"
        ></span>
        <span class="status-select-item-name">{{ status.name }}</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatusSelect',
  props: {
    modelValue: {
      type: [String, Number],
      default: '',
    },
    statuses: {
      type: Array,
      default: () => [],
    },
    placeholder: {
      type: String,
      default: 'Select status...',
    },
    size: {
      type: String,
      default: '',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    clearable: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue', 'change'],
  data() {
    return {
      isOpen: false,
      fallbackColor: '#6c757d',
    };
  },
  computed: {
    selectedStatus() {
      return this.statuses.find(status => String(status.id) === String(this.modelValue)) || null;
    },
    selectedButtonStyle() {
      if (!this.selectedStatus) return {};
      const color = this.selectedStatus.color || this.fallbackColor;
      return {
        backgroundColor: color,
        borderColor: color,
        color: this.textColor(color),
      };
    },
  },
  mounted() {
    document.addEventListener('click', this.onDocumentClick);
    document.addEventListener('keydown', this.onKeydown);
  },
  beforeUnmount() {
    document.removeEventListener('click', this.onDocumentClick);
    document.removeEventListener('keydown', this.onKeydown);
  },
  methods: {
    toggle() {
      if (this.disabled) return;
      this.isOpen = !this.isOpen;
    },
    selectStatus(value) {
      this.$emit('update:modelValue', value);
      this.$emit('change', value);
      this.isOpen = false;
    },
    onDocumentClick(event) {
      if (!this.$refs.root?.contains(event.target)) {
        this.isOpen = false;
      }
    },
    onKeydown(event) {
      if (event.key === 'Escape') {
        this.isOpen = false;
      }
    },
    textColor(color) {
      const hex = String(color).replace('#', '');
      if (!/^[0-9a-fA-F]{6}$/.test(hex)) return '#fff';
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness > 165 ? '#1f2933' : '#fff';
    },
  },
};
</script>

<style scoped>
.status-select {
  position: relative;
  width: 100%;
}
.status-select-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 38px;
  padding: 0.375rem 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 0.375rem;
  background: #fff;
  color: #212529;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.status-select-toggle:hover,
.status-select-toggle:focus {
  border-color: #86b7fe;
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.12);
}
.status-select-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.status-select-toggle.is-placeholder {
  color: #6c757d;
}
.status-select-sm .status-select-toggle {
  min-height: 31px;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}
.status-select-label {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 0.45rem;
}
.status-select-label span:last-child,
.status-select-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-select-caret {
  width: 0;
  height: 0;
  margin-left: 0.5rem;
  border-top: 0.35em solid currentColor;
  border-right: 0.35em solid transparent;
  border-left: 0.35em solid transparent;
}
.status-select-menu {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  z-index: 1060;
  width: 100%;
  max-height: 260px;
  padding: 0.25rem 0;
  overflow-y: auto;
  border: 1px solid #ced4da;
  border-radius: 0.375rem;
  background: #fff;
  box-shadow: 0 0.75rem 1.5rem rgba(15, 23, 42, 0.16);
}
.status-select-item {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 0.55rem;
  padding: 0.45rem 0.65rem;
  border: 0;
  background: transparent;
  color: #212529;
  text-align: left;
}
.status-select-item:hover,
.status-select-item.active {
  background: #f1f5f9;
}
.status-select-dot {
  flex: 0 0 auto;
  width: 0.72rem;
  height: 0.72rem;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 999px;
}
.selected-dot {
  border-color: rgba(255, 255, 255, 0.55);
}
</style>
