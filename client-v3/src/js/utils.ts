import { baseURL as platformBaseURL, makeURL as platformMakeURL } from '@/js/platform';

// The contrast-color library uses `this` inside its standalone function, which breaks
// in strict ESM. Inline the standard YIQ formula that the library implements.
export function contrastColor(bgColor: string): string {
  const hex = (bgColor ?? '#ffffff').replace('#', '');
  const r = Number.parseInt(hex.substring(0, 2), 16) || 0;
  const g = Number.parseInt(hex.substring(2, 4), 16) || 0;
  const b = Number.parseInt(hex.substring(4, 6), 16) || 0;
  return (r * 299 + g * 587 + b * 114) / 1000 >= 128 ? '#000000' : '#ffffff';
}

export function baseURL(): string {
  return platformBaseURL();
}

export function makeURL(path: string): string {
  return platformMakeURL(path);
}

export function titleCase(str: string, sep = ' '): string {
  const splitStr = str.toLowerCase().split(sep);
  for (let i = 0; i < splitStr.length; i++) {
    splitStr[i] = splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
  }
  return splitStr.join(' ');
}

export function randInt(min: number, max: number): number {
  const minCeil = Math.ceil(min);
  const maxFloor = Math.floor(max);
  return Math.floor(Math.random() * (maxFloor - minCeil) + minCeil);
}

export function msToTimerString(milliseconds: number): string {
  // Adapted from https://stackoverflow.com/a/33909506
  const hours = milliseconds / (1000 * 60 * 60);
  const absoluteHours = Math.floor(hours);
  const h = absoluteHours > 9 ? absoluteHours : `0${absoluteHours}`;
  const minutes = (hours - absoluteHours) * 60;
  const absoluteMinutes = Math.floor(minutes);
  const m = absoluteMinutes > 9 ? absoluteMinutes : `0${absoluteMinutes}`;
  const seconds = (minutes - absoluteMinutes) * 60;
  const absoluteSeconds = Math.floor(seconds);
  const s = absoluteSeconds > 9 ? absoluteSeconds : `0${absoluteSeconds}`;

  return `${h}:${m}:${s}`;
}

export function msToTimerParts(milliseconds: number): [number, number, number] {
  // Adapted from https://stackoverflow.com/a/33909506
  const hours = milliseconds / (1000 * 60 * 60);
  const absoluteHours = Math.floor(hours);
  const minutes = (hours - absoluteHours) * 60;
  const absoluteMinutes = Math.floor(minutes);
  const seconds = (minutes - absoluteMinutes) * 60;
  const absoluteSeconds = Math.floor(seconds);
  return [absoluteHours, absoluteMinutes, absoluteSeconds];
}

export function formatTimerParts(
  hours: number,
  minutes: number,
  seconds: number
): [string | number, string | number, string | number] {
  const h = hours > 9 ? hours : `0${hours}`;
  const m = minutes > 9 ? minutes : `0${minutes}`;
  const s = seconds > 9 ? seconds : `0${seconds}`;
  return [h, m, s];
}
