export interface BackupFile {
  filename: string;
  size_bytes: number;
  created_at: number;
}

export interface BackupsResponse {
  backups: BackupFile[];
  count: number;
  total_size_bytes: number;
}
