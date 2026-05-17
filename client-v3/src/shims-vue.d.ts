declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent;
  export default component;
}

declare module 'contrast-color' {
  interface ContrastColorOptions {
    bgColor: string;
    fgDarkColor?: string;
    fgLightColor?: string;
    threshold?: number;
  }
  export function contrastColor(options: ContrastColorOptions): string;
  const ContrastColor: {
    new (options?: Partial<ContrastColorOptions>): {
      contrastColor(options: ContrastColorOptions): string;
    };
  };
  export default ContrastColor;
}
