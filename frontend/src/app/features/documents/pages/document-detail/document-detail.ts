import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { DocumentItem } from '../../models/document.models';
import { DocumentService } from '../../services/document.service';

@Component({
  selector: 'app-document-detail', imports: [DatePipe, DecimalPipe, RouterLink, PageHeader, StatusBadge],
  template: `
    <app-page-header title="Detalhes do documento" description="Consulte as informações e acesse o conteúdo."><a class="btn btn-outline-secondary" routerLink="/documentos">Voltar</a>@if (auth.isAdmin() && document()) { <a class="btn btn-primary" [routerLink]="['/documentos', document()!.id, 'editar']">Editar</a> }</app-page-header>
    @if (error()) { <div class="alert alert-danger">Documento não encontrado ou indisponível.</div> }
    @if (document(); as item) { <section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex justify-content-between gap-3 mb-4"><div><h2 class="h4 mb-1">{{ item.title }}</h2><span class="badge text-bg-light border">{{ item.category_name }}</span></div><app-status-badge [active]="item.active" /></div><p class="text-body-secondary">{{ item.description || 'Sem descrição.' }}</p><dl class="row mb-4"><dt class="col-sm-4">Responsável</dt><dd class="col-sm-8">{{ item.created_by_name }}</dd><dt class="col-sm-4">Criado em</dt><dd class="col-sm-8">{{ item.created_at | date:'medium' }}</dd><dt class="col-sm-4">Atualizado em</dt><dd class="col-sm-8">{{ item.updated_at | date:'medium' }}</dd>@if (item.file_size) { <dt class="col-sm-4">Tamanho</dt><dd class="col-sm-8">{{ item.file_size / 1024 | number:'1.0-1' }} KB</dd> }</dl>@if (item.file_url) { <button class="btn btn-primary" type="button" (click)="openFile(item)">{{ item.file_name?.toLowerCase()?.endsWith('.pdf') ? 'Visualizar PDF' : 'Baixar arquivo' }}</button> } @else { <a class="btn btn-primary" [href]="item.external_url" target="_blank" rel="noopener noreferrer">Abrir link externo</a> }</div></section> }
  `
})
export class DocumentDetail {
  readonly auth = inject(AuthService); private readonly api = inject(DocumentService); private readonly route = inject(ActivatedRoute);
  readonly document = signal<DocumentItem | null>(null); readonly error = signal(false);
  constructor() { this.api.get(Number(this.route.snapshot.paramMap.get('id'))).subscribe({ next: item => this.document.set(item), error: () => this.error.set(true) }); }
  openFile(item: DocumentItem) { const attachment = !item.file_name?.toLowerCase().endsWith('.pdf'); this.api.download(item.id, attachment).subscribe({ next: blob => { const url = URL.createObjectURL(blob); window.open(url, '_blank', 'noopener,noreferrer'); setTimeout(() => URL.revokeObjectURL(url), 60_000); }, error: () => this.error.set(true) }); }
}
