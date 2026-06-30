import { useTranslate } from "@refinedev/core";
import { Button, Form, InputNumber, Select, Typography, message } from "antd";
import { useEffect } from "react";
import { useGetSetting, useSetSetting } from "../../utils/querySettings";
import { InsightsThresholdMode } from "../insights/model";

interface InsightsSettingsValues {
  insights_low_stock_threshold_mode: InsightsThresholdMode;
  insights_low_stock_threshold_g: number;
  insights_low_stock_threshold_percent: number;
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

function parseModeSetting(value: string | undefined): InsightsThresholdMode {
  if (!value) {
    return "percent";
  }

  try {
    const parsed = JSON.parse(value);
    return parsed === "weight" || parsed === "percent" ? parsed : "percent";
  } catch {
    return "percent";
  }
}

export function InsightsSettings() {
  const thresholdModeSetting = useGetSetting("insights_low_stock_threshold_mode");
  const thresholdWeightSetting = useGetSetting("insights_low_stock_threshold_g");
  const thresholdPercentSetting = useGetSetting("insights_low_stock_threshold_percent");
  const setThresholdMode = useSetSetting<InsightsThresholdMode>("insights_low_stock_threshold_mode");
  const setThresholdWeight = useSetSetting<number>("insights_low_stock_threshold_g");
  const setThresholdPercent = useSetSetting<number>("insights_low_stock_threshold_percent");
  const [form] = Form.useForm<InsightsSettingsValues>();
  const [messageApi, contextHolder] = message.useMessage();
  const t = useTranslate();

  useEffect(() => {
    form.setFieldsValue({
      insights_low_stock_threshold_mode: parseModeSetting(thresholdModeSetting.data?.value),
      insights_low_stock_threshold_g: parseNumberSetting(thresholdWeightSetting.data?.value, 200),
      insights_low_stock_threshold_percent: parseNumberSetting(thresholdPercentSetting.data?.value, 20),
    });
  }, [form, thresholdModeSetting.data?.value, thresholdPercentSetting.data?.value, thresholdWeightSetting.data?.value]);

  const onFinish = async (values: InsightsSettingsValues) => {
    const updates = [];

    if (thresholdModeSetting.data?.value !== JSON.stringify(values.insights_low_stock_threshold_mode)) {
      updates.push(setThresholdMode.mutateAsync(values.insights_low_stock_threshold_mode));
    }
    if (thresholdWeightSetting.data?.value !== JSON.stringify(values.insights_low_stock_threshold_g)) {
      updates.push(setThresholdWeight.mutateAsync(values.insights_low_stock_threshold_g));
    }
    if (thresholdPercentSetting.data?.value !== JSON.stringify(values.insights_low_stock_threshold_percent)) {
      updates.push(setThresholdPercent.mutateAsync(values.insights_low_stock_threshold_percent));
    }

    if (updates.length > 0) {
      await Promise.all(updates);
      messageApi.success(t("notifications.saveSuccessful"));
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
          insights_low_stock_threshold_mode: parseModeSetting(thresholdModeSetting.data?.value),
          insights_low_stock_threshold_g: parseNumberSetting(thresholdWeightSetting.data?.value, 200),
          insights_low_stock_threshold_percent: parseNumberSetting(thresholdPercentSetting.data?.value, 20),
        }}
        onFinish={onFinish}
        style={{
          maxWidth: "600px",
          margin: "0 auto",
        }}
      >
        <Form.Item
          label={t("settings.insights.low_stock_threshold_mode.label")}
          tooltip={t("settings.insights.low_stock_threshold_mode.tooltip")}
          name="insights_low_stock_threshold_mode"
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { label: t("settings.insights.low_stock_threshold_mode.options.percent"), value: "percent" },
              { label: t("settings.insights.low_stock_threshold_mode.options.weight"), value: "weight" },
            ]}
          />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, next) => prev.insights_low_stock_threshold_mode !== next.insights_low_stock_threshold_mode}>
          {({ getFieldValue }) =>
            getFieldValue("insights_low_stock_threshold_mode") === "weight" ? (
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
            ) : (
              <Form.Item
                label={t("settings.insights.low_stock_threshold_percent.label")}
                tooltip={t("settings.insights.low_stock_threshold_percent.tooltip")}
                name="insights_low_stock_threshold_percent"
                rules={[
                  {
                    required: true,
                    type: "number",
                    min: 0,
                    max: 100,
                  },
                ]}
              >
                <InputNumber min={0} max={100} style={{ width: "100%" }} />
              </Form.Item>
            )
          }
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 8, span: 16 }}>
          <Button
            type="primary"
            htmlType="submit"
            loading={
              thresholdModeSetting.isFetching ||
              thresholdWeightSetting.isFetching ||
              thresholdPercentSetting.isFetching ||
              setThresholdMode.isPending ||
              setThresholdWeight.isPending ||
              setThresholdPercent.isPending
            }
          >
            {t("buttons.save")}
          </Button>
        </Form.Item>
      </Form>
      {contextHolder}
    </>
  );
}