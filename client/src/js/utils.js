export function baseURL() {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
}

export function makeURL(path) {
  return `${baseURL()}${path}`;
}
