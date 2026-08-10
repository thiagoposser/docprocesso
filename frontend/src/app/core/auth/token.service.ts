import { Injectable } from '@angular/core';
import { TokenPair } from '../models/application.models';

const ACCESS_KEY = 'auth.access';
const REFRESH_KEY = 'auth.refresh';

@Injectable({ providedIn: 'root' })
export class TokenService {
  get accessToken() { return sessionStorage.getItem(ACCESS_KEY); }
  get refreshToken() { return sessionStorage.getItem(REFRESH_KEY); }

  store(tokens: Partial<TokenPair>) {
    if (tokens.access) sessionStorage.setItem(ACCESS_KEY, tokens.access);
    if (tokens.refresh) sessionStorage.setItem(REFRESH_KEY, tokens.refresh);
  }

  clear() { sessionStorage.removeItem(ACCESS_KEY); sessionStorage.removeItem(REFRESH_KEY); }
}
