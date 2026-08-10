import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../../core/auth/auth.service';
import { SettingsService } from '../../settings/services/settings.service';

@Component({
  selector: 'app-login', imports: [ReactiveFormsModule],
  template: `<main class="auth-page"><section class="card border-0 shadow-lg auth-card"><div class="card-body p-4 p-sm-5">@if (settings.logoUrl()) { <img class="login-logo mb-4" [src]="settings.logoUrl()" alt=""> } @else { <div class="brand-mark mb-4">{{ settings.shortName() }}</div> }<h1 class="h3">Acesse sua conta</h1><p class="text-body-secondary mb-4">Entre para continuar no {{ settings.name() }}.</p>
  @if (expired()) { <div class="alert alert-warning small">Sua sessão expirou. Entre novamente.</div> }
  @if (error()) { <div class="alert alert-danger small" role="alert">{{ error() }}</div> }
  <form [formGroup]="form" (ngSubmit)="submit()"><div class="mb-3"><label class="form-label" for="username">Usuário</label><input id="username" class="form-control" formControlName="username" autocomplete="username" [class.is-invalid]="form.controls.username.touched && form.controls.username.invalid"></div><div class="mb-4"><label class="form-label" for="password">Senha</label><input id="password" class="form-control" type="password" formControlName="password" autocomplete="current-password" [class.is-invalid]="form.controls.password.touched && form.controls.password.invalid"></div><button class="btn btn-primary w-100" type="submit" [disabled]="loading()">{{ loading() ? 'Entrando…' : 'Entrar' }}</button></form></div></section></main>`,
  styles: [`.auth-page{min-height:100vh;display:grid;place-items:center;padding:1.5rem;background:#f4f5f7}.auth-card{width:min(100%,27rem)}.brand-mark{display:grid;place-items:center;width:2.75rem;height:2.75rem;border-radius:.65rem;color:var(--color-primary);background:#ededff;font-weight:750}.login-logo{display:block;max-width:10rem;height:3rem;object-fit:contain}`]
})
export class Login {
  private readonly auth = inject(AuthService); private readonly router = inject(Router); private readonly route = inject(ActivatedRoute);
  readonly settings = inject(SettingsService); readonly loading = signal(false); readonly error = signal(''); readonly expired = signal(this.route.snapshot.queryParamMap.has('expired'));
  readonly form = new FormGroup({ username: new FormControl('', { nonNullable: true, validators: Validators.required }), password: new FormControl('', { nonNullable: true, validators: Validators.required }) });
  submit() { this.form.markAllAsTouched(); if (this.form.invalid || this.loading()) return; this.loading.set(true); this.error.set(''); this.auth.login(this.form.controls.username.value, this.form.controls.password.value).pipe(finalize(() => this.loading.set(false))).subscribe({ next: () => this.router.navigateByUrl(this.route.snapshot.queryParamMap.get('returnUrl') || '/dashboard'), error: () => this.error.set('Usuário ou senha inválidos.') }); }
}
