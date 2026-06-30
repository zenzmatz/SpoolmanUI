import { Button, Card, Space, Table, Tag } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { IRecentActivityItem } from "../model";

dayjs.extend(relativeTime);

interface RecentActivityProps {
  items: IRecentActivityItem[];
  loading: boolean;
  days: number;
  onOpenSpool: (spoolId: number) => void;
}

export function RecentActivity({ items, loading, days, onOpenSpool }: Readonly<RecentActivityProps>) {
  return (
    <Card title={`Recent activity (${days} days)`}>
      <Table<IRecentActivityItem>
        loading={loading}
        dataSource={items}
        rowKey="spool_id"
        pagination={false}
        size="small"
        scroll={{ x: "max-content" }}
        columns={[
          {
            title: "Spool",
            key: "spool",
            render: (_, record) => {
              const vendorName = record.vendor_name ?? "Unknown vendor";
              const filamentName = record.filament_name ?? "#" + String(record.spool_id);
              return `${vendorName} - ${filamentName}`;
            },
          },
          { title: "Material", dataIndex: "material", key: "material" },
          { title: "Location", dataIndex: "location", key: "location" },
          {
            title: "Last used",
            dataIndex: "last_used",
            key: "last_used",
            render: (value: string) => dayjs(value).fromNow(),
          },
          {
            title: "Remaining",
            dataIndex: "remaining_weight_g",
            key: "remaining_weight_g",
            align: "right",
            render: (value: number | undefined) => (value === undefined ? <Tag>Unknown</Tag> : `${value.toFixed(0)} g`),
          },
          {
            title: "Action",
            key: "action",
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => onOpenSpool(record.spool_id)}>
                  View
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}