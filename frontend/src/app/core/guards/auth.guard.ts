import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const authGuard: CanActivateFn = (_, state) => {
  const auth = inject(AuthService); const router = inject(Router);
  return auth.restore().pipe(map(user => user ? true : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } })));
};

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService); const router = inject(Router);
  return auth.restore().pipe(map(() => auth.isAdmin() ? true : router.createUrlTree(['/403'])));
};

export const auditGuard: CanActivateFn = () => {
  const auth = inject(AuthService); const router = inject(Router);
  return auth.restore().pipe(map(() => auth.user()?.permissions.includes('audit.view_auditlog') ? true : router.createUrlTree(['/403'])));
};
