import { Button, Card, Space, Table, Tag } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { ILowStockSpool } from "../model";

dayjs.extend(relativeTime);

interface LowStockTableProps {
  items: ILowStockSpool[];
  loading: boolean;
  thresholdG: number;
  onOpenSpool: (spoolId: number) => void;
  onEditSpool: (spoolId: number) => void;
}

export function LowStockTable({ items, loading, thresholdG, onOpenSpool, onEditSpool }: LowStockTableProps) {
  return (
    <Card title={`Low stock spools (${thresholdG} g threshold)`}>
      <Table<ILowStockSpool>
        loading={loading}
        dataSource={items}
        rowKey="spool_id"
        pagination={false}
        scroll={{ x: "max-content" }}
        columns={[
          {
            title: "Spool",
            key: "spool",
            render: (_, record) => `${record.vendor_name ?? "Unknown vendor"} - ${record.filament_name ?? `#${record.filament_id}`}`,
          },
          {
            title: "Material",
            dataIndex: "material",
            key: "material",
            render: (value: string | undefined) => value ?? "Unknown",
          },
          {
            title: "Location",
            dataIndex: "location",
            key: "location",
            render: (value: string | undefined) => value ?? "Unassigned",
          },
          {
            title: "Remaining",
            dataIndex: "remaining_weight_g",
            key: "remaining_weight_g",
            align: "right",
            render: (value: number | undefined) => (value !== undefined ? `${value.toFixed(0)} g` : "Unknown"),
          },
          {
            title: "Last used",
            dataIndex: "last_used",
            key: "last_used",
            render: (value: string | undefined) => (value ? dayjs(value).fromNow() : <Tag>Unused</Tag>),
          },
          {
            title: "Action",
            key: "action",
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => onOpenSpool(record.spool_id)}>
                  View
                </Button>
                <Button size="small" onClick={() => onEditSpool(record.spool_id)}>
                  Edit
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}