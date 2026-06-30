import { Button, Card, Col, Empty, InputNumber, Row, Select, Space, Switch, Tag, Typography } from "antd";
import { useTranslate } from "@refinedev/core";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useSpoolmanLocations, useSpoolmanMaterials } from "../../components/otherModels";
import { useGetSetting } from "../../utils/querySettings";
import {
  buildSpoolDrilldownPath,
  useInsightsByColor,
  useInsightsByLocation,
  useInsightsByMaterial,
  useInsightsLowStock,
  useInsightsOverview,
  useInsightsRecentActivity,
} from "./hooks";
import { ColorBreakdown } from "./components/colorBreakdown";
import { LocationBreakdown } from "./components/locationBreakdown";
import { LowStockTable } from "./components/lowStockTable";
import { MaterialBreakdown } from "./components/materialBreakdown";
import { OverviewCards } from "./components/overviewCards";
import { RecentActivity } from "./components/recentActivity";
import { InsightsFilters, InsightsThresholdMode } from "./model";

function buildFilters(searchParams: URLSearchParams): InsightsFilters {
  const daysValue = Number(searchParams.get("days") ?? "30");
  return {
    days: Number.isFinite(daysValue) ? daysValue : 30,
    allow_archived: searchParams.get("allow_archived") === "true",
    location: searchParams.get("location") ?? undefined,
    material: searchParams.get("material") ?? undefined,
  };
}

