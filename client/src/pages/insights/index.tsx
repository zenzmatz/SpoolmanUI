import { Col, Empty, InputNumber, Row, Select, Space, Switch, Typography } from "antd";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useSpoolmanLocations, useSpoolmanMaterials } from "../../components/otherModels";
import { buildSpoolDrilldownPath, useInsightsByLocation, useInsightsByMaterial, useInsightsLowStock, useInsightsOverview } from "./hooks";
import { LocationBreakdown } from "./components/locationBreakdown";
import { LowStockTable } from "./components/lowStockTable";
import { MaterialBreakdown } from "./components/materialBreakdown";
import { OverviewCards } from "./components/overviewCards";
import { InsightsFilters } from "./model";

function buildFilters(searchParams: URLSearchParams): InsightsFilters {
  const thresholdValue = Number(searchParams.get("threshold_g") ?? "200");
  return {
    threshold_g: Number.isFinite(thresholdValue) ? thresholdValue : 200,
    allow_archived: searchParams.get("allow_archived") === "true",
    location: searchParams.get("location") ?? undefined,
    material: searchParams.get("material") ?? undefined,
  };
}

export const Insights = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => buildFilters(searchParams), [searchParams]);
  const materialOptions = useSpoolmanMaterials(true);
  const locationOptions = useSpoolmanLocations(true);

  const overview = useInsightsOverview(filters);
  const lowStock = useInsightsLowStock(filters);
  const byMaterial = useInsightsByMaterial(filters);
  const byLocation = useInsightsByLocation(filters);

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
          Inventory overview, low stock monitoring, and location/material summaries.
        </Typography.Paragraph>
      </div>

      <Space wrap>
        <div>
          <Typography.Text strong>Threshold (g)</Typography.Text>
          <br />
          <InputNumber min={0} value={filters.threshold_g} onChange={(value) => updateParam("threshold_g", value ?? 200)} />
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

      {!overview.isLoading && (overview.data?.spool_count ?? 0) === 0 && <Empty description="No spools match the current filters." />}
    </Space>
  );
};

export default Insights;