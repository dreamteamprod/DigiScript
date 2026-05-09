export interface SystemSetting {
  key: string;
  value: string;
}

export interface SystemSettings {
  current_show: number | null;
  client_log_enabled: boolean | null;
  client_log_level: string | null;
  [key: string]: unknown;
}
