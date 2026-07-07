<template>
  <div ref="root" class="autocomplete-input">
    <input
        :value="modelValue"
        type="text"
        class="form-control"
        :placeholder="placeholder"
        autocomplete="off"
        @focus="openDropdown"
        @input="handleInput"
        @keydown.down.prevent="moveHighlight(1)"
        @keydown.up.prevent="moveHighlight(-1)"
        @keydown.enter.prevent="selectHighlighted"
        @keydown.esc="closeDropdown"
    />

    <div v-if="isOpen" class="autocomplete-menu shadow-sm">
      <button
          v-for="(option, index) in visibleOptions"
          :key="option.id || option.name"
          type="button"
          class="autocomplete-option"
          :class="{ active: index === highlightedIndex }"
          @mousedown.prevent="selectOption(option)"
      >
        <span class="autocomplete-name">{{ option.name }}</span>
        <span v-if="optionMeta(option)" class="autocomplete-meta">
          {{ optionMeta(option) }}
        </span>
      </button>

      <div v-if="!visibleOptions.length" class="autocomplete-empty">
        No matches
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AutocompleteInput',
  props: {
    modelValue: {
      type: String,
      default: '',
    },
    options: {
      type: Array,
      default: () => [],
    },
    placeholder: {
      type: String,
      default: '',
    },
    limit: {
      type: Number,
      default: 20,
    },
    modelModifiers: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['update:modelValue', 'input'],
  data() {
    return {
      isOpen: false,
      highlightedIndex: 0,
    };
  },
  computed: {
    visibleOptions() {
      const query = this.modelValue.trim().toLowerCase();
      const filtered = query
          ? this.options.filter(option => (option.name || '').toLowerCase().includes(query))
          : this.options;

      return filtered.slice(0, this.limit);
    },
  },
  mounted() {
    document.addEventListener('mousedown', this.handleOutsideClick);
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.handleOutsideClick);
  },
  methods: {
    openDropdown() {
      this.isOpen = true;
      this.highlightedIndex = 0;
    },
    closeDropdown() {
      this.isOpen = false;
    },
    handleInput(event) {
      const value = this.modelModifiers.trim ? event.target.value.trim() : event.target.value;
      this.$emit('update:modelValue', value);
      this.$emit('input');
      this.openDropdown();
    },
    selectOption(option) {
      this.$emit('update:modelValue', option.name || '');
      this.$emit('input');
      this.closeDropdown();
    },
    moveHighlight(direction) {
      if (!this.isOpen) {
        this.openDropdown();
        return;
      }
      if (!this.visibleOptions.length) return;

      const nextIndex = this.highlightedIndex + direction;
      if (nextIndex < 0) {
        this.highlightedIndex = this.visibleOptions.length - 1;
      } else if (nextIndex >= this.visibleOptions.length) {
        this.highlightedIndex = 0;
      } else {
        this.highlightedIndex = nextIndex;
      }
    },
    selectHighlighted() {
      const option = this.visibleOptions[this.highlightedIndex];
      if (option) this.selectOption(option);
    },
    handleOutsideClick(event) {
      if (!this.$refs.root?.contains(event.target)) {
        this.closeDropdown();
      }
    },
    optionMeta(option) {
      const roles = [];
      if (option.is_supplier) roles.push('Supplier');
      if (option.is_customer) roles.push('Customer');

      const region = option.type === 'china' ? 'Chinese' : option.type === 'local' ? 'Local' : option.type;
      return [...roles, region].filter(Boolean).join(' / ');
    },
  },
};
</script>

<style scoped>
.autocomplete-input {
  position: relative;
}

.autocomplete-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  left: 0;
  z-index: 1055;
  max-height: 260px;
  overflow-y: auto;
  padding: 0.35rem;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
}

.autocomplete-option {
  display: flex;
  width: 100%;
  min-height: 38px;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  color: #212529;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 0.25rem;
}

.autocomplete-option:hover,
.autocomplete-option.active {
  background: #f1f5f9;
}

.autocomplete-name {
  overflow: hidden;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.autocomplete-meta {
  flex: 0 0 auto;
  max-width: 45%;
  overflow: hidden;
  color: #6c757d;
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.autocomplete-empty {
  padding: 0.7rem 0.6rem;
  color: #6c757d;
  font-size: 0.9rem;
}
</style>
