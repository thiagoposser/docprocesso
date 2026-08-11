export interface ReportFilters { date_from?:string; date_to?:string; sector?:string; type?:string; responsible?:string; process_status?:string; payment_status?:string; supplier?:string; min_amount?:string; max_amount?:string; purpose?:string; }
export interface CountGroup { status?:string; name?:string; count:number; total?:string; }
export interface ProcessReportSummary { total:number; by_status:CountGroup[]; by_type:CountGroup[]; }
export interface SectorTimeReport { sector:number; sector_name:string; average_hours:number; movements:number; }
export interface PaymentReportSummary { count:number; total:string; average:string; by_status:CountGroup[]; }
export interface PaymentGroupReport { sector?:number; supplier?:number; name:string; count:number; total:string; }
