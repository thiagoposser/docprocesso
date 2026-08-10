import { Component, computed, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { AuthService } from '../../core/auth/auth.service';
import { PageHeader } from '../../shared/components/page-header/page-header';

@Component({
  selector: 'app-profile', imports: [PageHeader, DatePipe],
  template: `
    <app-page-header title="Meu perfil" description="Consulte seus dados pessoais e informações de acesso." />
    @if (user(); as currentUser) { <div class="row g-4"><div class="col-12 col-lg-8"><section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex flex-column flex-sm-row align-items-sm-center gap-3 mb-4"><div class="profile-avatar">{{ initials() }}</div><div><h2 class="h5 mb-1">{{ currentUser.name }}</h2><span class="text-body-secondary">&#64;{{ currentUser.username }}</span></div></div><dl class="row mb-0"><dt class="col-sm-4 text-body-secondary fw-normal">E-mail</dt><dd class="col-sm-8">{{ currentUser.email }}</dd><dt class="col-sm-4 text-body-secondary fw-normal">Grupos/Perfis</dt><dd class="col-sm-8">@for (group of currentUser.groups; track group) { <span class="badge text-bg-primary me-1">{{ group }}</span> } @empty { <span class="text-body-secondary">Sem grupo</span> }</dd><dt class="col-sm-4 text-body-secondary fw-normal">Último acesso</dt><dd class="col-sm-8 mb-0">{{ currentUser.last_login ? (currentUser.last_login | date:'short') : 'Primeiro acesso' }}</dd></dl></div></section></div>
    <div class="col-12 col-lg-4"><section class="card border-0 shadow-sm"><div class="card-header bg-white py-3"><h2 class="h6 mb-0">Ações da conta</h2></div><div class="card-body d-grid gap-2"><button class="btn btn-outline-primary" disabled>Editar dados</button><button class="btn btn-outline-secondary" disabled>Alterar senha</button><small class="text-body-secondary mt-2">Funcionalidades preparadas para integração futura.</small></div></section></div></div> }
  `,
  styles: [`.profile-avatar { display:grid;place-items:center;width:4rem;height:4rem;border-radius:.8rem;color:#4a4ab8;background:#ededff;font-size:1.15rem;font-weight:750; }`]
})
export class Profile {
  private readonly auth = inject(AuthService); readonly user = this.auth.user;
  readonly initials = computed(() => (this.user()?.name || 'U').split(' ').slice(0, 2).map(part => part[0]).join(''));
}
