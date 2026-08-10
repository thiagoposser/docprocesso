import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { UserItem } from '../../../../core/models/application.models';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { UserService } from '../services/user.service';

@Component({
  selector: 'app-user-list', imports: [FormsModule, RouterLink, DatePipe, PageHeader, StatusBadge],
  template: `
    <app-page-header title="Usuários" description="Gerencie acessos, perfis e situação dos usuários."><a class="btn btn-primary" routerLink="/administracao/usuarios/novo">+ Novo usuário</a></app-page-header>
    <section class="card border-0 shadow-sm"><div class="card-body border-bottom"><div class="row g-3"><div class="col-12 col-md-8"><label class="form-label" for="user-search">Buscar</label><input id="user-search" class="form-control" type="search" placeholder="Nome, e-mail ou usuário" [ngModel]="search()" (ngModelChange)="updateSearch($event)"></div><div class="col-12 col-md-4"><label class="form-label" for="status">Status</label><select id="status" class="form-select" [ngModel]="status()" (ngModelChange)="updateStatus($event)"><option value="all">Todos</option><option value="active">Ativos</option><option value="inactive">Inativos</option></select></div></div></div>
    @if (error()) { <div class="alert alert-danger m-3">Não foi possível carregar os usuários.</div> }
    <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Nome</th><th>E-mail</th><th>Usuário</th><th>Perfil/Grupo</th><th>Status</th><th>Último acesso</th><th class="text-end">Ações</th></tr></thead><tbody>
      @for (user of users(); track user.id) { <tr><td class="fw-semibold">{{ user.name }}</td><td>{{ user.email }}</td><td><code>{{ user.username }}</code></td><td>{{ user.groups.join(', ') || 'Sem grupo' }}</td><td><app-status-badge [active]="user.is_active" /></td><td class="text-nowrap">{{ user.last_login ? (user.last_login | date:'short') : 'Nunca' }}</td><td class="text-end text-nowrap"><a class="btn btn-sm btn-light me-1" [routerLink]="['/administracao/usuarios', user.id]">Ver</a><a class="btn btn-sm btn-outline-primary" [routerLink]="['/administracao/usuarios', user.id, 'editar']">Editar</a></td></tr> } @empty { @if (!loading()) { <tr><td colspan="7" class="text-center text-body-secondary py-5">Nenhum usuário encontrado.</td></tr> } }
    </tbody></table></div><div class="card-footer bg-white d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2"><small class="text-body-secondary">{{ loading() ? 'Carregando…' : 'Exibindo ' + users().length + ' de ' + count() + ' usuários' }}</small><nav aria-label="Paginação"><ul class="pagination pagination-sm mb-0"><li class="page-item disabled"><span class="page-link">Anterior</span></li><li class="page-item active"><span class="page-link">1</span></li><li class="page-item disabled"><span class="page-link">Próxima</span></li></ul></nav></div></section>
  `
})
export class UserList {
  private readonly api = inject(UserService); readonly users = signal<UserItem[]>([]); readonly count = signal(0); readonly loading = signal(true); readonly error = signal(false); readonly search = signal(''); readonly status = signal('all');
  constructor() { this.load(); }
  updateSearch(value: string) { this.search.set(value); this.load(); }
  updateStatus(value: string) { this.status.set(value); this.load(); }
  private load() { this.loading.set(true); this.error.set(false); this.api.list(this.search(), this.status()).subscribe({ next: page => { this.users.set(page.results); this.count.set(page.count); this.loading.set(false); }, error: () => { this.error.set(true); this.loading.set(false); } }); }
}
