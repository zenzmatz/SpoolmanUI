import { useQuery } from "@tanstack/react-query";
import { getAPIURL } from "../../utils/url";
import {
  IInsightsOverview,
  ILocationSummaryResponse,
  ILowStockResponse,
  IMaterialSummaryResponse,
  InsightsFilters,
} from "./model";

function buildQueryString(filters: InsightsFilters): string {
  const params = new URLSearchParams();
  params.set("threshold_g", String(filters.threshold_g));
  if (filters.allow_archived) {
    params.set("allow_archived", "true");
  }
  if (filters.location) {
    params.set("location", filters.location);
  }
  if (filters.material) {
    params.set("material", filters.material);
  }
  return params.toString();
}

async function fetchJson<T>(path: string, filters: InsightsFilters): Promise<T> {
  const response = await fetch(`${getAPIURL()}${path}?${buildQueryString(filters)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}`);
  }
  return response.json();
}

export function useInsightsOverview(filters: InsightsFilters) {
  return useQuery<IInsightsOverview>({
    queryKey: ["insights", "overview", filters],
    queryFn: async () => fetchJson<IInsightsOverview>("/insights/overview", filters),
  });
}

export function useInsightsLowStock(filters: InsightsFilters) {
  return useQuery<ILowStockResponse>({
    queryKey: ["insights", "low-stock", filters],
    queryFn: async () => fetchJson<ILowStockResponse>("/insights/low-stock", filters),
  });
}

export function useInsightsByMaterial(filters: InsightsFilters) {
  return useQuery<IMaterialSummaryResponse>({
    queryKey: ["insights", "by-material", filters],
    queryFn: async () => fetchJson<IMaterialSummaryResponse>("/insights/by-material", filters),
  });
}

export function useInsightsByLocation(filters: InsightsFilters) {
  return useQuery<ILocationSummaryResponse>({
    queryKey: ["insights", "by-location", filters],
    queryFn: async () => fetchJson<ILocationSummaryResponse>("/insights/by-location", filters),
  });
}

interface DrilldownOptions {
  filters?: Array<{ field: string; operator: string; value: string[] }>;
  sorters?: Array<{ field: string; order: "asc" | "desc" }>;
  showArchived?: boolean;
}

export function buildSpoolDrilldownPath(options: DrilldownOptions = {}): string {
  const params = new URLSearchParams();
  if (options.filters && options.filters.length > 0) {
    params.set("filters", JSON.stringify(options.filters));
  }
  if (options.sorters && options.sorters.length > 0) {
    params.set("sorters", JSON.stringify(options.sorters));
  }
  params.set("pagination", JSON.stringify({ currentPage: 1, pageSize: 20 }));
  if (options.showArchived !== undefined) {
    params.set("showArchived", options.showArchived ? "true" : "false");
  }
  return `/spool#${params.toString()}`;
}