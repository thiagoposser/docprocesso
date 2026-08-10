import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { UserPayload } from '../../../../core/models/application.models';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { UserService } from '../services/user.service';

@Component({
  selector: 'app-user-form', imports: [ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header [title]="title" [description]="description"><a class="btn btn-outline-secondary" routerLink="/administracao/usuarios">Voltar</a></app-page-header>
    <form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body p-3 p-md-4"><div class="row g-3">
      <div class="col-12 col-md-6"><label class="form-label" for="firstName">Nome</label><input id="firstName" class="form-control" formControlName="firstName" [class.is-invalid]="invalid('firstName')"><div class="invalid-feedback">Informe o nome.</div></div>
      <div class="col-12 col-md-6"><label class="form-label" for="lastName">Sobrenome</label><input id="lastName" class="form-control" formControlName="lastName"></div>
      <div class="col-12 col-md-6"><label class="form-label" for="email">E-mail</label><input id="email" class="form-control" type="email" formControlName="email" [class.is-invalid]="invalid('email')"><div class="invalid-feedback">Informe um e-mail válido.</div></div>
      <div class="col-12 col-md-6"><label class="form-label" for="username">Usuário</label><input id="username" class="form-control" formControlName="username" [class.is-invalid]="invalid('username')"><div class="invalid-feedback">Use pelo menos 3 caracteres.</div></div>
      @if (!id) { <div class="col-12 col-md-6"><label class="form-label" for="password">Senha inicial</label><input id="password" class="form-control" type="password" formControlName="password" [class.is-invalid]="invalid('password')"><div class="invalid-feedback">Use pelo menos 8 caracteres.</div></div> }
      <div class="col-12 col-md-6"><label class="form-label" for="group">Perfil/Grupo</label><select id="group" class="form-select" formControlName="group"><option>Administrador</option><option>Usuário</option></select></div>
      <div class="col-12"><div class="form-check form-switch"><input id="active" class="form-check-input" type="checkbox" formControlName="active"><label class="form-check-label" for="active">Usuário ativo</label></div></div>
    </div></div>
    @if (!viewMode) { <div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" routerLink="/administracao/usuarios">Cancelar</a><button class="btn btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Salvando…' : 'Salvar usuário' }}</button></div> }
    </form>
    @if (error()) { <div class="alert alert-danger mt-3" role="alert">Não foi possível salvar o usuário. Revise os dados informados.</div> }
  `
})
export class UserForm {
  private readonly fb = inject(FormBuilder); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router); private readonly api = inject(UserService);
  readonly viewMode = this.route.snapshot.data['mode'] === 'view'; readonly id = Number(this.route.snapshot.paramMap.get('id')) || 0; readonly saving = signal(false); readonly error = signal(false);
  readonly title = this.id ? (this.viewMode ? 'Detalhes do usuário' : 'Editar usuário') : 'Novo usuário'; readonly description = this.viewMode ? 'Consulte os dados e acessos do usuário.' : 'Preencha os dados cadastrais e defina o perfil de acesso.';
  readonly form = this.fb.nonNullable.group({ firstName: ['', Validators.required], lastName: [''], email: ['', [Validators.required, Validators.email]], username: ['', [Validators.required, Validators.minLength(3)]], password: ['', this.id ? [] : [Validators.required, Validators.minLength(8)]], group: ['Usuário', Validators.required], active: [true] });
  constructor() { if (this.id) this.api.get(this.id).subscribe(user => { this.form.patchValue({ firstName: user.first_name, lastName: user.last_name, email: user.email, username: user.username, group: user.groups[0] || 'Usuário', active: user.is_active }); if (this.viewMode) this.form.disable(); }); }
  invalid(control: string) { const field = this.form.get(control); return Boolean(field?.invalid && (field.dirty || field.touched)); }
  submit() { this.form.markAllAsTouched(); if (this.form.invalid || this.saving()) return; const value = this.form.getRawValue(); const payload: UserPayload = { first_name: value.firstName, last_name: value.lastName, email: value.email, username: value.username, is_active: value.active, group_names: [value.group], ...(this.id ? {} : { password: value.password }) }; this.saving.set(true); this.error.set(false); const request = this.id ? this.api.update(this.id, payload) : this.api.create(payload); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: () => this.router.navigateByUrl('/administracao/usuarios'), error: () => this.error.set(true) }); }
}
