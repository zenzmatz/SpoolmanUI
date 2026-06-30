import { Button, Card, Form, Input, Typography, message } from "antd";
import { useTranslate } from "@refinedev/core";
import { useNavigate } from "react-router";
import authProvider from "../../authProvider";

interface LoginValues {
  username: string;
  password: string;
}

export const Login = () => {
  const t = useTranslate();
  const navigate = useNavigate();
  const [form] = Form.useForm<LoginValues>();
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: LoginValues) => {
    const redirectTo = new URLSearchParams(globalThis.location.search).get("to") ?? "/";
    const result = await authProvider.login({
      ...values,
      to: redirectTo,
    });

    if (!result.success) {
      messageApi.error(result.error?.message ?? t("auth.errors.login_failed"));
      form.setFieldValue("password", "");
      return;
    }

    navigate((result.redirectTo as string | undefined) ?? "/", { replace: true });
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <Card style={{ width: "100%", maxWidth: 420 }}>
        <Typography.Title level={2} style={{ marginBottom: 8 }}>
          {t("auth.login.title")}
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 24 }}>
          {t("auth.login.description")}
        </Typography.Paragraph>

        <Form form={form} layout="vertical" onFinish={onFinish} autoComplete="on">
          <Form.Item
            name="username"
            label={t("auth.login.username")}
            rules={[{ required: true, message: t("auth.login.username_required") }]}
          >
            <Input autoFocus autoComplete="username" />
          </Form.Item>

          <Form.Item
            name="password"
            label={t("auth.login.password")}
            rules={[{ required: true, message: t("auth.login.password_required") }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block>
              {t("auth.login.submit")}
            </Button>
          </Form.Item>
        </Form>
      </Card>
      {contextHolder}
    </div>
  );
};

export default Login;
