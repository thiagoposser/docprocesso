export interface PublicSettings {
  system_name: string; system_short_name: string; logo_url: string | null; primary_color: string;
  language_code: string; timezone: string; version: string;
}

export interface AdminSettings extends PublicSettings {
  system_description: string; support_email: string; support_url: string;
  maintenance_mode: boolean; created_at: string; updated_at: string;
}
