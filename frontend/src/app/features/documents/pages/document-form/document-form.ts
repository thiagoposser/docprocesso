import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { DocumentCategory } from '../../models/document.models';
import { DocumentService } from '../../services/document.service';

const ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg'];
const MAX_BYTES = 10 * 1024 * 1024;

@Component({
  selector: 'app-document-form', imports: [ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header [title]="id ? 'Editar documento' : 'Novo documento'" description="Informe os dados e escolha um arquivo ou uma URL externa."><a class="btn btn-outline-secondary" routerLink="/documentos">Voltar</a></app-page-header>
    <form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body p-3 p-md-4"><div class="row g-3">
      <div class="col-12"><label class="form-label" for="title">Título</label><input id="title" class="form-control" formControlName="title" [class.is-invalid]="invalid('title')"><div class="invalid-feedback">Informe o título.</div></div>
      <div class="col-12"><label class="form-label" for="description">Descrição</label><textarea id="description" class="form-control" rows="3" formControlName="description"></textarea></div>
      <div class="col-12 col-md-7"><label class="form-label" for="category">Categoria</label><select id="category" class="form-select" formControlName="category" [class.is-invalid]="invalid('category')"><option value="">Selecione</option>@for (category of categories(); track category.id) { <option [value]="category.id">{{ category.name }}</option> }</select><div class="invalid-feedback">Selecione uma categoria.</div></div>
      <div class="col-12 col-md-5"><label class="form-label" for="new-category">Nova categoria</label><div class="input-group"><input id="new-category" class="form-control" #newCategory placeholder="Nome"><button class="btn btn-outline-secondary" type="button" (click)="createCategory(newCategory.value); newCategory.value = ''">Adicionar</button></div></div>
      <div class="col-12 col-md-6"><label class="form-label" for="file">Arquivo</label><input id="file" class="form-control" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.png,.jpg,.jpeg" (change)="selectFile($event)"><div class="form-text">PDF, Office, texto ou imagem. Máximo de 10 MB.</div>@if (existingFile()) { <small class="text-body-secondary">Arquivo atual: {{ existingFile() }}</small> }</div>
      <div class="col-12 col-md-6"><label class="form-label" for="externalUrl">URL externa</label><input id="externalUrl" class="form-control" type="url" formControlName="externalUrl" placeholder="https://..." [class.is-invalid]="invalid('externalUrl')"><div class="invalid-feedback">Informe uma URL HTTP ou HTTPS válida.</div></div>
      <div class="col-12"><div class="form-check form-switch"><input id="active" class="form-check-input" type="checkbox" formControlName="active"><label class="form-check-label" for="active">Documento ativo</label></div></div>
    </div></div><div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" routerLink="/documentos">Cancelar</a><button class="btn btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Salvando…' : 'Salvar documento' }}</button></div></form>
    @if (sourceError()) { <div class="alert alert-warning mt-3">Informe somente um arquivo ou uma URL externa.</div> }
    @if (fileError()) { <div class="alert alert-warning mt-3">{{ fileError() }}</div> }
    @if (error()) { <div class="alert alert-danger mt-3">Não foi possível salvar. Revise os dados informados.</div> }
  `
})
export class DocumentForm {
  private readonly fb = inject(FormBuilder); private readonly api = inject(DocumentService); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  readonly id = Number(this.route.snapshot.paramMap.get('id')) || 0; readonly categories = signal<DocumentCategory[]>([]);
  readonly saving = signal(false); readonly error = signal(false); readonly sourceError = signal(false); readonly fileError = signal(''); readonly existingFile = signal<string | null>(null);
  private selected: File | null = null;
  readonly form = this.fb.nonNullable.group({ title: ['', Validators.required], description: [''], category: ['', Validators.required], externalUrl: ['', Validators.pattern(/^https?:\/\/.+/i)], active: [true] });
  constructor() { this.loadCategories(); if (this.id) this.api.get(this.id).subscribe(item => { this.existingFile.set(item.file_name); this.form.patchValue({ title: item.title, description: item.description, category: String(item.category), externalUrl: item.external_url, active: item.active }); }); }
  invalid(name: string) { const control = this.form.get(name); return Boolean(control?.invalid && (control.dirty || control.touched)); }
  selectFile(event: Event) { this.fileError.set(''); const file = (event.target as HTMLInputElement).files?.[0] ?? null; if (!file) { this.selected = null; return; } const extension = file.name.split('.').pop()?.toLowerCase() || ''; if (!ALLOWED_EXTENSIONS.includes(extension)) { this.fileError.set('Extensão de arquivo não permitida.'); this.selected = null; return; } if (file.size > MAX_BYTES) { this.fileError.set('O arquivo excede o limite de 10 MB.'); this.selected = null; return; } this.selected = file; }
  createCategory(name: string) { const value = name.trim(); if (!value) return; this.api.createCategory(value).subscribe({ next: category => { this.categories.update(items => [...items, category].sort((a, b) => a.name.localeCompare(b.name))); this.form.patchValue({ category: String(category.id) }); }, error: () => this.error.set(true) }); }
  submit() { this.form.markAllAsTouched(); this.sourceError.set(false); const value = this.form.getRawValue(); const hasFile = Boolean(this.selected || this.existingFile()); const hasUrl = Boolean(value.externalUrl.trim()); if (hasFile === hasUrl) this.sourceError.set(true); if (this.form.invalid || this.sourceError() || this.fileError() || this.saving()) return; const payload = new FormData(); payload.set('title', value.title); payload.set('description', value.description); payload.set('category', value.category); payload.set('external_url', value.externalUrl.trim()); payload.set('active', String(value.active)); if (this.selected) payload.set('file', this.selected); this.saving.set(true); this.error.set(false); const request = this.id ? this.api.update(this.id, payload) : this.api.create(payload); request.pipe(finalize(() => this.saving.set(false))).subscribe({ next: item => this.router.navigate(['/documentos', item.id]), error: () => this.error.set(true) }); }
  private loadCategories() { this.api.categories().subscribe({ next: response => this.categories.set(response.results.filter(item => item.active)), error: () => this.error.set(true) }); }
}
