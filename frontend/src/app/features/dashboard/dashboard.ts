import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { APPLICATION_CONFIG } from '../../core/config/application.config';
import { AuthService } from '../../core/auth/auth.service';
import { DashboardSummary, FinancialDashboardSummary, ProcessDashboardSummary } from '../../core/models/application.models';
import { DashboardService } from '../../core/services/dashboard.service';
import { AppIcon } from '../../shared/components/app-icon/app-icon';
import { PageHeader } from '../../shared/components/page-header/page-header';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, CurrencyPipe, DatePipe, AppIcon, PageHeader],
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

    @if (processes(); as processTotals) {
      <section class="mb-4" aria-labelledby="operational-title"><div class="d-flex justify-content-between align-items-end mb-2"><div><h2 id="operational-title" class="h5 mb-1">Operação de processos</h2><small class="text-body-secondary">Parado significa sem atualização há mais de {{ processTotals.stalled_days }} dias.</small></div><small class="text-body-secondary d-none d-sm-block">Atualizado em {{ processTotals.as_of | date:'short' }}</small></div><div class="metrics-grid operational-grid">
        <a class="metric metric-link" routerLink="/processos" [queryParams]="{ scope: 'my-action' }"><div class="metric-top"><span>Aguardando minha ação</span></div><strong>{{ processTotals.my_action }}</strong><small>Abrir caixa de trabalho</small></a>
        <a class="metric metric-link" routerLink="/processos" [queryParams]="{ scope: 'my-sector' }"><div class="metric-top"><span>No meu setor</span></div><strong>{{ processTotals.my_sector }}</strong><small>Processos ativos do escopo</small></a>
        <a class="metric metric-link" routerLink="/processos" [queryParams]="{ scope: 'my-action', search: 'aprova' }"><div class="metric-top"><span>Aguardando aprovação</span></div><strong>{{ processTotals.awaiting_approval }}</strong><small>Ações de aprovação elegíveis</small></a>
        <a class="metric metric-link" routerLink="/processos" [queryParams]="{ scope: 'my-sector', stalled: 'true', ordering: 'updated_at' }"><div class="metric-top"><span>Processos parados</span></div><strong [class.text-danger]="processTotals.stalled > 0">{{ processTotals.stalled }}</strong><small>Mais de {{ processTotals.stalled_days }} dias</small></a>
      </div></section>
      @if (processTotals.by_stage.length) { <section class="panel mb-4"><header class="panel-header"><div><h2>Distribuição por etapa</h2><p>Estado atual dos processos no seu escopo</p></div></header><div class="d-flex flex-wrap gap-2 p-3">@for (stage of processTotals.by_stage; track stage.current_stage_id) { <a class="btn btn-sm btn-light border" routerLink="/processos" [queryParams]="{ scope: 'my-sector', stage: stage.current_stage_id }">{{ stage.current_stage__name }} <span class="badge text-bg-primary ms-1">{{ stage.count }}</span></a> }</div></section> }
    }
    @if (financial(); as finance) { <section class="mb-4" aria-labelledby="financial-title"><div class="d-flex justify-content-between align-items-end mb-2"><h2 id="financial-title" class="h5 mb-0">Financeiro</h2><small class="text-body-secondary">Atualizado em {{ finance.as_of | date:'short' }}</small></div><div class="metrics-grid"><a class="metric metric-link" routerLink="/pagamentos" [queryParams]="{ status: 'PENDING' }"><div class="metric-top"><span>Pagamentos pendentes</span></div><strong>{{ finance.pending }}</strong><small>{{ finance.pending_total | currency:'BRL':'symbol':'1.2-2':'pt-BR' }}</small></a><a class="metric metric-link" routerLink="/pagamentos" [queryParams]="{ deadline: 'overdue' }"><div class="metric-top"><span>Pagamentos vencidos</span></div><strong class="text-danger">{{ finance.overdue }}</strong><small>Vencimento anterior a hoje</small></a><a class="metric metric-link" routerLink="/pagamentos" [queryParams]="{ deadline: 'upcoming' }"><div class="metric-top"><span>Próximos 7 dias</span></div><strong>{{ finance.due_next_7_days }}</strong><small>{{ finance.due_this_month }} vencem neste mês</small></a><a class="metric metric-link" routerLink="/pagamentos" [queryParams]="{ status: 'SCHEDULED' }"><div class="metric-top"><span>Agendados</span></div><strong>{{ finance.scheduled }}</strong><small>Pagamentos programados</small></a></div></section> }

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
  readonly processes = signal<ProcessDashboardSummary | null>(null);
  readonly financial = signal<FinancialDashboardSummary | null>(null);
  constructor() { this.service.summary().subscribe({ next: summary => this.summary.set(summary) }); if(this.auth.can('processes.view_administrativeprocess'))this.service.processes().subscribe({next:summary=>this.processes.set(summary)}); if(this.auth.can('payments.view_payment')&&this.auth.can('payments.view_financial_data'))this.service.financial().subscribe({next:summary=>this.financial.set(summary)}); }
}
