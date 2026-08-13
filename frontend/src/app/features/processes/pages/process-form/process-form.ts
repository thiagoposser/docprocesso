import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin, of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { UserSectorMembershipSummary } from '../../../../core/models/application.models';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { ProcessPayload, ProcessType } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-form', imports: [ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header [title]="id ? 'Editar processo' : 'Novo processo'" description="Informe os dados básicos do processo administrativo."><a class="btn btn-outline-secondary" [routerLink]="id ? ['/processos', id] : ['/processos']">Voltar</a></app-page-header>
    @if (loading()) { <div class="card border-0 shadow-sm"><div class="card-body p-5 text-center text-body-secondary">Carregando…</div></div> } @else {
      @if (notEditable()) { <div class="alert alert-warning" role="alert">Somente processos em rascunho podem ser editados.</div> }
      @if (!id && !memberships().length) { <div class="alert alert-warning" role="alert">Você precisa de um vínculo organizacional ativo e vigente para criar um processo.</div> }
      <form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body row g-3 p-4">
        <div class="col-12 col-lg-8"><label class="form-label" for="process-title">Título</label><input id="process-title" class="form-control" maxlength="200" formControlName="title" [class.is-invalid]="invalid('title')"><div class="invalid-feedback">Informe o título do processo.</div></div>
        <div class="col-12 col-lg-4"><label class="form-label" for="process-type">Classificação do processo</label><select id="process-type" class="form-select" formControlName="process_type" [class.is-invalid]="invalid('process_type')"><option value="">Selecione</option>@for (item of types(); track item.id) { <option [value]="item.id">{{ item.name }}</option> }</select><div class="invalid-feedback">Selecione uma classificação.</div><div class="form-text">Indica a finalidade do processo; não define seu fluxo nem o tipo dos documentos.</div></div>
        <div class="col-12"><label class="form-label" for="process-description">Descrição</label><textarea id="process-description" class="form-control" rows="5" formControlName="description"></textarea></div>
        <div class="col-12"><label class="form-label" [attr.for]="memberships().length > 1 && !id ? 'process-origin' : null">Origem organizacional</label>
          @if (id) { <div class="form-control bg-body-tertiary">{{ existingOrigin() }}</div><div class="form-text">A origem não pode ser alterada após a criação.</div> }
          @else if (memberships().length > 1) { <select id="process-origin" class="form-select" formControlName="origin_membership" [class.is-invalid]="invalid('origin_membership')"><option value="">Selecione um vínculo</option>@for (item of memberships(); track item.id) { <option [value]="item.id">{{ membershipLabel(item) }}</option> }</select><div class="invalid-feedback">Selecione um dos seus vínculos autorizados.</div> }
          @else if (memberships().length === 1) { <div class="form-control bg-body-tertiary">{{ membershipLabel(memberships()[0]) }}</div><div class="form-text">Origem determinada pelo seu vínculo vigente.</div> }
          @else { <div class="form-control bg-body-tertiary text-body-secondary">Nenhuma origem disponível</div> }
        </div>
      </div><div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" [routerLink]="id ? ['/processos', id] : ['/processos']">Cancelar</a><button class="btn btn-primary" type="submit" [disabled]="saving() || notEditable() || (!id && !memberships().length)">{{ saving() ? 'Salvando…' : 'Salvar processo' }}</button></div></form>
    }
    @if (error()) { <div class="alert alert-danger mt-3" role="alert">{{ error() }}</div> }
  `
})
export class ProcessForm {
  private readonly fb = inject(FormBuilder); private readonly api = inject(ProcessService); private readonly auth = inject(AuthService); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  readonly id = Number(this.route.snapshot.paramMap.get('id')) || 0; readonly loading = signal(true); readonly saving = signal(false); readonly error = signal(''); readonly notEditable = signal(false); readonly existingOrigin = signal('');
  readonly types = signal<ProcessType[]>([]); readonly memberships = signal<UserSectorMembershipSummary[]>([]);
  readonly form = this.fb.nonNullable.group({ title: ['', Validators.required], description: [''], process_type: ['', Validators.required], origin_membership: [''] });
  constructor() { const item$ = this.id ? this.api.get(this.id) : of(null); forkJoin({ types: this.api.types(), item: item$ }).subscribe({ next: ({ types, item }) => { if (item && !types.some(type => type.id === item.process_type)) types.push({ id: item.process_type, name: `${item.process_type_name} (inativo)`, code: '', description: '' }); this.types.set(types); this.memberships.set(this.auth.user()?.sector_memberships || []); if (!this.id && this.memberships().length > 1) this.form.controls.origin_membership.addValidators(Validators.required); if (item) { this.notEditable.set(item.status !== 'DRAFT'); this.existingOrigin.set(item.origin_sector_name); this.form.patchValue({ title: item.title, description: item.description || '', process_type: String(item.process_type) }); } this.loading.set(false); }, error: response => { this.error.set(this.errorMessage(response)); this.loading.set(false); } }); }
  invalid(name: string) { const control = this.form.get(name); return Boolean(control?.invalid && (control.dirty || control.touched)); }
  membershipLabel(item: UserSectorMembershipSummary) { return `${item.unit_name || 'Unidade não informada'} · ${item.sector_name}${item.function_name ? ' · ' + item.function_name : ''}${item.is_primary ? ' · Principal' : ''}`; }
  submit() { this.form.markAllAsTouched(); if (this.form.invalid || this.saving() || this.notEditable()) return; const value = this.form.getRawValue(); const membership = this.memberships().length === 1 ? this.memberships()[0].id : Number(value.origin_membership) || undefined; const payload: ProcessPayload = { title: value.title.trim(), description: value.description.trim(), process_type: Number(value.process_type), ...(!this.id && membership ? { origin_membership: membership } : {}) }; this.saving.set(true); this.error.set(''); const request = this.id ? this.api.update(this.id, payload) : this.api.create(payload); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: item => this.router.navigate(['/processos', item.id]), error: response => this.error.set(this.firstError(response.error) || this.errorMessage(response)) }); }
  private errorMessage(response: { status?: number }) { return response?.status === 403 ? 'Você não possui permissão ou vínculo vigente para esta operação.' : response?.status === 404 ? 'Processo não encontrado ou fora do seu escopo.' : response?.status === 409 ? 'O processo foi alterado por outro usuário. Recarregue antes de salvar.' : 'Não foi possível carregar ou salvar o processo.'; }
  private firstError(error: unknown): string { if (!error || typeof error !== 'object') return ''; const value = Object.values(error as Record<string, unknown>)[0]; return Array.isArray(value) ? String(value[0]) : String(value || ''); }
}
