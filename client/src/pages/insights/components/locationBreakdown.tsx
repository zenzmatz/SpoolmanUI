import { Button, Card, Table, Tag } from "antd";
import { ILocationSummary } from "../model";

interface LocationBreakdownProps {
  items: ILocationSummary[];
  loading: boolean;
  onOpenLocation: (location: string) => void;
}

export function LocationBreakdown({ items, loading, onOpenLocation }: LocationBreakdownProps) {
  return (
    <Card title="By location">
      <Table<ILocationSummary>
        loading={loading}
        dataSource={items}
        rowKey="location"
        pagination={false}
        size="small"
        columns={[
          { title: "Location", dataIndex: "location", key: "location" },
          { title: "Spools", dataIndex: "spool_count", key: "spool_count", align: "right" },
          {
            title: "Remaining",
            dataIndex: "remaining_weight_total_g",
            key: "remaining_weight_total_g",
            align: "right",
            render: (value: number) => `${value.toFixed(0)} g`,
          },
          {
            title: "Materials",
            dataIndex: "materials",
            key: "materials",
            render: (values: string[]) => values.map((value) => <Tag key={value}>{value}</Tag>),
          },
          {
            title: "Action",
            key: "action",
            render: (_, record) => (
              <Button size="small" onClick={() => onOpenLocation(record.location)}>
                View spools
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
}