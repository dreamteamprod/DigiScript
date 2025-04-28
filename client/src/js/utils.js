export function baseURL() {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
}

export function makeURL(path) {
  return `${baseURL()}${path}`;
}

export function titleCase(str, sep = ' ') {
  const splitStr = str.toLowerCase().split(sep);
  for (let i = 0; i < splitStr.length; i++) {
    splitStr[i] = splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
  }
  return splitStr.join(' ');
}

export function randInt(min, max) {
  const minCeil = Math.ceil(min);
  const maxFloor = Math.floor(max);
  return Math.floor(Math.random() * (maxFloor - minCeil) + minCeil);
}

export function msToTimerString(milliseconds) {
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

export function msToTimerParts(milliseconds) {
  // Adapted from https://stackoverflow.com/a/33909506
  const hours = milliseconds / (1000 * 60 * 60);
  const absoluteHours = Math.floor(hours);
  const minutes = (hours - absoluteHours) * 60;
  const absoluteMinutes = Math.floor(minutes);
  const seconds = (minutes - absoluteMinutes) * 60;
  const absoluteSeconds = Math.floor(seconds);
  return [absoluteHours, absoluteMinutes, absoluteSeconds];
}

export function formatTimerParts(hours, minutes, seconds) {
  const h = hours > 9 ? hours : `0${hours}`;
  const m = minutes > 9 ? minutes : `0${minutes}`;
  const s = seconds > 9 ? seconds : `0${seconds}`;
  return [h, m, s];
}
