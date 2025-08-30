/**
 * Utility functions for the Vue 3 DigiScript application
 * These functions replicate the functionality from client/src/js/utils.js
 */

export function baseURL(): string {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
}

export function makeURL(path: string): string {
  return `${baseURL()}${path}`;
}

export function titleCase(str: string, sep: string = ' '): string {
  const splitStr = str.toLowerCase().split(sep);
  for (let i = 0; i < splitStr.length; i += 1) {
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
  seconds: number,
): [string, string, string] {
  const h = hours > 9 ? hours.toString() : `0${hours}`;
  const m = minutes > 9 ? minutes.toString() : `0${minutes}`;
  const s = seconds > 9 ? seconds.toString() : `0${seconds}`;
  return [h, m, s];
}
