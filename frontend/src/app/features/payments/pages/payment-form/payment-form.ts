import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { ProcessItem } from '../../../processes/models/process.models';
import { ProcessService } from '../../../processes/services/process.service';
import { Supplier } from '../../models/payment.models';
import { PaymentService } from '../../services/payment.service';

@Component({
  selector:'app-payment-form', imports:[ReactiveFormsModule,RouterLink,PageHeader],
  template:`<app-page-header [title]="id?'Editar pagamento':'Novo pagamento'" description="Cadastre a obrigação financeira sem confirmar o pagamento."><a class="btn btn-outline-secondary" routerLink="/pagamentos">Voltar</a></app-page-header>
  @if(error()){<div class="alert alert-danger">{{error()}}</div>}<form class="card border-0 shadow-sm" [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="card-body p-4"><div class="row g-3">
  <div class="col-md-6"><label class="form-label" for="payment-process">Processo</label><select id="payment-process" class="form-select" formControlName="process" (change)="syncSector()"><option value="">Selecione</option>@for(item of processes();track item.id){<option [value]="item.id">{{item.number}} — {{item.title}}</option>}</select></div>
  <div class="col-md-6"><label class="form-label" for="payment-supplier-form">Fornecedor</label><select id="payment-supplier-form" class="form-select" formControlName="supplier"><option value="">Selecione</option>@for(item of suppliers();track item.id){<option [value]="item.id">{{item.name}} ({{item.tax_id_masked}})</option>}</select></div>
  <div class="col-md-8"><label class="form-label" for="payment-description">Descrição</label><input id="payment-description" class="form-control" maxlength="250" formControlName="description"></div>
  <div class="col-md-2"><label class="form-label" for="payment-amount">Valor</label><input id="payment-amount" class="form-control" inputmode="decimal" placeholder="0,00" formControlName="amount"></div>
  <div class="col-md-2"><label class="form-label" for="payment-due">Vencimento</label><input id="payment-due" class="form-control" type="date" formControlName="due_date"></div>
  </div><input type="hidden" formControlName="sector"></div><div class="card-footer bg-white d-flex justify-content-end gap-2 p-3"><a class="btn btn-light" routerLink="/pagamentos">Cancelar</a><button class="btn btn-primary" [disabled]="saving()">{{saving()?'Salvando…':'Salvar pagamento'}}</button></div></form>`
})
export class PaymentForm{
  private readonly api=inject(PaymentService);private readonly processApi=inject(ProcessService);private readonly route=inject(ActivatedRoute);private readonly router=inject(Router);readonly id=Number(this.route.snapshot.paramMap.get('id'))||0;
  readonly processes=signal<ProcessItem[]>([]);readonly suppliers=signal<Supplier[]>([]);readonly workflowEligible=signal(false);readonly saving=signal(false);readonly error=signal('');
  readonly form=new FormGroup({process:new FormControl('',{nonNullable:true,validators:[Validators.required]}),sector:new FormControl('',{nonNullable:true,validators:[Validators.required]}),supplier:new FormControl('',{nonNullable:true,validators:[Validators.required]}),description:new FormControl('',{nonNullable:true,validators:[Validators.required]}),amount:new FormControl('',{nonNullable:true,validators:[Validators.required,Validators.pattern(/^\d{1,12}([.,]\d{1,2})?$/)]}),due_date:new FormControl('',{nonNullable:true,validators:[Validators.required]})});
  constructor(){this.processApi.list().subscribe({next:r=>{this.processes.set(r.results);if(this.id)this.load();}});this.api.suppliers().subscribe({next:r=>this.suppliers.set(r.results)});}
  syncSector(){const process=this.processes().find(item=>item.id===Number(this.form.controls.process.value));this.workflowEligible.set(Boolean(process&&!process.workflow_version));this.form.controls.sector.setValue(String(process?.current_sector||process?.origin_sector||''));if(process?.workflow_version)this.processApi.availableActions(process.id).subscribe({next:actions=>{const eligible=actions.some(action=>action.integration_action==='create_payment');this.workflowEligible.set(eligible);if(!eligible)this.error.set('O processo não está na etapa de processamento financeiro.');}});}
  submit(){this.form.markAllAsTouched();if(this.form.invalid||this.saving())return;if(!this.id&&!this.workflowEligible()){this.error.set('O processo não está na etapa de processamento financeiro.');return;}const value=this.form.getRawValue();const payload={process:Number(value.process),sector:Number(value.sector),supplier:Number(value.supplier),description:value.description.trim(),amount:value.amount.replace(',','.'),due_date:value.due_date};this.saving.set(true);this.error.set('');const request=this.id?this.api.update(this.id,payload):this.api.create(payload);request.pipe(finalize(()=>this.saving.set(false))).subscribe({next:item=>this.router.navigate(['/pagamentos',item.id]),error:r=>this.error.set(this.firstError(r?.error)||'Não foi possível salvar o pagamento.')});}
  private load(){this.api.get(this.id).subscribe({next:item=>{this.form.patchValue({process:String(item.process),sector:String(item.sector),supplier:String(item.supplier),description:item.description,amount:item.amount,due_date:item.due_date});if(!this.processes().some(process=>process.id===item.process))this.processApi.get(item.process).subscribe({next:process=>this.processes.update(items=>[process,...items])});},error:()=>this.error.set('Pagamento não encontrado ou fora do seu escopo.')});}
  private firstError(error:unknown){if(!error||typeof error!=='object')return'';const value=Object.values(error as Record<string,unknown>)[0];return Array.isArray(value)?String(value[0]):String(value||'');}
}
