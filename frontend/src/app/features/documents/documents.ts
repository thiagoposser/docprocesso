import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DemoDataService } from '../../core/services/demo-data.service';
import { PageHeader } from '../../shared/components/page-header/page-header';

@Component({
  selector: 'app-documents', imports: [FormsModule, PageHeader],
  template: `
    <app-page-header title="Documentos" description="Consulte e organize os documentos disponíveis." />
    <section class="card border-0 shadow-sm"><div class="card-body border-bottom"><div class="row g-3"><div class="col-12 col-md-8"><label class="form-label" for="document-search">Buscar</label><input id="document-search" class="form-control" type="search" placeholder="Nome ou descrição" [ngModel]="search()" (ngModelChange)="search.set($event)"></div><div class="col-12 col-md-4"><label class="form-label" for="category">Categoria</label><select id="category" class="form-select" [ngModel]="category()" (ngModelChange)="category.set($event)"><option value="">Todas</option>@for (item of categories; track item) { <option [value]="item">{{ item }}</option> }</select></div></div></div>
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Documento</th><th>Categoria</th><th>Última atualização</th><th class="text-end">Ação</th></tr></thead><tbody>
      @for (document of filtered(); track document.id) { <tr><td><strong class="d-block">{{ document.name }}</strong><small class="text-body-secondary">{{ document.description }}</small></td><td><span class="badge text-bg-light border">{{ document.category }}</span></td><td class="text-nowrap">{{ document.updatedAt }}</td><td class="text-end"><button class="btn btn-sm btn-outline-primary" type="button">Visualizar</button></td></tr> } @empty { <tr><td colspan="4" class="text-center text-body-secondary py-5">Nenhum documento encontrado.</td></tr> }
      </tbody></table></div>
    </section>
  `
})
export class Documents {
  private readonly data = inject(DemoDataService);
  readonly search = signal(''); readonly category = signal('');
  readonly categories = [...new Set(this.data.documents.map(item => item.category))];
  readonly filtered = computed(() => { const term = this.search().toLowerCase(); return this.data.documents.filter(item => (!term || `${item.name} ${item.description}`.toLowerCase().includes(term)) && (!this.category() || item.category === this.category())); });
}