function parseNumberSetting(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "number" && Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function parseThresholdModeSetting(value: string | undefined): InsightsThresholdMode {
  if (!value) {
    return "percent";
  }

  try {
    const parsed = JSON.parse(value);
    return parsed === "weight" || parsed === "percent" ? parsed : "percent";
  } catch {
    return "percent";
  }
}

function buildThresholdLabel(mode: InsightsThresholdMode, thresholdG: number, thresholdPercent: number): string {
  if (mode === "percent") {
    return `${thresholdPercent.toFixed(0)}%`;
  }
  return `${thresholdG.toFixed(0)} g`;
}

function getLocationLabel(location: string, unassignedLabel: string): string {
  return location === "Unassigned" ? unassignedLabel : location;
}

function buildColorDrilldownFilters(colorKey: string): Array<{ field: string; operator: string; value: string[] }> {
  if (colorKey === "UNKNOWN") {
    return [
      { field: "filament.color_hex", operator: "eq", value: ["<empty>"] },
      { field: "filament.multi_color_hexes", operator: "eq", value: ["<empty>"] },
    ];
  }

  if (colorKey.startsWith("MULTI:")) {
    return [{ field: "filament.multi_color_hexes", operator: "eq", value: [`"${colorKey.slice(6)}"`] }];
  }

  return [{ field: "filament.color_hex", operator: "eq", value: [`"${colorKey.replace("#", "")}"`] }];
}

function hasActiveFilters(filters: InsightsFilters): boolean {
  return filters.allow_archived || filters.location !== undefined || filters.material !== undefined || filters.days !== 30;
}

export const Insights = () => {
  const navigate = useNavigate();
  const t = useTranslate();
  const [searchParams, setSearchParams] = useSearchParams();
  const thresholdModeSetting = useGetSetting("insights_low_stock_threshold_mode");
  const thresholdWeightSetting = useGetSetting("insights_low_stock_threshold_g");
  const thresholdPercentSetting = useGetSetting("insights_low_stock_threshold_percent");
  const filters = useMemo(() => {
    const next = buildFilters(searchParams);
    const thresholdMode = parseThresholdModeSetting(thresholdModeSetting.data?.value);
    const thresholdG = parseNumberSetting(thresholdWeightSetting.data?.value, 200);
    const thresholdPercent = parseNumberSetting(thresholdPercentSetting.data?.value, 20);
    return {
      ...next,
      threshold_mode: thresholdMode,
      threshold_g: thresholdMode === "weight" ? thresholdG : undefined,
      threshold_percent: thresholdMode === "percent" ? thresholdPercent : undefined,
    };
  }, [searchParams, thresholdModeSetting.data?.value, thresholdPercentSetting.data?.value, thresholdWeightSetting.data?.value]);
  const thresholdLabel = useMemo(
    () => buildThresholdLabel(filters.threshold_mode ?? "percent", filters.threshold_g ?? 200, filters.threshold_percent ?? 20),
    [filters.threshold_g, filters.threshold_mode, filters.threshold_percent],
  );
  const materialOptions = useSpoolmanMaterials(true);
  const locationOptions = useSpoolmanLocations(true);

  const overview = useInsightsOverview(filters);
  const lowStock = useInsightsLowStock(filters);
  const byMaterial = useInsightsByMaterial(filters);
  const byLocation = useInsightsByLocation(filters);
  const byColor = useInsightsByColor(filters);
  const recentActivity = useInsightsRecentActivity(filters);

  const updateParam = (key: string, value?: string | number | boolean) => {
    const next = new URLSearchParams(searchParams);
    if (value === undefined || value === "") {
      next.delete(key);
    } else {
      next.set(key, String(value));
    }
    setSearchParams(next, { replace: true });
  };

  const openMaterial = (material: string) => {
    navigate(
      buildSpoolDrilldownPath({
        filters: [{ field: "filament.material", operator: "eq", value: [material] }],
        showArchived: filters.allow_archived,
      }),
    );
  };

  const openLocation = (location: string) => {
    navigate(
      buildSpoolDrilldownPath({
        filters: [{ field: "location", operator: "eq", value: [location === "Unassigned" ? "<empty>" : location] }],
        showArchived: filters.allow_archived,
      }),
    );
  };

  const openLowStockList = () => {
    navigate(
      buildSpoolDrilldownPath({
        sorters: [{ field: "remaining_weight", order: "asc" }],
        showArchived: filters.allow_archived,
      }),
    );
  };

  const openColor = (colorKey: string) => {
    navigate(
      buildSpoolDrilldownPath({
        filters: buildColorDrilldownFilters(colorKey),
        showArchived: filters.allow_archived,
      }),
    );
  };

  const clearFilters = () => {
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  return (
    <div style={{ maxWidth: 1360, margin: "0 auto", width: "100%" }}>
      <Space direction="vertical" size="middle" style={{ display: "flex" }}>
      <Card>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} xl={9}>
            <Typography.Title level={2} style={{ marginBottom: 0 }}>
              {t("insights.title")}
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              {t("insights.description")}
            </Typography.Paragraph>
            <Space size={[8, 8]} wrap>
              <Tag color="blue">{t("insights.filters.threshold", { threshold: thresholdLabel })}</Tag>
              {hasActiveFilters(filters) && <Tag>{t("buttons.filter")}</Tag>}
            </Space>
          </Col>
          <Col xs={24} xl={15}>
            <Row gutter={[12, 12]}>
              <Col xs={24} sm={12} lg={12} xl={6}>
                <Typography.Text strong>{t("insights.filters.recent_days")}</Typography.Text>
                <InputNumber
                  min={1}
                  max={365}
                  style={{ width: "100%", marginTop: 8 }}
                  value={filters.days}
                  onChange={(value) => updateParam("days", value ?? 30)}
                />
              </Col>
              <Col xs={24} sm={12} lg={12} xl={6}>
                <Typography.Text strong>{t("spool.fields.material")}</Typography.Text>
                <Select
                  allowClear
                  style={{ width: "100%", marginTop: 8 }}
                  value={filters.material}
                  options={(materialOptions.data ?? []).map((material) => ({ label: material, value: material }))}
                  onChange={(value) => updateParam("material", value)}
                />
              </Col>
              <Col xs={24} sm={12} lg={12} xl={6}>
                <Typography.Text strong>{t("spool.fields.location")}</Typography.Text>
                <Select
                  allowClear
                  style={{ width: "100%", marginTop: 8 }}
                  value={filters.location}
                  options={(locationOptions.data ?? []).map((location) => ({
                    label: getLocationLabel(location, t("insights.values.unassigned")),
                    value: location,
                  }))}
                  onChange={(value) => updateParam("location", value)}
                />
              </Col>
              <Col xs={24} sm={12} lg={12} xl={6}>
                <Typography.Text strong>{t("insights.filters.include_archived")}</Typography.Text>
                <div style={{ marginTop: 12 }}>
                  <Switch checked={filters.allow_archived} onChange={(checked) => updateParam("allow_archived", checked || undefined)} />
                </div>
              </Col>
              <Col xs={24}>
                <Space wrap>
                  <Button onClick={clearFilters} disabled={!hasActiveFilters(filters)}>
                    {t("buttons.clearFilters")}
                  </Button>
                </Space>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      <OverviewCards overview={overview.data} loading={overview.isLoading} onOpenLowStock={openLowStockList} />

      <LowStockTable
        items={lowStock.data?.items ?? []}
        loading={lowStock.isLoading}
        thresholdLabel={thresholdLabel}
        thresholdMode={filters.threshold_mode ?? "percent"}
        onOpenSpool={(spoolId) => navigate(`/spool/show/${spoolId}`)}
        onEditSpool={(spoolId) => navigate(`/spool/edit/${spoolId}`)}
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12}>
          <MaterialBreakdown items={byMaterial.data?.items ?? []} loading={byMaterial.isLoading} onOpenMaterial={openMaterial} />
        </Col>
        <Col xs={24} xl={12}>
          <LocationBreakdown items={byLocation.data?.items ?? []} loading={byLocation.isLoading} onOpenLocation={openLocation} />
        </Col>
      </Row>

      <ColorBreakdown items={byColor.data?.items ?? []} loading={byColor.isLoading} onOpenColor={openColor} />

      <RecentActivity
        items={recentActivity.data?.items ?? []}
        loading={recentActivity.isLoading}
        days={filters.days}
        onOpenSpool={(spoolId) => navigate(`/spool/show/${spoolId}`)}
      />

      {!overview.isLoading && (overview.data?.spool_count ?? 0) === 0 && <Empty description={t("insights.empty")} />}
      </Space>
    </div>
  );
};

export default Insights;