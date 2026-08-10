import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { RefreshService } from '../auth/refresh.service';
import { TokenService } from '../auth/token.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const tokens = inject(TokenService); const refresh = inject(RefreshService);
  const auth = inject(AuthService); const router = inject(Router);
  const isAuthEndpoint = ['/api/auth/login/', '/api/auth/refresh/', '/api/auth/logout/']
    .some(endpoint => request.url.includes(endpoint));
  const authenticatedRequest = !isAuthEndpoint && tokens.accessToken
    ? request.clone({ setHeaders: { Authorization: `Bearer ${tokens.accessToken}` } }) : request;

  return next(authenticatedRequest).pipe(catchError((error: HttpErrorResponse) => {
    if (error.status === 503 && error.error?.code === 'maintenance_mode') {
      router.navigateByUrl('/manutencao');
      return throwError(() => error);
    }
    if (error.status !== 401 || isAuthEndpoint || !tokens.refreshToken) return throwError(() => error);
    return refresh.refresh().pipe(
      switchMap(() => next(request.clone({ setHeaders: { Authorization: `Bearer ${tokens.accessToken}` } }))),
      catchError(refreshError => { auth.clearSession(); router.navigate(['/login'], { queryParams: { expired: true } }); return throwError(() => refreshError); })
    );
  }));
};
