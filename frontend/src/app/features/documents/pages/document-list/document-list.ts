import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { DocumentCategory, DocumentItem } from '../../models/document.models';
import { DocumentService } from '../../services/document.service';

@Component({
  selector: 'app-document-list', imports: [DatePipe, FormsModule, RouterLink, PageHeader, StatusBadge],
  template: `
    <app-page-header title="Documentos" description="Consulte e organize os documentos disponíveis.">
      @if (auth.isAdmin()) { <a class="btn btn-primary" routerLink="/documentos/novo">+ Novo documento</a> }
    </app-page-header>
    <section class="card border-0 shadow-sm">
      <div class="card-body border-bottom"><div class="row g-3">
        <div class="col-12 col-lg-4"><label class="form-label" for="document-search">Buscar</label><input id="document-search" class="form-control" type="search" placeholder="Título, descrição ou categoria" [(ngModel)]="search" (keyup.enter)="applyFilters()"></div>
        <div class="col-12 col-sm-6 col-lg-3"><label class="form-label" for="category">Categoria</label><select id="category" class="form-select" [(ngModel)]="category" (change)="applyFilters()"><option value="">Todas</option>@for (item of categories(); track item.id) { <option [value]="item.id">{{ item.name }}</option> }</select></div>
        @if (auth.isAdmin()) { <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="status">Status</label><select id="status" class="form-select" [(ngModel)]="status" (change)="applyFilters()"><option value="">Todos</option><option value="true">Ativos</option><option value="false">Inativos</option></select></div> }
        <div class="col-12 col-sm-6 col-lg-3"><label class="form-label" for="ordering">Ordenar por</label><select id="ordering" class="form-select" [(ngModel)]="ordering" (change)="applyFilters()"><option value="-updated_at">Mais recentes</option><option value="updated_at">Mais antigos</option><option value="title">Título A–Z</option><option value="-title">Título Z–A</option></select></div>
      </div></div>
      @if (error()) { <div class="alert alert-danger m-3" role="alert">Não foi possível carregar os documentos.</div> }
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Documento</th><th>Categoria/Tipo</th><th>Responsável</th><th>Atualização</th><th>Status</th><th class="text-end">Ações</th></tr></thead><tbody>
        @for (document of documents(); track document.id) { <tr><td><strong class="d-block">{{ document.title }}</strong><small class="text-body-secondary">{{ document.description || 'Sem descrição' }}</small></td><td><span class="badge text-bg-light border">{{ document.category_name }}</span><small class="d-block text-body-secondary mt-1">{{ document.source_type === 'file' ? extension(document) : 'Link externo' }}</small></td><td>{{ document.created_by_name }}</td><td class="text-nowrap">{{ document.updated_at | date:'short' }}</td><td><app-status-badge [active]="document.active" /></td><td class="text-end text-nowrap"><a class="btn btn-sm btn-light me-1" [routerLink]="['/documentos', document.id]">Visualizar</a>@if (document.file_url) { <button class="btn btn-sm btn-outline-secondary me-1" type="button" (click)="openFile(document)">Abrir</button> } @else { <a class="btn btn-sm btn-outline-secondary me-1" [href]="document.external_url" target="_blank" rel="noopener noreferrer">Abrir</a> } @if (auth.isAdmin()) { <a class="btn btn-sm btn-outline-primary me-1" [routerLink]="['/documentos', document.id, 'editar']">Editar</a><button class="btn btn-sm btn-outline-secondary" type="button" (click)="toggle(document)">{{ document.active ? 'Desativar' : 'Ativar' }}</button> }</td></tr> }
        @empty { @if (!loading()) { <tr><td colspan="6" class="text-center text-body-secondary py-5">Nenhum documento encontrado.</td></tr> } }
      </tbody></table></div>
      <div class="card-footer bg-white d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2"><small class="text-body-secondary">{{ loading() ? 'Carregando…' : 'Exibindo ' + documents().length + ' de ' + count() + ' documentos' }}</small><nav aria-label="Paginação"><ul class="pagination pagination-sm mb-0"><li class="page-item" [class.disabled]="page() === 1"><button class="page-link" type="button" (click)="goTo(page() - 1)">Anterior</button></li><li class="page-item active"><span class="page-link">{{ page() }}</span></li><li class="page-item" [class.disabled]="!next()"><button class="page-link" type="button" (click)="goTo(page() + 1)">Próxima</button></li></ul></nav></div>
    </section>`
})
export class DocumentList {
  readonly auth = inject(AuthService); private readonly api = inject(DocumentService);
  readonly documents = signal<DocumentItem[]>([]); readonly categories = signal<DocumentCategory[]>([]);
  readonly count = signal(0); readonly next = signal<string | null>(null); readonly page = signal(1);
  readonly loading = signal(true); readonly error = signal(false);
  search = ''; category = ''; status = ''; ordering = '-updated_at';
  constructor() { this.api.categories().subscribe(response => this.categories.set(response.results)); this.load(); }
  applyFilters() { this.page.set(1); this.load(); }
  goTo(page: number) { if (page < 1 || (page > this.page() && !this.next())) return; this.page.set(page); this.load(); }
  toggle(document: DocumentItem) { this.api.update(document.id, { active: !document.active }).subscribe({ next: () => this.load(), error: () => this.error.set(true) }); }
  extension(document: DocumentItem) { return document.file_name?.split('.').pop()?.toUpperCase() || 'Arquivo'; }
  openFile(document: DocumentItem) { this.api.download(document.id).subscribe({ next: blob => { const url = URL.createObjectURL(blob); window.open(url, '_blank', 'noopener,noreferrer'); setTimeout(() => URL.revokeObjectURL(url), 60_000); }, error: () => this.error.set(true) }); }
  private load() { this.loading.set(true); this.error.set(false); this.api.list({ search: this.search, category: this.category, active: this.status, ordering: this.ordering, page: this.page() }).subscribe({ next: result => { this.documents.set(result.results); this.count.set(result.count); this.next.set(result.next); this.loading.set(false); }, error: () => { this.error.set(true); this.loading.set(false); } }); }
}
