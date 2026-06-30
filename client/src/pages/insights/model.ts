export interface InsightsFilters {
  threshold_g: number;
  days: number;
  allow_archived: boolean;
  location?: string;
  material?: string;
}

export interface IInsightsOverview {
  spool_count: number;
  active_spool_count: number;
  archived_spool_count: number;
  low_stock_count: number;
  out_of_stock_count: number;
  material_count: number;
  location_count: number;
  vendor_count: number;
  remaining_weight_total_g: number;
  used_weight_total_g: number;
  updated_at: string;
}

export interface ILowStockSpool {
  spool_id: number;
  filament_id: number;
  vendor_name?: string;
  filament_name?: string;
  material?: string;
  location?: string;
  remaining_weight_g?: number;
  used_weight_g: number;
  color_hex?: string;
  multi_color_hexes?: string;
  last_used?: string;
  archived: boolean;
}

export interface ILowStockResponse {
  threshold_g: number;
  total: number;
  items: ILowStockSpool[];
}

export interface IMaterialSummary {
  material: string;
  spool_count: number;
  low_stock_count: number;
  remaining_weight_total_g: number;
  used_weight_total_g: number;
  percentage_of_inventory: number;
}

export interface IMaterialSummaryResponse {
  items: IMaterialSummary[];
}

export interface ILocationSummary {
  location: string;
  spool_count: number;
  low_stock_count: number;
  remaining_weight_total_g: number;
  materials: string[];
}

export interface ILocationSummaryResponse {
  items: ILocationSummary[];
}

export interface IColorSummary {
  color_key: string;
  display_name: string;
  display_hex?: string;
  spool_count: number;
  remaining_weight_total_g: number;
}

export interface IColorSummaryResponse {
  items: IColorSummary[];
}

export interface IRecentActivityItem {
  spool_id: number;
  filament_name?: string;
  vendor_name?: string;
  material?: string;
  location?: string;
  last_used: string;
  remaining_weight_g?: number;
  used_weight_g: number;
}

export interface IRecentActivityResponse {
  days: number;
  items: IRecentActivityItem[];
}