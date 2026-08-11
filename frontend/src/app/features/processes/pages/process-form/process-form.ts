import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin, of } from 'rxjs';

import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { FlatSectorNode, SectorTreeNode } from '../../../sectors/models/sector.models';
import { SectorService } from '../../../sectors/services/sector.service';
import { ProcessPayload, ProcessType } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-form', imports: [ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header [title]="id ? 'Editar processo' : 'Novo processo'" description="Informe os dados básicos do processo administrativo."><a class="btn btn-outline-secondary" [routerLink]="id ? ['/processos', id] : ['/processos']">Voltar</a></app-page-header>
    @if (loading()) { <div class="card border-0 shadow-sm"><div class="card-body p-5 text-center text-body-secondary">Carregando…</div></div> } @else {
      @if (notEditable()) { <div class="alert alert-warning" role="alert">Somente processos em rascunho podem ser editados.</div> }
      <form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body row g-3 p-4">
        <div class="col-12 col-lg-8"><label class="form-label" for="process-title">Título</label><input id="process-title" class="form-control" maxlength="200" formControlName="title" [class.is-invalid]="invalid('title')"><div class="invalid-feedback">Informe o título do processo.</div></div>
        <div class="col-12 col-lg-4"><label class="form-label" for="process-type">Tipo</label><select id="process-type" class="form-select" formControlName="process_type" [class.is-invalid]="invalid('process_type')"><option value="">Selecione</option>@for (item of types(); track item.id) { <option [value]="item.id">{{ item.name }}</option> }</select><div class="invalid-feedback">Selecione um tipo.</div></div>
        <div class="col-12"><label class="form-label" for="process-description">Descrição</label><textarea id="process-description" class="form-control" rows="5" formControlName="description"></textarea></div>
        <div class="col-12 col-md-7"><label class="form-label" for="process-origin">Setor de origem</label><select id="process-origin" class="form-select" formControlName="origin_sector" [class.is-invalid]="invalid('origin_sector')"><option value="">Selecione</option>@for (item of sectors(); track item.id) { <option [value]="item.id">{{ '— '.repeat(item.level) }}{{ item.name }}</option> }</select><div class="invalid-feedback">Selecione o setor de origem.</div>@if (id) { <div class="form-text">O setor de origem não pode ser alterado após a criação.</div> }</div>
        <div class="col-12 col-md-5"><label class="form-label" for="process-assignee">ID do responsável</label><input id="process-assignee" class="form-control" type="number" min="1" formControlName="assignee"><div class="form-text">Opcional. Informe o ID de um usuário existente.</div></div>
      </div><div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" [routerLink]="id ? ['/processos', id] : ['/processos']">Cancelar</a><button class="btn btn-primary" type="submit" [disabled]="saving() || notEditable()">{{ saving() ? 'Salvando…' : 'Salvar processo' }}</button></div></form>
    }
    @if (error()) { <div class="alert alert-danger mt-3" role="alert">{{ error() }}</div> }
  `
})
export class ProcessForm {
  private readonly fb = inject(FormBuilder); private readonly api = inject(ProcessService); private readonly sectorApi = inject(SectorService); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  readonly id = Number(this.route.snapshot.paramMap.get('id')) || 0; readonly loading = signal(true); readonly saving = signal(false); readonly error = signal(''); readonly notEditable = signal(false);
  readonly types = signal<ProcessType[]>([]); readonly sectors = signal<FlatSectorNode[]>([]);
  readonly form = this.fb.nonNullable.group({ title: ['', Validators.required], description: [''], process_type: ['', Validators.required], origin_sector: ['', Validators.required], assignee: [''] });
  constructor() { const item$ = this.id ? this.api.get(this.id) : of(null); forkJoin({ types: this.api.types(), tree: this.sectorApi.tree('true'), item: item$ }).subscribe({ next: ({ types, tree, item }) => { const sectors = this.flatten(tree); if (item && !types.some(type => type.id === item.process_type)) types.push({ id: item.process_type, name: `${item.process_type_name} (inativo)`, code: '', description: '' }); if (item && !sectors.some(sector => sector.id === item.origin_sector)) sectors.unshift({ id: item.origin_sector, name: `${item.origin_sector_name} (inativo)`, code: null, parent: null, manager: null, manager_name: null, active: false, children: [], level: 0 }); this.types.set(types); this.sectors.set(sectors); if (item) { this.notEditable.set(item.status !== 'DRAFT'); this.form.patchValue({ title: item.title, description: item.description || '', process_type: String(item.process_type), origin_sector: String(item.origin_sector), assignee: item.assignee ? String(item.assignee) : '' }); this.form.controls.origin_sector.disable(); } this.loading.set(false); }, error: response => { this.error.set(this.errorMessage(response)); this.loading.set(false); } }); }
  invalid(name: string) { const control = this.form.get(name); return Boolean(control?.invalid && (control.dirty || control.touched)); }
  submit() { this.form.markAllAsTouched(); if (this.form.invalid || this.saving() || this.notEditable()) return; const value = this.form.getRawValue(); const payload: ProcessPayload = { title: value.title.trim(), description: value.description.trim(), process_type: Number(value.process_type), origin_sector: Number(value.origin_sector), assignee: value.assignee ? Number(value.assignee) : null }; this.saving.set(true); this.error.set(''); const request = this.id ? this.api.update(this.id, payload) : this.api.create(payload); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: item => this.router.navigate(['/processos', item.id]), error: response => this.error.set(this.firstError(response.error) || this.errorMessage(response)) }); }
  private errorMessage(response: { status?: number }) { return response?.status === 403 ? 'Você não possui permissão para esta operação.' : response?.status === 404 ? 'Processo não encontrado ou fora do seu escopo.' : response?.status === 409 ? 'O processo foi alterado por outro usuário. Recarregue antes de salvar.' : 'Não foi possível carregar ou salvar o processo.'; }
  private firstError(error: unknown): string { if (!error || typeof error !== 'object') return ''; const value = Object.values(error as Record<string, unknown>)[0]; return Array.isArray(value) ? String(value[0]) : String(value || ''); }
  private flatten(nodes: SectorTreeNode[], level = 0): FlatSectorNode[] { return nodes.flatMap(node => [{ ...node, level }, ...this.flatten(node.children, level + 1)]); }
}
