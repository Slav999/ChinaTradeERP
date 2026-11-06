<template>
  <div class="searchable-counterparty-select position-relative">
    <input
      :value="searchText"
      :placeholder="placeholder"
      class="form-control"
      :class="sizeClass"
      autocomplete="off"
      @focus="showDropdown = true"
      @input="onInput"
      @blur="commitText"
      @keydown.down.prevent="moveHighlight(1)"
      @keydown.up.prevent="moveHighlight(-1)"
      @keydown.enter.prevent="selectHighlighted"
      @keydown.esc="closeDropdown"
    />
    <ul
      v-if="showDropdown && filteredOptions.length"
      class="list-group position-absolute w-100 counterparty-suggestions-list"
    >
      <li
        v-for="(option, index) in filteredOptions"
        :key="option.id"
        class="list-group-item list-group-item-action counterparty-suggestion"
        :class="{ active: index === highlightedIndex }"
        @mousedown.prevent="selectOption(option)"
      >
        {{ option.name }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'SearchableCounterpartySelect',
  props: {
    modelValue: { type: [Number, String], default: '' },
    options: { type: Array, default: () => [] },
    placeholder: { type: String, default: 'Select...' },
    size: { type: String, default: 'sm' },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      searchText: '',
      showDropdown: false,
      highlightedIndex: 0,
    };
  },
  computed: {
    sizeClass() {
      return this.size === 'sm' ? 'form-control-sm' : '';
    },
    selectedOption() {
      return this.options.find(option => String(option.id) === String(this.modelValue)) || null;
    },
    filteredOptions() {
      const query = this.searchText.trim().toLowerCase();
      const source = query
        ? this.options.filter(option => (option.name || '').toLowerCase().includes(query))
        : this.options;
      return source.slice(0, 80);
    },
  },
  watch: {
    modelValue: {
      immediate: true,
      handler() {
        this.syncSearchText();
      },
    },
    options() {
      this.syncSearchText();
    },
  },
  methods: {
    syncSearchText() {
      this.searchText = this.selectedOption?.name || '';
    },
    onInput(event) {
      this.searchText = event.target.value;
      this.showDropdown = true;
      this.highlightedIndex = 0;
      if (!this.searchText) {
        this.$emit('update:modelValue', '');
        return;
      }
      const exact = this.findExact(this.searchText);
      if (exact) {
        this.$emit('update:modelValue', exact.id);
      }
    },
    commitText() {
      setTimeout(() => {
        if (!this.searchText) {
          this.$emit('update:modelValue', '');
        } else {
          const exact = this.findExact(this.searchText);
          if (exact) {
            this.$emit('update:modelValue', exact.id);
          } else {
            this.syncSearchText();
          }
        }
        this.closeDropdown();
      }, 120);
    },
    closeDropdown() {
      this.showDropdown = false;
      this.highlightedIndex = 0;
    },
    selectOption(option) {
      this.searchText = option.name || '';
      this.$emit('update:modelValue', option.id);
      this.closeDropdown();
    },
    moveHighlight(direction) {
      this.showDropdown = true;
      if (!this.filteredOptions.length) return;
      const max = this.filteredOptions.length - 1;
      this.highlightedIndex += direction;
      if (this.highlightedIndex < 0) this.highlightedIndex = max;
      if (this.highlightedIndex > max) this.highlightedIndex = 0;
    },
    selectHighlighted() {
      const option = this.filteredOptions[this.highlightedIndex];
      if (option) {
        this.selectOption(option);
      }
    },
    findExact(value) {
      const normalized = value.trim().toLowerCase();
      return this.options.find(option => (option.name || '').trim().toLowerCase() === normalized);
    },
  },
};
</script>

<style scoped>
.searchable-counterparty-select {
  flex: 1 1 auto;
  min-width: 0;
}

.counterparty-suggestions-list {
  top: calc(100% + 2px);
  z-index: 1060;
  max-height: 240px;
  overflow-y: auto;
  overflow-x: hidden;
}

.counterparty-suggestion {
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.35;
  padding: 0.4rem 0.55rem;
}

.counterparty-suggestion:not(.active):hover {
  background-color: #eef5ff;
}
</style>
