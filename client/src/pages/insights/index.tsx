import { Col, Empty, InputNumber, Row, Select, Space, Switch, Typography } from "antd";
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
import { InsightsFilters } from "./model";

function buildFilters(searchParams: URLSearchParams): InsightsFilters {
  const daysValue = Number(searchParams.get("days") ?? "30");
  return {
    threshold_g: 200,
    days: Number.isFinite(daysValue) ? daysValue : 30,
    allow_archived: searchParams.get("allow_archived") === "true",
    location: searchParams.get("location") ?? undefined,
    material: searchParams.get("material") ?? undefined,
  };
}

function parseThresholdSetting(value: string | undefined): number {
  if (!value) {
    return 200;
  }

  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "number" && Number.isFinite(parsed) ? parsed : 200;
  } catch {
    return 200;
  }
}

export const Insights = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const thresholdSetting = useGetSetting("insights_low_stock_threshold_g");
  const filters = useMemo(() => {
    const next = buildFilters(searchParams);
    return {
      ...next,
      threshold_g: parseThresholdSetting(thresholdSetting.data?.value),
    };
  }, [searchParams, thresholdSetting.data?.value]);
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

  return (
    <Space direction="vertical" size="large" style={{ display: "flex" }}>
      <div>
        <Typography.Title level={2} style={{ marginBottom: 0 }}>
          Insights
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Inventory overview, low stock monitoring, and location/material summaries. The low stock threshold is managed in Settings.
        </Typography.Paragraph>
      </div>

      <Space wrap>
        <div>
          <Typography.Text strong>Recent window (days)</Typography.Text>
          <br />
          <InputNumber min={1} max={365} value={filters.days} onChange={(value) => updateParam("days", value ?? 30)} />
        </div>
        <div>
          <Typography.Text strong>Material</Typography.Text>
          <br />
          <Select
            allowClear
            style={{ minWidth: 180 }}
            value={filters.material}
            options={(materialOptions.data ?? []).map((material) => ({ label: material, value: material }))}
            onChange={(value) => updateParam("material", value)}
          />
        </div>
        <div>
          <Typography.Text strong>Location</Typography.Text>
          <br />
          <Select
            allowClear
            style={{ minWidth: 180 }}
            value={filters.location}
            options={(locationOptions.data ?? []).map((location) => ({ label: location, value: location }))}
            onChange={(value) => updateParam("location", value)}
          />
        </div>
        <div>
          <Typography.Text strong>Include archived</Typography.Text>
          <br />
          <Switch checked={filters.allow_archived} onChange={(checked) => updateParam("allow_archived", checked || undefined)} />
        </div>
      </Space>

      <OverviewCards overview={overview.data} loading={overview.isLoading} onOpenLowStock={openLowStockList} />

      <LowStockTable
        items={lowStock.data?.items ?? []}
        loading={lowStock.isLoading}
        thresholdG={filters.threshold_g}
        onOpenSpool={(spoolId) => navigate(`/spool/show/${spoolId}`)}
        onEditSpool={(spoolId) => navigate(`/spool/edit/${spoolId}`)}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <MaterialBreakdown items={byMaterial.data?.items ?? []} loading={byMaterial.isLoading} onOpenMaterial={openMaterial} />
        </Col>
        <Col xs={24} xl={12}>
          <LocationBreakdown items={byLocation.data?.items ?? []} loading={byLocation.isLoading} onOpenLocation={openLocation} />
        </Col>
      </Row>

      <ColorBreakdown items={byColor.data?.items ?? []} loading={byColor.isLoading} />

      <RecentActivity
        items={recentActivity.data?.items ?? []}
        loading={recentActivity.isLoading}
        days={filters.days}
        onOpenSpool={(spoolId) => navigate(`/spool/show/${spoolId}`)}
      />

      {!overview.isLoading && (overview.data?.spool_count ?? 0) === 0 && <Empty description="No spools match the current filters." />}
    </Space>
  );
};

export default Insights;