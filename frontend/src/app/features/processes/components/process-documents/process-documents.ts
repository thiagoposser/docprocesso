import { DatePipe } from '@angular/common';
import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { concatMap, finalize, from, toArray } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { DocumentCategory } from '../../../documents/models/document.models';
import { DocumentService } from '../../../documents/services/document.service';
import { ProcessDocument, ProcessItem } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-documents',
  imports: [DatePipe, ReactiveFormsModule],
  template: `
    <section class="card border-0 shadow-sm mt-4">
      <div class="card-header bg-white p-3 d-flex justify-content-between align-items-center">
        <div><h2 class="h5 mb-1">Documentos e anexos</h2><small class="text-body-secondary">Dossiê vinculado a este processo.</small></div>
        @if (canAdd()) { <button class="btn btn-sm btn-primary" type="button" (click)="showForm.set(!showForm())">+ Documento</button> }
      </div>
      @if (showForm()) {
        <form class="card-body border-bottom" [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <div class="row g-3">
            <div class="col-md-5"><label class="form-label" for="process-document-title">Título</label><input id="process-document-title" class="form-control" maxlength="200" formControlName="title"></div>
            <div class="col-md-4"><label class="form-label" for="process-document-category">Categoria</label><select id="process-document-category" class="form-select" formControlName="category"><option value="">Selecione</option>@for (category of categories(); track category.id) { <option [value]="category.id">{{ category.name }}</option> }</select></div>
            <div class="col-md-3"><label class="form-label" for="process-document-files">Anexos</label><input id="process-document-files" class="form-control" type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.png,.jpg,.jpeg" (change)="selectFiles($event)"></div>
            <div class="col-12"><label class="form-label" for="process-document-description">Descrição</label><textarea id="process-document-description" class="form-control" rows="2" formControlName="description"></textarea></div>
          </div>
          @if (selectedNames()) { <small class="d-block text-body-secondary mt-2">Selecionados: {{ selectedNames() }}</small> }
          @if (submitError()) { <div class="alert alert-danger mt-3 mb-0" role="alert">{{ submitError() }}</div> }
          <div class="d-flex justify-content-end mt-3"><button class="btn btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Enviando…' : 'Criar e anexar' }}</button></div>
        </form>
      }
      <div class="list-group list-group-flush">
        @for (item of documents(); track item.id) {
          <article class="list-group-item p-3">
            <div class="d-flex justify-content-between gap-3"><div><strong>{{ item.title }}</strong><small class="d-block text-body-secondary">{{ item.category_name }} · {{ item.updated_at | date:'short' }}</small></div><span class="badge text-bg-light border align-self-start">{{ item.attachments.length }} anexo(s)</span></div>
            @if (item.description) { <p class="small text-body-secondary mt-2 mb-2">{{ item.description }}</p> }
            <div class="d-flex flex-column gap-2">@for (attachment of item.attachments; track attachment.id) { <div class="d-flex justify-content-between align-items-center border rounded p-2" [class.opacity-50]="!attachment.active"><span class="small">{{ attachment.file_name || (attachment.source_type === 'external_url' ? 'Link externo' : 'Arquivo') }} @if (!attachment.active) { <span class="text-danger">(removido)</span> }</span><div>@if (attachment.active) { <button class="btn btn-sm btn-outline-primary me-1" type="button" (click)="download(attachment.id, attachment.file_name)">Abrir</button>@if (canChange()) { <button class="btn btn-sm btn-outline-secondary" type="button" (click)="deactivate(attachment.id)">Inativar</button> } }</div></div> }</div>
          </article>
        } @empty { @if (!loading()) { <div class="p-4 text-center text-body-secondary">Nenhum documento vinculado.</div> } }
      </div>
      @if (error()) { <div class="alert alert-danger m-3" role="alert">{{ error() }}</div> }
    </section>
  `
})
export class ProcessDocuments implements OnInit {
  readonly process = input.required<ProcessItem>();
  readonly changed = output<void>();
  private readonly api = inject(ProcessService);
  private readonly documentApi = inject(DocumentService);
  private readonly auth = inject(AuthService);
  private files: File[] = [];
  readonly documents = signal<ProcessDocument[]>([]);
  readonly categories = signal<DocumentCategory[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly showForm = signal(false);
  readonly error = signal('');
  readonly submitError = signal('');
  readonly selectedNames = signal('');
  readonly form = new FormGroup({
    title: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    description: new FormControl('', { nonNullable: true }),
    category: new FormControl('', { nonNullable: true, validators: [Validators.required] })
  });

  ngOnInit() { this.load(); this.documentApi.categories().subscribe({ next: page => this.categories.set(page.results) }); }
  private sector() { return this.process().current_sector || this.process().origin_sector; }
  canAdd() { return !['COMPLETED', 'CANCELLED', 'ARCHIVED'].includes(this.process().status) && this.auth.canInSector('processes.view_administrativeprocess', this.sector()) && this.auth.can('documents.add_document') && this.auth.can('documents.add_attachment'); }
  canChange() { return this.auth.canInSector('processes.view_administrativeprocess', this.sector()) && this.auth.can('documents.change_document') && this.auth.can('documents.change_attachment'); }
  selectFiles(event: Event) { this.files = Array.from((event.target as HTMLInputElement).files || []); this.selectedNames.set(this.files.map(file => file.name).join(', ')); }
  submit() {
    this.form.markAllAsTouched();
    const invalidFile = this.files.find(file => file.size > 10 * 1024 * 1024 || !/\.(pdf|docx?|xlsx?|txt|png|jpe?g)$/i.test(file.name));
    if (this.form.invalid || !this.files.length || invalidFile || this.saving()) { this.submitError.set(invalidFile ? `O arquivo ${invalidFile.name} possui extensão ou tamanho inválido.` : 'Informe título, categoria e ao menos um anexo.'); return; }
    const value = this.form.getRawValue(); this.saving.set(true); this.submitError.set('');
    this.api.createDocument(this.process().id, { title: value.title.trim(), description: value.description.trim(), category: Number(value.category) }).pipe(
      concatMap(document => from(this.files).pipe(concatMap(file => this.api.addAttachment(document.id, file)), toArray())), finalize(() => this.saving.set(false))
    ).subscribe({ next: () => { this.form.reset(); this.files = []; this.selectedNames.set(''); this.showForm.set(false); this.load(); this.changed.emit(); }, error: () => { this.submitError.set('Parte do envio pode ter sido concluída. Atualize o dossiê antes de tentar novamente.'); this.load(); this.changed.emit(); } });
  }
  download(id: number, name: string | null) { this.api.downloadAttachment(id).subscribe({ next: blob => { if (blob.type.includes('json')) { blob.text().then(text => { const target = JSON.parse(text).external_url; if (target) window.open(target, '_blank', 'noopener,noreferrer'); }); return; } const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = name || 'anexo'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 60_000); }, error: () => this.error.set('Não foi possível baixar o anexo.') }); }
  deactivate(id: number) { if (!window.confirm('Inativar este anexo?')) return; this.api.deactivateAttachment(id).subscribe({ next: () => { this.load(); this.changed.emit(); }, error: () => this.error.set('Não foi possível inativar o anexo.') }); }
  private load() { this.loading.set(true); this.error.set(''); this.api.documents(this.process().id).subscribe({ next: page => { this.documents.set(page.results); this.loading.set(false); }, error: () => { this.error.set('Não foi possível carregar o dossiê.'); this.loading.set(false); } }); }
}
