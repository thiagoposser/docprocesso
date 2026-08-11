import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { FlatSectorNode, SectorTreeNode } from '../../../sectors/models/sector.models';
import { SectorService } from '../../../sectors/services/sector.service';
import { PAYMENT_STATUS_LABELS, Payment, PaymentDeadlineSummary, PaymentStatus, Supplier } from '../../models/payment.models';
import { PaymentService } from '../../services/payment.service';

@Component({
  selector: 'app-payment-list', imports: [CurrencyPipe, DatePipe, FormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header title="Pagamentos" description="Consulte obrigações financeiras autorizadas para seus setores.">@if (auth.can('payments.add_payment')) { <a class="btn btn-primary" routerLink="/pagamentos/novo">+ Novo pagamento</a> }</app-page-header>
    @if (summary(); as totals) { <div class="row g-3 mb-3"><div class="col-md-4"><button class="card card-body border-0 shadow-sm w-100 text-start" type="button" (click)="selectDeadline('overdue')"><strong class="text-danger">{{ totals.overdue }}</strong><small>Vencidos</small></button></div><div class="col-md-4"><button class="card card-body border-0 shadow-sm w-100 text-start" type="button" (click)="selectDeadline('today')"><strong class="text-warning">{{ totals.today }}</strong><small>Vencem hoje</small></button></div><div class="col-md-4"><button class="card card-body border-0 shadow-sm w-100 text-start" type="button" (click)="selectDeadline('upcoming')"><strong class="text-primary">{{ totals.upcoming }}</strong><small>Próximos 7 dias</small></button></div></div> }
    <section class="card border-0 shadow-sm"><div class="card-body border-bottom"><div class="row g-3">
      <div class="col-sm-6 col-lg-2"><label class="form-label" for="payment-deadline">Vencimento</label><select id="payment-deadline" class="form-select" [(ngModel)]="deadline" (change)="apply()"><option value="">Todos</option><option value="overdue">Vencidos</option><option value="today">Hoje</option><option value="upcoming">Próximos 7 dias</option></select></div>
      <div class="col-lg-3"><label class="form-label" for="payment-search">Buscar</label><input id="payment-search" class="form-control" [(ngModel)]="search" (keyup.enter)="apply()" placeholder="Descrição, fornecedor ou processo"></div>
      <div class="col-sm-6 col-lg-2"><label class="form-label" for="payment-status">Estado</label><select id="payment-status" class="form-select" [(ngModel)]="status" (change)="apply()"><option value="">Todos</option>@for (item of statuses; track item) { <option [value]="item">{{ labels[item] }}</option> }</select></div>
      <div class="col-sm-6 col-lg-2"><label class="form-label" for="payment-sector">Setor</label><select id="payment-sector" class="form-select" [(ngModel)]="sector" (change)="apply()"><option value="">Todos</option>@for (item of sectors(); track item.id) { <option [value]="item.id">{{ '— '.repeat(item.level) }}{{ item.name }}</option> }</select></div>
      <div class="col-sm-6 col-lg-2"><label class="form-label" for="payment-supplier">Fornecedor</label><select id="payment-supplier" class="form-select" [(ngModel)]="supplier" (change)="apply()"><option value="">Todos</option>@for (item of suppliers(); track item.id) { <option [value]="item.id">{{ item.name }}</option> }</select></div>
      <div class="col-sm-6 col-lg-1"><label class="form-label" for="payment-due-from">De</label><input id="payment-due-from" type="date" class="form-control" [(ngModel)]="dueFrom" (change)="apply()"></div>
      <div class="col-sm-6 col-lg-1"><label class="form-label" for="payment-due-to">Até</label><input id="payment-due-to" type="date" class="form-control" [(ngModel)]="dueTo" (change)="apply()"></div>
      <div class="col-sm-6 col-lg-1"><label class="form-label" for="payment-order">Ordem</label><select id="payment-order" class="form-select" [(ngModel)]="ordering" (change)="apply()"><option value="due_date">Vencimento</option><option value="-due_date">Mais distantes</option><option value="-amount">Maior valor</option></select></div>
    </div></div>
    @if (error()) { <div class="alert alert-danger m-3">{{ error() }}</div> }
    <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Descrição</th><th>Processo</th><th>Fornecedor</th><th>Setor</th><th>Valor</th><th>Vencimento</th><th>Estado</th><th></th></tr></thead><tbody>@for (item of payments(); track item.id) { <tr><td>{{ item.description }}</td><td>{{ item.process_number }}</td><td>{{ item.supplier_name }}</td><td>{{ item.sector_name }}</td><td class="text-nowrap">{{ item.amount | currency:'BRL':'symbol':'1.2-2':'pt-BR' }}</td><td class="text-nowrap" [class.text-danger]="item.is_overdue">{{ item.due_date | date:'shortDate' }} @if (item.is_overdue) { <small>(vencido)</small> }</td><td><span class="badge" [class]="statusClass(item)">{{ labels[item.status] }}</span></td><td class="text-end"><a class="btn btn-sm btn-light" [routerLink]="['/pagamentos', item.id]">Visualizar</a></td></tr>} @empty { @if (!loading()) { <tr><td colspan="8" class="text-center text-body-secondary py-5">Nenhum pagamento encontrado.</td></tr> } }</tbody></table></div>
    <div class="card-footer bg-white d-flex justify-content-between"><small>{{ loading() ? 'Carregando…' : 'Exibindo ' + payments().length + ' de ' + count() }}</small><div><button class="btn btn-sm btn-light me-1" [disabled]="page() === 1" (click)="go(page()-1)">Anterior</button><button class="btn btn-sm btn-light" [disabled]="!next()" (click)="go(page()+1)">Próxima</button></div></div></section>
  `
})
export class PaymentList {
  readonly auth = inject(AuthService); private readonly api = inject(PaymentService); private readonly sectorApi = inject(SectorService); private readonly route = inject(ActivatedRoute);
  readonly payments = signal<Payment[]>([]); readonly suppliers = signal<Supplier[]>([]); readonly sectors = signal<FlatSectorNode[]>([]); readonly summary = signal<PaymentDeadlineSummary|null>(null); readonly loading = signal(true); readonly error = signal(''); readonly count = signal(0); readonly next = signal<string|null>(null); readonly page = signal(1);
  readonly labels = PAYMENT_STATUS_LABELS; readonly statuses = Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[];
  search=''; process=this.route.snapshot.queryParamMap.get('process') || ''; status=''; deadline=''; sector=''; supplier=''; dueFrom=''; dueTo=''; ordering='due_date';
  constructor() { this.api.suppliers().subscribe({ next: page => this.suppliers.set(page.results) }); this.sectorApi.tree('true').subscribe({ next: tree => this.sectors.set(this.flatten(tree)) }); this.api.deadlineSummary().subscribe({next: summary => this.summary.set(summary)}); this.load(); }
  apply(){ this.page.set(1); this.load(); } go(page:number){ if(page<1||(page>this.page()&&!this.next()))return; this.page.set(page); this.load(); }
  selectDeadline(deadline:string){this.deadline=deadline;this.apply();}
  statusClass(item:Payment){ return `text-bg-${item.status==='PAID'?'success':item.status==='CANCELLED'?'secondary':item.is_overdue?'danger':item.status==='SCHEDULED'?'info':'warning'}`; }
  private load(){ this.loading.set(true); this.error.set(''); this.api.list({search:this.search,process:this.process,status:this.status,deadline:this.deadline,sector:this.sector,supplier:this.supplier,dueFrom:this.dueFrom,dueTo:this.dueTo,ordering:this.ordering,page:this.page()}).subscribe({next:r=>{this.payments.set(r.results);this.count.set(r.count);this.next.set(r.next);this.loading.set(false);},error:e=>{this.error.set(e?.status===403?'Você não possui acesso aos dados financeiros.':'Não foi possível carregar os pagamentos.');this.loading.set(false);}}); }
  private flatten(nodes:SectorTreeNode[],level=0):FlatSectorNode[]{return nodes.flatMap(node=>[{...node,level},...this.flatten(node.children,level+1)]);}
}
