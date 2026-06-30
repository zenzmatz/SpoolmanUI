import { useTranslate } from "@refinedev/core";
import { Button, Form, InputNumber, Typography, message } from "antd";
import { useEffect } from "react";
import { useGetSetting, useSetSetting } from "../../utils/querySettings";

interface InsightsSettingsValues {
  insights_low_stock_threshold_g: number;
}

function parseNumberSetting(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "number" && Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function InsightsSettings() {
  const thresholdSetting = useGetSetting("insights_low_stock_threshold_g");
  const setThreshold = useSetSetting("insights_low_stock_threshold_g");
  const [form] = Form.useForm<InsightsSettingsValues>();
  const [messageApi, contextHolder] = message.useMessage();
  const t = useTranslate();

  useEffect(() => {
    form.setFieldsValue({
      insights_low_stock_threshold_g: parseNumberSetting(thresholdSetting.data?.value, 200),
    });
  }, [form, thresholdSetting.data?.value]);

  useEffect(() => {
    if (setThreshold.isSuccess) {
      messageApi.success(t("notifications.saveSuccessful"));
    }
  }, [messageApi, setThreshold.isSuccess, t]);

  const onFinish = (values: InsightsSettingsValues) => {
    if (thresholdSetting.data?.value !== JSON.stringify(values.insights_low_stock_threshold_g)) {
      setThreshold.mutate(values.insights_low_stock_threshold_g);
    }
  };

  return (
    <>
      <Typography.Paragraph type="secondary" style={{ maxWidth: "600px", margin: "0 auto 24px" }}>
        {t("settings.insights.description")}
      </Typography.Paragraph>
      <Form
        form={form}
        labelCol={{ span: 8 }}
        wrapperCol={{ span: 16 }}
        initialValues={{
          insights_low_stock_threshold_g: parseNumberSetting(thresholdSetting.data?.value, 200),
        }}
        onFinish={onFinish}
        style={{
          maxWidth: "600px",
          margin: "0 auto",
        }}
      >
        <Form.Item
          label={t("settings.insights.low_stock_threshold_g.label")}
          tooltip={t("settings.insights.low_stock_threshold_g.tooltip")}
          name="insights_low_stock_threshold_g"
          rules={[
            {
              required: true,
              type: "number",
              min: 0,
            },
          ]}
        >
          <InputNumber min={0} style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 8, span: 16 }}>
          <Button type="primary" htmlType="submit" loading={thresholdSetting.isFetching || setThreshold.isPending}>
            {t("buttons.save")}
          </Button>
        </Form.Item>
      </Form>
      {contextHolder}
    </>
  );
}