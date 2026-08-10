import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

export interface HealthResponse { status: string; service: string; }

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  // Relative URLs work through Nginx and Angular's development proxy.
  health() { return this.http.get<HealthResponse>('/api/health/'); }
}
