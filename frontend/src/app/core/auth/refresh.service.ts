import { inject, Injectable } from '@angular/core';
import { finalize, Observable, shareReplay, tap, throwError } from 'rxjs';
import { RefreshResponse } from '../models/application.models';
import { LoginService } from './login.service';
import { TokenService } from './token.service';

@Injectable({ providedIn: 'root' })
export class RefreshService {
  private readonly api = inject(LoginService);
  private readonly tokens = inject(TokenService);
  private inFlight?: Observable<RefreshResponse>;

  refresh() {
    if (this.inFlight) return this.inFlight;
    const refresh = this.tokens.refreshToken;
    if (!refresh) return throwError(() => new Error('Refresh token unavailable'));
    this.inFlight = this.api.refresh(refresh).pipe(
      tap(response => this.tokens.store({ access: response.access, refresh: response.refresh ?? refresh })),
      finalize(() => this.inFlight = undefined),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.inFlight;
  }
}
