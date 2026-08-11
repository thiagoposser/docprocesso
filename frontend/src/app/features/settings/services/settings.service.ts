import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { map, tap } from 'rxjs';
import { AdminSettings, PublicSettings } from '../models/settings.models';

const DEFAULT_SETTINGS: PublicSettings = {
  system_name: 'DocProcesso', system_short_name: 'DP', logo_url: null,
  primary_color: '#4a4ab8', language_code: 'pt-br', timezone: 'America/Sao_Paulo', version: '0.1.0'
};

@Injectable({ providedIn: 'root' })
export class SettingsService {
  private readonly http = inject(HttpClient);
  readonly publicSettings = signal<PublicSettings>(DEFAULT_SETTINGS);
  readonly name = computed(() => this.publicSettings().system_name);
  readonly shortName = computed(() => this.publicSettings().system_short_name);
  readonly logoUrl = computed(() => this.publicSettings().logo_url);

  loadPublic() { return this.http.get<PublicSettings>('/api/settings/public/').pipe(tap(settings => this.apply(this.withProjectIdentity(settings)))); }
  getAdmin() { return this.http.get<AdminSettings>('/api/settings/').pipe(map(settings => this.withProjectIdentity(settings))); }
  update(payload: FormData) { return this.http.patch<AdminSettings>('/api/settings/', payload).pipe(tap(settings => this.apply(settings))); }

  private apply(settings: PublicSettings) {
    this.publicSettings.set(settings);
    document.title = settings.system_name;
    document.documentElement.lang = settings.language_code;
    document.documentElement.style.setProperty('--color-primary', settings.primary_color);
    document.documentElement.style.setProperty('--color-primary-hover', `color-mix(in srgb, ${settings.primary_color} 88%, black)`);
    document.documentElement.style.setProperty('--bs-primary', settings.primary_color);
  }

  private withProjectIdentity<T extends PublicSettings>(settings: T): T {
    return {
      ...settings,
      system_name: settings.system_name === 'Base Admin' ? 'DocProcesso' : settings.system_name,
      system_short_name: settings.system_short_name === 'BA' ? 'DP' : settings.system_short_name
    };
  }
}
