import { Button, Card, Table } from "antd";
import { IMaterialSummary } from "../model";

interface MaterialBreakdownProps {
  items: IMaterialSummary[];
  loading: boolean;
  onOpenMaterial: (material: string) => void;
}

export function MaterialBreakdown({ items, loading, onOpenMaterial }: MaterialBreakdownProps) {
  return (
    <Card title="By material">
      <Table<IMaterialSummary>
        loading={loading}
        dataSource={items}
        rowKey="material"
        pagination={false}
        size="small"
        columns={[
          { title: "Material", dataIndex: "material", key: "material" },
          { title: "Spools", dataIndex: "spool_count", key: "spool_count", align: "right" },
          {
            title: "Remaining",
            dataIndex: "remaining_weight_total_g",
            key: "remaining_weight_total_g",
            align: "right",
            render: (value: number) => `${value.toFixed(0)} g`,
          },
          { title: "Low stock", dataIndex: "low_stock_count", key: "low_stock_count", align: "right" },
          {
            title: "Action",
            key: "action",
            render: (_, record) => (
              <Button size="small" onClick={() => onOpenMaterial(record.material)}>
                View spools
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
}