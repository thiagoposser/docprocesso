import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { AuthUser, LoginResponse, RefreshResponse } from '../models/application.models';

@Injectable({ providedIn: 'root' })
export class LoginService {
  private readonly http = inject(HttpClient);
  login(username: string, password: string) { return this.http.post<LoginResponse>('/api/auth/login/', { username, password }); }
  refresh(refresh: string) { return this.http.post<RefreshResponse>('/api/auth/refresh/', { refresh }); }
  logout(refresh: string) { return this.http.post<void>('/api/auth/logout/', { refresh }); }
  me() { return this.http.get<AuthUser>('/api/auth/me/'); }
}
