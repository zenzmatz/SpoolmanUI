import { Card, Col, Row, Space, Typography } from "antd";
import { useTranslate } from "@refinedev/core";
import SpoolIcon from "../../../components/spoolIcon";
import { IColorSummary } from "../model";

interface ColorBreakdownProps {
  items: IColorSummary[];
  loading: boolean;
  onOpenColor: (colorKey: string) => void;
}

function getDisplayName(item: IColorSummary, unknownLabel: string, multiColorLabel: string): string {
  if (item.color_key === "UNKNOWN") {
    return unknownLabel;
  }

  if (item.color_key.startsWith("MULTI:")) {
    return multiColorLabel;
  }

  return item.display_name;
}

export function ColorBreakdown({ items, loading, onOpenColor }: Readonly<ColorBreakdownProps>) {
  const t = useTranslate();

  return (
    <Card title={t("insights.sections.by_color")} loading={loading}>
      <Row gutter={[12, 12]}>
        {items.map((item) => (
          <Col xs={24} sm={12} xl={8} key={item.color_key}>
            <Card size="small" hoverable onClick={() => onOpenColor(item.color_key)} style={{ height: "100%" }}>
              <Space align="start">
                {item.display_hex ? <SpoolIcon color={item.display_hex} /> : <div style={{ width: 24 }} />}
                <div>
                  <Typography.Text strong>{getDisplayName(item, t("unknown"), t("insights.values.multi_color"))}</Typography.Text>
                  <br />
                  <Typography.Text type="secondary">{t("insights.values.spools_count", { count: item.spool_count })}</Typography.Text>
                  <br />
                  <Typography.Text type="secondary">
                    {t("insights.values.remaining_grams", { count: item.remaining_weight_total_g.toFixed(0) })}
                  </Typography.Text>
                </div>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
}