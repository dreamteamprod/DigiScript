import Vue from 'vue';

// Import Bootstrap-Vue component group plugins and icons for tree-shaking
import {
  // Component plugins
  LayoutPlugin,
  FormPlugin,
  FormInputPlugin,
  FormSelectPlugin,
  FormCheckboxPlugin,
  FormGroupPlugin,
  InputGroupPlugin,
  ButtonPlugin,
  TablePlugin,
  TabsPlugin,
  CardPlugin,
  ModalPlugin,
  NavbarPlugin,
  NavPlugin,
  DropdownPlugin,
  AlertPlugin,
  PaginationPlugin,
  ProgressPlugin,
  SpinnerPlugin,
  OverlayPlugin,
  CollapsePlugin,
  LinkPlugin,
  TooltipPlugin,
  FormTimepickerPlugin,

  // Individual icons (no group plugin available)
  BIcon,
  BIconPlusSquareFill,
  BIconCheckSquareFill,
  BIconXSquareFill,
  BIconXCircle,
  BIconSquareFill,
  BIconQuestionCircleFill,
  BIconClipboard,
  BIconCheckCircle,
} from 'bootstrap-vue';

// Register component plugins
Vue.use(LayoutPlugin);
Vue.use(FormPlugin);
Vue.use(FormInputPlugin);
Vue.use(FormSelectPlugin);
Vue.use(FormCheckboxPlugin);
Vue.use(FormGroupPlugin);
Vue.use(InputGroupPlugin);
Vue.use(ButtonPlugin);
Vue.use(TablePlugin);
Vue.use(TabsPlugin);
Vue.use(CardPlugin);
Vue.use(ModalPlugin);
Vue.use(NavbarPlugin);
Vue.use(NavPlugin);
Vue.use(DropdownPlugin);
Vue.use(AlertPlugin);
Vue.use(PaginationPlugin);
Vue.use(ProgressPlugin);
Vue.use(SpinnerPlugin);
Vue.use(OverlayPlugin);
Vue.use(CollapsePlugin);
Vue.use(LinkPlugin);
Vue.use(TooltipPlugin);
Vue.use(FormTimepickerPlugin);

// Register icons individually
Vue.component('BIcon', BIcon);
Vue.component('BIconPlusSquareFill', BIconPlusSquareFill);
Vue.component('BIconCheckSquareFill', BIconCheckSquareFill);
Vue.component('BIconXSquareFill', BIconXSquareFill);
Vue.component('BIconXCircle', BIconXCircle);
Vue.component('BIconSquareFill', BIconSquareFill);
Vue.component('BIconQuestionCircleFill', BIconQuestionCircleFill);
Vue.component('BIconClipboard', BIconClipboard);
Vue.component('BIconCheckCircle', BIconCheckCircle);
