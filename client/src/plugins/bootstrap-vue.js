import Vue from 'vue';

// Import only the Bootstrap-Vue components, icons, and plugins used in the application
import {
  // Layout & Grid
  BContainer,
  BRow,
  BCol,

  // Forms
  BForm,
  BFormGroup,
  BFormInput,
  BFormSelect,
  BFormSelectOption,
  BFormCheckbox,
  BFormInvalidFeedback,
  BFormText,
  BFormRow,
  BInputGroup,
  BInputGroupAppend,

  // Buttons
  BButton,
  BButtonGroup,

  // Table
  BTable,
  BTableSimple,
  BTbody,
  BTr,
  BTh,
  BTd,

  // Tabs
  BTabs,
  BTab,

  // Card
  BCard,
  BCardText,

  // Modal
  BModal,

  // Navigation
  BNavbar,
  BNavbarBrand,
  BNavbarNav,
  BNavbarToggle,
  BNavItem,
  BNavItemDropdown,
  BNavText,

  // Dropdown
  BDropdownItem,
  BDropdownItemButton,

  // Alert
  BAlert,

  // Pagination
  BPagination,

  // Progress
  BProgress,

  // Spinner
  BSpinner,

  // Overlay
  BOverlay,

  // Collapse
  BCollapse,

  // Link
  BLink,

  // Tooltip
  BTooltip,

  // Time
  BTime,

  // Icons
  BIcon,
  BIconPlusSquareFill,
  BIconCheckSquareFill,
  BIconXSquareFill,
  BIconXCircle,
  BIconSquareFill,
  BIconQuestionCircleFill,
  BIconClipboard,
  BIconCheckCircle,

  // Plugins
  BVModalPlugin,
} from 'bootstrap-vue';

// Register components globally
Vue.component('BContainer', BContainer);
Vue.component('BRow', BRow);
Vue.component('BCol', BCol);
Vue.component('BForm', BForm);
Vue.component('BFormGroup', BFormGroup);
Vue.component('BFormInput', BFormInput);
Vue.component('BFormSelect', BFormSelect);
Vue.component('BFormSelectOption', BFormSelectOption);
Vue.component('BFormCheckbox', BFormCheckbox);
Vue.component('BFormInvalidFeedback', BFormInvalidFeedback);
Vue.component('BFormText', BFormText);
Vue.component('BFormRow', BFormRow);
Vue.component('BInputGroup', BInputGroup);
Vue.component('BInputGroupAppend', BInputGroupAppend);
Vue.component('BButton', BButton);
Vue.component('BButtonGroup', BButtonGroup);
Vue.component('BTable', BTable);
Vue.component('BTableSimple', BTableSimple);
Vue.component('BTbody', BTbody);
Vue.component('BTr', BTr);
Vue.component('BTh', BTh);
Vue.component('BTd', BTd);
Vue.component('BTabs', BTabs);
Vue.component('BTab', BTab);
Vue.component('BCard', BCard);
Vue.component('BCardText', BCardText);
Vue.component('BModal', BModal);
Vue.component('BNavbar', BNavbar);
Vue.component('BNavbarBrand', BNavbarBrand);
Vue.component('BNavbarNav', BNavbarNav);
Vue.component('BNavbarToggle', BNavbarToggle);
Vue.component('BNavItem', BNavItem);
Vue.component('BNavItemDropdown', BNavItemDropdown);
Vue.component('BNavText', BNavText);
Vue.component('BDropdownItem', BDropdownItem);
Vue.component('BDropdownItemButton', BDropdownItemButton);
Vue.component('BAlert', BAlert);
Vue.component('BPagination', BPagination);
Vue.component('BProgress', BProgress);
Vue.component('BSpinner', BSpinner);
Vue.component('BOverlay', BOverlay);
Vue.component('BCollapse', BCollapse);
Vue.component('BLink', BLink);
Vue.component('BTooltip', BTooltip);
Vue.component('BTime', BTime);

// Register icons
Vue.component('BIcon', BIcon);
Vue.component('BIconPlusSquareFill', BIconPlusSquareFill);
Vue.component('BIconCheckSquareFill', BIconCheckSquareFill);
Vue.component('BIconXSquareFill', BIconXSquareFill);
Vue.component('BIconXCircle', BIconXCircle);
Vue.component('BIconSquareFill', BIconSquareFill);
Vue.component('BIconQuestionCircleFill', BIconQuestionCircleFill);
Vue.component('BIconClipboard', BIconClipboard);
Vue.component('BIconCheckCircle', BIconCheckCircle);

// Register plugins (for $bvModal, etc.)
Vue.use(BVModalPlugin);
