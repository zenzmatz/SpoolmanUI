import { Card, Col, Row, Space, Typography } from "antd";
import SpoolIcon from "../../../components/spoolIcon";
import { IColorSummary } from "../model";

interface ColorBreakdownProps {
  items: IColorSummary[];
  loading: boolean;
}

export function ColorBreakdown({ items, loading }: Readonly<ColorBreakdownProps>) {
  return (
    <Card title="By color" loading={loading}>
      <Row gutter={[12, 12]}>
        {items.map((item) => (
          <Col xs={24} md={12} xl={8} key={item.color_key}>
            <Card size="small">
              <Space align="start">
                {item.display_hex ? <SpoolIcon color={item.display_hex} /> : <div style={{ width: 24 }} />}
                <div>
                  <Typography.Text strong>{item.display_name}</Typography.Text>
                  <br />
                  <Typography.Text type="secondary">{item.spool_count} spools</Typography.Text>
                  <br />
                  <Typography.Text type="secondary">{item.remaining_weight_total_g.toFixed(0)} g remaining</Typography.Text>
                </div>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
}