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
