import { Button, Card, Space, Table, Tag } from "antd";
import { useTranslate } from "@refinedev/core";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { ILowStockSpool, InsightsThresholdMode } from "../model";

dayjs.extend(relativeTime);

interface LowStockTableProps {
  items: ILowStockSpool[];
  loading: boolean;
  thresholdLabel: string;
  thresholdMode: InsightsThresholdMode;
  onOpenSpool: (spoolId: number) => void;
  onEditSpool: (spoolId: number) => void;
}

function formatSpoolLabel(record: ILowStockSpool, unknownVendor: string): string {
  const vendorName = record.vendor_name ?? unknownVendor;
  const filamentName = record.filament_name ?? "#" + String(record.filament_id);
  return `${vendorName} - ${filamentName}`;
}

export function LowStockTable({ items, loading, thresholdLabel, thresholdMode, onOpenSpool, onEditSpool }: Readonly<LowStockTableProps>) {
  const t = useTranslate();
  const columns = [
    {
      title: t("spool.spool"),
      key: "spool",
      render: (_: unknown, record: ILowStockSpool) => formatSpoolLabel(record, t("insights.values.unknown_vendor")),
    },
    {
      title: t("spool.fields.material"),
      dataIndex: "material",
      key: "material",
      render: (value: string | undefined) => value ?? t("unknown"),
    },
    {
      title: t("spool.fields.location"),
      dataIndex: "location",
      key: "location",
      render: (value: string | undefined) => {
        if (value === "Unassigned" || value === undefined) {
          return t("insights.values.unassigned");
        }
        return value;
      },
    },
    {
      title: t("spool.fields.remaining_weight"),
      dataIndex: "remaining_weight_g",
      key: "remaining_weight_g",
      align: "right" as const,
      render: (value: number | undefined) => {
        if (value === undefined) {
          return t("unknown");
        }

        return `${value.toFixed(0)} g`;
      },
    },
    ...(thresholdMode === "percent"
      ? [
          {
            title: t("insights.columns.remaining_percent"),
            dataIndex: "remaining_percentage",
            key: "remaining_percentage",
            align: "right" as const,
            render: (value: number | undefined) => {
              if (value === undefined) {
                return t("unknown");
              }

              return `${value.toFixed(0)}%`;
            },
          },
        ]
      : []),
    {
      title: t("spool.fields.last_used"),
      dataIndex: "last_used",
      key: "last_used",
      render: (value: string | undefined) => (value ? dayjs(value).fromNow() : <Tag>{t("insights.values.unused")}</Tag>),
    },
    {
      title: t("table.actions"),
      key: "action",
      render: (_: unknown, record: ILowStockSpool) => (
        <Space>
          <Button size="small" onClick={() => onOpenSpool(record.spool_id)}>
            {t("buttons.show")}
          </Button>
          <Button size="small" onClick={() => onEditSpool(record.spool_id)}>
            {t("buttons.edit")}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card title={t("insights.low_stock.title", { threshold: thresholdLabel })}>
      <Table<ILowStockSpool>
        loading={loading}
        dataSource={items}
        rowKey="spool_id"
        pagination={false}
        scroll={{ x: "max-content" }}
        columns={columns}
      />
    </Card>
  );
}