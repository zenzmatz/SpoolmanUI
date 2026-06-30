import { Alert, Button, Divider, Form, Input, InputNumber, Popconfirm, Space, Table, Typography, message } from "antd";
import { useTranslate } from "@refinedev/core";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { getAPIURL } from "../../utils/url";

interface AuthStatusResponse {
  enabled: boolean;
}

interface TokenItem {
  id: number;
  name: string;
  token_preview: string;
  created: string;
  last_used?: string;
  expires_at?: string;
  revoked_at?: string;
}

interface TokenCreateResponse {
  token: string;
  token_info: TokenItem;
}

interface DeviceCodeCreateResponse {
  code: string;
  name: string;
  expires_at: string;
}

interface CreateTokenValues {
  name: string;
  expires_in_days: number;
}

interface CreateDeviceCodeValues {
  name: string;
  expires_in_minutes: number;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getAPIURL()}${path}`, {
    credentials: "include",
    ...init,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(typeof payload?.message === "string" ? payload.message : `Request failed (${response.status})`);
  }

  return response.json();
}

export function AccessSettings() {
  const t = useTranslate();
  const [form] = Form.useForm<CreateTokenValues>();
  const [deviceForm] = Form.useForm<CreateDeviceCodeValues>();
  const [messageApi, contextHolder] = message.useMessage();
  const [authEnabled, setAuthEnabled] = useState<boolean | null>(null);
  const [tokens, setTokens] = useState<TokenItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [creatingDeviceCode, setCreatingDeviceCode] = useState(false);
  const [latestToken, setLatestToken] = useState<string | null>(null);
  const [latestDeviceCode, setLatestDeviceCode] = useState<DeviceCodeCreateResponse | null>(null);

  const load = async () => {
    setLoading(true);
    setLatestToken(null);
    try {
      const status = await fetchJson<AuthStatusResponse>("/auth/status");
      setAuthEnabled(status.enabled);
      if (!status.enabled) {
        setTokens([]);
        return;
      }

      const nextTokens = await fetchJson<TokenItem[]>("/auth/tokens");
      setTokens(nextTokens.filter((item) => item.revoked_at === undefined || item.revoked_at === null));
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : t("notifications.error", { statusCode: 500 }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    form.setFieldsValue({ expires_in_days: 365 });
    deviceForm.setFieldsValue({ name: "SpoolmanScale", expires_in_minutes: 15 });
    load().catch(() => undefined);
  }, [form, deviceForm]);

  const onFinish = async (values: CreateTokenValues) => {
    setCreating(true);
    try {
      const payload = await fetchJson<TokenCreateResponse>("/auth/tokens", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });
      setLatestToken(payload.token);
      setTokens((current) => [payload.token_info, ...current]);
      form.resetFields(["name"]);
      form.setFieldValue("expires_in_days", values.expires_in_days);
      messageApi.success(t("settings.access.create_success"));
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : t("notifications.error", { statusCode: 500 }));
    } finally {
      setCreating(false);
    }
  };

  const revokeToken = async (tokenId: number) => {
    try {
      await fetchJson(`/auth/tokens/${tokenId}`, { method: "DELETE" });
      setTokens((current) => current.filter((item) => item.id !== tokenId));
      messageApi.success(t("settings.access.revoke_success"));
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : t("notifications.error", { statusCode: 500 }));
    }
  };

  const createDeviceCode = async (values: CreateDeviceCodeValues) => {
    setCreatingDeviceCode(true);
    setLatestDeviceCode(null);
    try {
      const payload = await fetchJson<DeviceCodeCreateResponse>("/auth/device-codes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });
      setLatestDeviceCode(payload);
      messageApi.success(t("settings.access.hardware.create_success"));
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : t("notifications.error", { statusCode: 500 }));
    } finally {
      setCreatingDeviceCode(false);
    }
  };

  return (
    <>
      <Typography.Paragraph type="secondary" style={{ maxWidth: "720px", margin: "0 auto 24px" }}>
        {t("settings.access.description")}
      </Typography.Paragraph>

      {authEnabled === false && (
        <Alert
          type="info"
          showIcon
          message={t("settings.access.auth_disabled")}
          style={{ maxWidth: 720, margin: "0 auto 24px" }}
        />
      )}

      {latestToken && (
        <Alert
          type="success"
          showIcon
          message={t("settings.access.latest_token")}
          description={
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              <Typography.Text>{t("settings.access.latest_token_help")}</Typography.Text>
              <Typography.Text copyable>{latestToken}</Typography.Text>
            </Space>
          }
          style={{ maxWidth: 720, margin: "0 auto 24px" }}
        />
      )}

      {latestDeviceCode && (
        <Alert
          type="success"
          showIcon
          message={t("settings.access.hardware.latest_code")}
          description={
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              <Typography.Text>
                {t("settings.access.hardware.latest_code_help", {
                  expiresAt: dayjs(latestDeviceCode.expires_at).format("YYYY-MM-DD HH:mm"),
                })}
              </Typography.Text>
              <Typography.Text copyable code style={{ fontSize: 22 }}>
                {latestDeviceCode.code}
              </Typography.Text>
            </Space>
          }
          style={{ maxWidth: 720, margin: "0 auto 24px" }}
        />
      )}

      {authEnabled && (
        <>
          <Typography.Title level={3} style={{ maxWidth: 720, margin: "0 auto 16px" }}>
            {t("settings.access.hardware.title")}
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ maxWidth: 720, margin: "0 auto 16px" }}>
            {t("settings.access.hardware.description")}
          </Typography.Paragraph>
          <Form
            form={deviceForm}
            layout="vertical"
            onFinish={createDeviceCode}
            style={{ maxWidth: 720, margin: "0 auto 24px" }}
            initialValues={{ name: "SpoolmanScale", expires_in_minutes: 15 }}
          >
            <Form.Item
              name="name"
              label={t("settings.access.hardware.device_name.label")}
              tooltip={t("settings.access.hardware.device_name.tooltip")}
              rules={[{ required: true, message: t("settings.access.hardware.device_name.required") }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="expires_in_minutes"
              label={t("settings.access.hardware.expires_in_minutes.label")}
              tooltip={t("settings.access.hardware.expires_in_minutes.tooltip")}
              rules={[{ required: true, type: "number", min: 1, max: 1440 }]}
            >
              <InputNumber min={1} max={1440} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={creatingDeviceCode}>
                {t("settings.access.hardware.create_code")}
              </Button>
            </Form.Item>
          </Form>

          <Divider />

          <Typography.Title level={3} style={{ maxWidth: 720, margin: "0 auto 16px" }}>
            {t("settings.access.api_tokens_title")}
          </Typography.Title>
          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            style={{ maxWidth: 720, margin: "0 auto 24px" }}
            initialValues={{ expires_in_days: 365 }}
          >
            <Form.Item
              name="name"
              label={t("settings.access.token_name.label")}
              tooltip={t("settings.access.token_name.tooltip")}
              rules={[{ required: true, message: t("settings.access.token_name.required") }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="expires_in_days"
              label={t("settings.access.expires_in_days.label")}
              tooltip={t("settings.access.expires_in_days.tooltip")}
              rules={[{ required: true, type: "number", min: 1, max: 3650 }]}
            >
              <InputNumber min={1} max={3650} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={creating}>
                {t("settings.access.create_token")}
              </Button>
            </Form.Item>
          </Form>

          <Table<TokenItem>
            dataSource={tokens}
            rowKey="id"
            loading={loading}
            pagination={false}
            locale={{ emptyText: t("settings.access.empty") }}
            columns={[
              {
                title: t("settings.access.columns.name"),
                dataIndex: "name",
                key: "name",
              },
              {
                title: t("settings.access.columns.preview"),
                dataIndex: "token_preview",
                key: "token_preview",
                render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
              },
              {
                title: t("settings.access.columns.created"),
                dataIndex: "created",
                key: "created",
                render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm"),
              },
              {
                title: t("settings.access.columns.last_used"),
                dataIndex: "last_used",
                key: "last_used",
                render: (value: string | undefined) =>
                  value ? dayjs(value).format("YYYY-MM-DD HH:mm") : t("auth.values.never"),
              },
              {
                title: t("settings.access.columns.expires_at"),
                dataIndex: "expires_at",
                key: "expires_at",
                render: (value: string | undefined) =>
                  value ? dayjs(value).format("YYYY-MM-DD") : t("auth.values.never"),
              },
              {
                title: t("table.actions"),
                key: "actions",
                render: (_: unknown, record: TokenItem) => (
                  <Popconfirm title={t("settings.access.revoke_confirm")} onConfirm={() => revokeToken(record.id)}>
                    <Button danger size="small">
                      {t("settings.access.revoke")}
                    </Button>
                  </Popconfirm>
                ),
              },
            ]}
          />
        </>
      )}
      {contextHolder}
    </>
  );
}

export default AccessSettings;
