import { inject } from '@angular/core';
import { ResolveFn } from '@angular/router';
import { AuthUser } from '../models/application.models';
import { AuthService } from '../auth/auth.service';

export const authResolver: ResolveFn<AuthUser | null> = () => inject(AuthService).restore();
