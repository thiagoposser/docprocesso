import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { PaymentGroupReport, PaymentReportSummary, ProcessReportSummary, ReportFilters, SectorTimeReport } from '../models/report.models';

@Injectable({providedIn:'root'})
export class ReportService {
  private readonly http=inject(HttpClient);
  processSummary(filters:ReportFilters){return this.http.get<ProcessReportSummary>('/api/reports/processes/summary/',{params:this.params(filters,'process_status')});}
  timeBySector(filters:ReportFilters){return this.http.get<SectorTimeReport[]>('/api/reports/processes/time-by-sector/',{params:this.params(filters,'process_status')});}
  paymentSummary(filters:ReportFilters){return this.http.get<PaymentReportSummary>('/api/reports/payments/summary/',{params:this.params(filters,'payment_status')});}
  paymentsBySector(filters:ReportFilters){return this.http.get<PaymentGroupReport[]>('/api/reports/payments/by-sector/',{params:this.params(filters,'payment_status')});}
  paymentsBySupplier(filters:ReportFilters){return this.http.get<PaymentGroupReport[]>('/api/reports/payments/by-supplier/',{params:this.params(filters,'payment_status')});}
  private params(filters:ReportFilters,statusField:'process_status'|'payment_status') { let params=new HttpParams(); Object.entries(filters).forEach(([key,value])=>{if(value&&key!=='process_status'&&key!=='payment_status')params=params.set(key,value)}); const status=filters[statusField]; if(status)params=params.set('status',status); return params; }
}
