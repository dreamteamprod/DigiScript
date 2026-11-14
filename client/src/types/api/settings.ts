export interface SystemSetting {
  key: string;
  value: string;
}

export interface SystemSettings {
  current_show: number | null;
  client_log_enabled: boolean | null;
  client_log_level: string | null;
  /** Server-wide switch to the collaborative script editor (admin setting, default off). */
  collaborative_script_editing?: boolean;
  [key: string]: unknown;
}
