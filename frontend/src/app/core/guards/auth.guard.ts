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

export const sectorGuard: CanActivateFn = () => {
  const auth = inject(AuthService); const router = inject(Router);
  return auth.restore().pipe(map(() => auth.user()?.permissions.includes('sectors.manage_sector') || auth.user()?.is_staff ? true : router.createUrlTree(['/403'])));
};

export const unitGuard = structurePermissionGuard('sectors.manage_organizational_unit');
export const organizationalFunctionGuard = structurePermissionGuard('sectors.manage_organizational_function');

function structurePermissionGuard(permission: string): CanActivateFn {
  return () => {
    const auth = inject(AuthService); const router = inject(Router);
    return auth.restore().pipe(map(() => auth.user()?.is_staff || auth.can(permission) ? true : router.createUrlTree(['/403'])));
  };
}

function permissionGuard(permission: string): CanActivateFn {
  return () => {
    const auth = inject(AuthService); const router = inject(Router);
    return auth.restore().pipe(map(() => auth.can(permission) ? true : router.createUrlTree(['/403'])));
  };
}

export const processViewGuard = permissionGuard('processes.view_administrativeprocess');
export const processAddGuard = permissionGuard('processes.add_administrativeprocess');
export const processChangeGuard = permissionGuard('processes.change_administrativeprocess');
export const workflowGuard = permissionGuard('processes.view_administrativeworkflow');
export const paymentViewGuard: CanActivateFn = () => {
  const auth = inject(AuthService); const router = inject(Router);
  return auth.restore().pipe(map(() => auth.can('payments.view_payment') && auth.can('payments.view_financial_data') && auth.can('processes.view_administrativeprocess') ? true : router.createUrlTree(['/403'])));
};
export const paymentAddGuard = permissionGuard('payments.add_payment');
export const paymentChangeGuard = permissionGuard('payments.change_payment');
export const reportsGuard = permissionGuard('core.generate_reports');
