# Vue 3 Migration: BootstrapVue to PrimeVue Component Mapping

This document provides comprehensive mapping from BootstrapVue components to PrimeVue equivalents for the DigiScript Vue 3 migration.

## Table of Contents
- [Layout & Navigation](#layout--navigation)
- [Form Controls](#form-controls)
- [Data Display](#data-display)
- [Feedback](#feedback)
- [Typography & Content](#typography--content)
- [Utilities](#utilities)
- [Migration Patterns](#migration-patterns)

## Layout & Navigation

### Navigation Components
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-navbar>` | `<Menubar>` | Use template slots `#start` and `#end` |
| `<b-nav>` | `<TabMenu>` or `<Menu>` | Context-dependent |
| `<b-nav-item>` | Menu model objects | Define in component data |
| `<b-breadcrumb>` | `<Breadcrumb>` | Similar API |
| `<b-sidebar>` | `<Sidebar>` | Similar functionality |

### Layout Components  
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-container>` | Native CSS or `<div>` | Use CSS classes |
| `<b-row>` | Native CSS Grid/Flexbox | Use CSS classes |
| `<b-col>` | Native CSS Grid/Flexbox | Use CSS classes |
| `<b-card>` | `<Card>` | Similar structure |
| `<b-card-header>` | `<template #header>` | Use slot |
| `<b-card-body>` | `<template #content>` | Use slot |

## Form Controls

### Input Components
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-form-input>` | `<InputText>` | Basic text input |
| `<b-form-textarea>` | `<Textarea>` | Multiline text |
| `<b-form-select>` | `<Dropdown>` | Options via `options` prop |
| `<b-form-checkbox>` | `<Checkbox>` | Binary true/false |
| `<b-form-radio>` | `<RadioButton>` | Single selection |
| `<b-form-datepicker>` | `<Calendar>` | Date selection |
| `<b-form-timepicker>` | `<Calendar>` | Use `timeOnly` mode |

### Form Layout
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-form>` | `<form>` | Native HTML |
| `<b-form-group>` | `<div>` + CSS | Custom layout |
| `<b-form-row>` | CSS Grid/Flexbox | Use CSS classes |
| `<b-input-group>` | `<InputGroup>` | Input with addons |

### Validation
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `state` prop | `invalid` prop | Boolean validation state |
| `<b-form-invalid-feedback>` | `<small>` with error styling | Manual implementation |
| `<b-form-valid-feedback>` | `<small>` with success styling | Manual implementation |

## Data Display

### Tables
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-table>` | `<DataTable>` | Feature-rich table |
| `items` prop | `value` prop | Data source |
| `fields` prop | `<Column>` components | Column definition |
| `<b-table-simple>` | Native HTML table | For simple tables |

### Lists
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-list-group>` | `<Listbox>` | Interactive lists |
| `<b-list-group-item>` | List options | Via data model |

## Feedback

### Alerts & Messages
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-alert>` | `<InlineMessage>` | Static messages |
| `$bvToast.toast()` | `$toast.add()` | Programmatic toasts |
| `<b-modal>` | `<Dialog>` | Modal dialogs |
| `<b-progress>` | `<ProgressBar>` | Progress indication |
| `<b-spinner>` | `<ProgressSpinner>` | Loading indication |

### Overlays
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-tooltip>` | `<Tooltip>` | Hover information |
| `<b-popover>` | `<OverlayPanel>` | Click-triggered overlay |

## Typography & Content

### Text Components
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| `<b-badge>` | `<Badge>` | Status indicators |
| Bootstrap typography classes | CSS custom styles | Use CSS variables |

## Utilities

### Layout Utilities
| BootstrapVue | PrimeVue | Notes |
|--------------|----------|-------|
| Bootstrap flex classes | PrimeVue flex classes | `.flex`, `.align-items-center` |
| Bootstrap spacing | CSS custom properties | Use CSS variables |
| Bootstrap colors | PrimeVue color variables | `var(--p-primary-color)` |

## Migration Patterns

### 1. Component Import Pattern

**BootstrapVue (Vue 2):**
```javascript
import { BTable, BButton } from 'bootstrap-vue'
export default {
  components: { BTable, BButton }
}
```

**PrimeVue (Vue 3):**
```typescript
import DataTable from 'primevue/datatable'
import Button from 'primevue/button'
```

### 2. Template Structure Migration

**BootstrapVue Navigation:**
```vue
<b-navbar toggleable="lg" type="dark" variant="dark">
  <b-navbar-brand to="/">DigiScript</b-navbar-brand>
  <b-navbar-nav>
    <b-nav-item to="/shows">Shows</b-nav-item>
    <b-nav-item to="/config">Config</b-nav-item>
  </b-navbar-nav>
</b-navbar>
```

**PrimeVue Navigation:**
```vue
<Menubar :model="menuItems">
  <template #start>
    <div class="navbar-brand">DigiScript</div>
  </template>
</Menubar>

<script setup lang="ts">
const menuItems = ref([
  { label: 'Shows', icon: 'pi pi-list', to: '/shows' },
  { label: 'Config', icon: 'pi pi-cog', to: '/config' }
])
</script>
```

### 3. Form Migration Pattern

**BootstrapVue Forms:**
```vue
<b-form @submit="onSubmit">
  <b-form-group label="Name" label-for="name-input">
    <b-form-input 
      id="name-input" 
      v-model="form.name" 
      :state="validation.name"
      required 
    />
    <b-form-invalid-feedback>Name is required</b-form-invalid-feedback>
  </b-form-group>
  
  <b-button type="submit" variant="primary">Submit</b-button>
</b-form>
```

**PrimeVue Forms:**
```vue
<form @submit.prevent="onSubmit">
  <div class="field">
    <label for="name-input">Name</label>
    <InputText 
      id="name-input" 
      v-model="form.name" 
      :invalid="!validation.name"
      required 
    />
    <small v-if="!validation.name" class="p-error">Name is required</small>
  </div>
  
  <Button type="submit" label="Submit" />
</form>
```

### 4. Table Migration Pattern

**BootstrapVue Tables:**
```vue
<b-table 
  :items="items" 
  :fields="fields" 
  striped 
  hover 
  small
>
  <template #cell(actions)="row">
    <b-button size="sm" @click="edit(row.item)">Edit</b-button>
  </template>
</b-table>
```

**PrimeVue Tables:**
```vue
<DataTable 
  :value="items" 
  stripedRows 
  :paginator="true" 
  :rows="10"
>
  <Column field="name" header="Name" />
  <Column field="email" header="Email" />
  <Column header="Actions">
    <template #body="slotProps">
      <Button 
        size="small" 
        @click="edit(slotProps.data)"
        label="Edit" 
      />
    </template>
  </Column>
</DataTable>
```

## TypeScript Integration

### Type Definitions
```typescript
// PrimeVue menu item type
interface MenuItem {
  label?: string;
  icon?: string;
  to?: string;
  command?: () => void;
  items?: MenuItem[];
}

// Form validation type
interface FormValidation {
  [key: string]: boolean;
}
```

### Component Props with TypeScript
```typescript
<script setup lang="ts">
interface Props {
  items: any[];
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});
</script>
```

## CSS Variable Migration

### BootstrapVue to PrimeVue Variables
| Bootstrap Variable | PrimeVue Variable | Usage |
|--------------------|-------------------|-------|
| `$primary` | `var(--p-primary-color)` | Primary brand color |
| `$secondary` | `var(--p-primary-200)` | Secondary colors |
| `$success` | `var(--p-green-500)` | Success state |
| `$danger` | `var(--p-red-500)` | Error state |
| `$warning` | `var(--p-orange-500)` | Warning state |
| `$info` | `var(--p-blue-500)` | Info state |

## Best Practices

### 1. Component Organization
- Import PrimeVue components individually for tree-shaking
- Use TypeScript interfaces for props and emits
- Utilize Composition API with `<script setup>` syntax

### 2. Styling Strategy
- Use PrimeVue CSS variables for theming
- Combine with custom CSS for specific DigiScript branding
- Maintain responsive design principles

### 3. Migration Approach
- Migrate one component type at a time (navigation → forms → tables)
- Test thoroughly at each step
- Preserve existing functionality during migration

### 4. Performance Considerations
- PrimeVue components are generally larger than BootstrapVue
- Use dynamic imports for large components
- Consider code splitting for optimal bundle size

---

*This mapping guide will be updated as migration progresses through Phase 3 of the Vue 3 implementation.*