import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { APPLICATION_CONFIG } from '../../core/config/application.config';
import { AuthService } from '../../core/auth/auth.service';
import { DashboardSummary } from '../../core/models/application.models';
import { DashboardService } from '../../core/services/dashboard.service';
import { AppIcon } from '../../shared/components/app-icon/app-icon';
import { PageHeader } from '../../shared/components/page-header/page-header';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, DatePipe, AppIcon, PageHeader],
  template: `
    <app-page-header title="Visão geral" [description]="'Bom dia, ' + firstName + '. Aqui está o resumo do seu workspace.'">
      <span class="demo-label"><span></span> Dados atualizados pela API</span>
    </app-page-header>

    <div class="metrics-grid mb-4">
      <article class="metric"><div class="metric-top"><span>Usuários ativos</span><app-icon name="user" /></div><strong>{{ summary()?.total_users ?? '—' }}</strong><small>Contas habilitadas</small></article>
      <article class="metric"><div class="metric-top"><span>Documentos</span><app-icon name="document" /></div><strong>{{ summary()?.total_documents ?? '—' }}</strong><small>Itens disponíveis</small></article>
      <article class="metric"><div class="metric-top"><span>Status da API</span><span class="status-dot" [class.offline]="summary()?.api_status !== 'operational'"></span></div><strong class="status-value" [class.text-danger]="summary()?.api_status !== 'operational'">{{ summary()?.api_status === 'operational' ? 'Operacional' : 'Indisponível' }}</strong><small>Health check autenticado</small></article>
      <article class="metric"><div class="metric-top"><span>Ambiente</span><span class="environment-dot"></span></div><strong>{{ summary()?.environment ?? config.environment }}</strong><small>Versão {{ summary()?.version ?? '—' }}</small></article>
    </div>

    <div class="row g-4">
      <div class="col-12 col-xl-7">
        <section class="panel h-100"><header class="panel-header"><div><h2>Atividades recentes</h2><p>Últimas movimentações do sistema</p></div><button class="btn btn-sm btn-light" type="button">Ver todas</button></header>
          <div class="timeline">
            @for (activity of summary()?.recent_activity || []; track activity.id) { <div class="timeline-item"><span class="timeline-icon"><app-icon name="check" [size]="16" /></span><div><strong>{{ activity.action }}</strong><p>{{ activity.description }} · {{ activity.user }}</p></div><time>{{ activity.created_at | date:'short' }}</time></div> } @empty { <div class="timeline-item"><span class="timeline-icon"><app-icon name="check" [size]="16" /></span><div><strong>Nenhuma atividade disponível</strong><p>As atividades administrativas aparecem somente para usuários autorizados.</p></div></div> }
          </div>
        </section>
      </div>
      <div class="col-12 col-xl-5">
        <section class="panel h-100"><header class="panel-header"><div><h2>Acesso rápido</h2><p>Atalhos frequentes</p></div></header>
          <div class="quick-grid">
            <a routerLink="/documentos"><span><app-icon name="document" /></span><div><strong>Documentos</strong><small>Consultar arquivos</small></div><app-icon name="arrow" [size]="14" /></a>
            @if (auth.isAdmin()) { <a routerLink="/administracao/usuarios/novo"><span><app-icon name="plus" /></span><div><strong>Novo usuário</strong><small>Criar novo acesso</small></div><app-icon name="arrow" [size]="14" /></a> }
            <a routerLink="/perfil"><span><app-icon name="user" /></span><div><strong>Meu perfil</strong><small>Dados da conta</small></div><app-icon name="arrow" [size]="14" /></a>
          </div>
        </section>
      </div>
    </div>
  `,
  styleUrl: './dashboard.scss'
})
export class Dashboard {
  readonly service = inject(DashboardService);
  readonly config = APPLICATION_CONFIG;
  readonly auth = inject(AuthService);
  readonly firstName = this.auth.user()?.name.split(' ')[0] || 'Usuário';
  readonly summary = signal<DashboardSummary | null>(null);
  constructor() { this.service.summary().subscribe({ next: summary => this.summary.set(summary) }); }
}
