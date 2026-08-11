import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin, of } from 'rxjs';

import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { FlatSectorNode, SectorTreeNode } from '../../models/sector.models';
import { SectorService } from '../../services/sector.service';

@Component({
  selector: 'app-sector-form', imports: [ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header [title]="id ? 'Editar setor' : 'Novo setor'" description="Informe a identificação, posição hierárquica e responsável."><a class="btn btn-outline-secondary" routerLink="/administracao/setores">Voltar</a></app-page-header>
    @if (loading()) { <div class="card border-0 shadow-sm"><div class="card-body p-5 text-center text-body-secondary">Carregando…</div></div> } @else {
      <form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body row g-3 p-4"><div class="col-12 col-md-8"><label class="form-label" for="sector-name">Nome</label><input id="sector-name" class="form-control" formControlName="name" [class.is-invalid]="invalid('name')"><div class="invalid-feedback">Informe o nome do setor.</div></div><div class="col-12 col-md-4"><label class="form-label" for="sector-code">Código/Sigla</label><input id="sector-code" class="form-control" maxlength="30" formControlName="code"></div><div class="col-12 col-md-7"><label class="form-label" for="sector-parent">Setor pai</label><select id="sector-parent" class="form-select" formControlName="parent"><option value="">Nenhum (raiz)</option>@for (sector of parentOptions(); track sector.id) { <option [value]="sector.id">{{ '— '.repeat(sector.level) }}{{ sector.name }}{{ sector.code ? ' (' + sector.code + ')' : '' }}</option> }</select><div class="form-text">O próprio setor e seus descendentes não podem ser selecionados.</div></div><div class="col-12 col-md-5"><label class="form-label" for="sector-manager">ID do responsável</label><input id="sector-manager" class="form-control" type="number" min="1" formControlName="manager"><div class="form-text">Opcional. Informe o ID de um usuário existente.</div></div><div class="col-12"><div class="form-check form-switch"><input id="sector-active" class="form-check-input" type="checkbox" formControlName="active"><label class="form-check-label" for="sector-active">Setor ativo</label></div></div></div><div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" routerLink="/administracao/setores">Cancelar</a><button class="btn btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Salvando…' : 'Salvar setor' }}</button></div></form>
    } @if (error()) { <div class="alert alert-danger mt-3" role="alert">{{ error() }}</div> }
  `
})
export class SectorForm {
  private readonly fb = inject(FormBuilder); private readonly api = inject(SectorService); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  readonly id = Number(this.route.snapshot.paramMap.get('id')) || 0; readonly loading = signal(true); readonly saving = signal(false); readonly error = signal(''); readonly parentOptions = signal<FlatSectorNode[]>([]);
  readonly form = this.fb.nonNullable.group({ name: ['', Validators.required], code: [''], parent: [''], manager: [''], active: [true] });
  constructor() { const item$ = this.id ? this.api.get(this.id) : of(null); forkJoin({ tree: this.api.tree(), item: item$ }).subscribe({ next: ({ tree, item }) => { const excluded = item ? this.descendantIds(tree, item.id) : new Set<number>(); if (item) excluded.add(item.id); this.parentOptions.set(this.flatten(tree).filter(node => !excluded.has(node.id) && (node.active || node.id === item?.parent))); if (item) this.form.patchValue({ name: item.name, code: item.code || '', parent: item.parent ? String(item.parent) : '', manager: item.manager ? String(item.manager) : '', active: item.active }); this.loading.set(false); }, error: () => { this.error.set('Não foi possível carregar o formulário.'); this.loading.set(false); } }); }
  invalid(name: string) { const control = this.form.get(name); return Boolean(control?.invalid && (control.dirty || control.touched)); }
  submit() { this.form.markAllAsTouched(); if (this.form.invalid || this.saving()) return; const value = this.form.getRawValue(); const payload = { name: value.name.trim(), code: value.code.trim() || null, parent: value.parent ? Number(value.parent) : null, manager: value.manager ? Number(value.manager) : null, active: value.active }; this.saving.set(true); this.error.set(''); const request = this.id ? this.api.update(this.id, payload) : this.api.create(payload); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: () => this.router.navigateByUrl('/administracao/setores'), error: response => this.error.set(this.firstError(response.error) || 'Não foi possível salvar o setor.') }); }
  private flatten(nodes: SectorTreeNode[], level = 0): FlatSectorNode[] { return nodes.flatMap(node => [{ ...node, level }, ...this.flatten(node.children, level + 1)]); }
  private descendantIds(nodes: SectorTreeNode[], id: number): Set<number> { const target = this.find(nodes, id); return new Set(target ? this.flatten(target.children).map(item => item.id) : []); }
  private find(nodes: SectorTreeNode[], id: number): SectorTreeNode | null { for (const node of nodes) { if (node.id === id) return node; const found = this.find(node.children, id); if (found) return found; } return null; }
  private firstError(error: unknown): string { if (!error || typeof error !== 'object') return ''; const value = Object.values(error as Record<string, unknown>)[0]; return Array.isArray(value) ? String(value[0]) : String(value || ''); }
}
