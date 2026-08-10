import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, of, switchMap, tap } from 'rxjs';
import { AuthUser } from '../models/application.models';
import { LoginService } from './login.service';
import { TokenService } from './token.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly loginApi = inject(LoginService);
  private readonly tokens = inject(TokenService);
  private readonly router = inject(Router);
  readonly user = signal<AuthUser | null>(null);
  readonly isAuthenticated = computed(() => Boolean(this.user()));
  readonly isAdmin = computed(() => Boolean(this.user()?.is_staff || this.user()?.groups.includes('Administrador')));

  login(username: string, password: string) {
    return this.loginApi.login(username, password).pipe(
      tap(response => this.tokens.store(response)),
      switchMap(() => this.loadCurrentUser())
    );
  }

  loadCurrentUser() {
    return this.loginApi.me().pipe(tap(user => this.user.set(user)));
  }

  restore() {
    if (this.user()) return of(this.user());
    if (!this.tokens.accessToken) return of(null);
    return this.loadCurrentUser().pipe(catchError(() => { this.clearSession(); return of(null); }));
  }

  logout() {
    const refresh = this.tokens.refreshToken;
    const request = refresh ? this.loginApi.logout(refresh) : of(undefined);
    return request.pipe(catchError(() => of(undefined)), finalize(() => { this.clearSession(); this.router.navigateByUrl('/login'); }));
  }

  clearSession() { this.tokens.clear(); this.user.set(null); }
}
