import { DashboardOutlined, FileOutlined, HighlightOutlined, PlusOutlined, UnorderedListOutlined, UserOutlined } from "@ant-design/icons";
import { useList, useTranslate } from "@refinedev/core";
import { Button, Card, Col, Row, Space, Statistic, Typography, theme } from "antd";
import { Content } from "antd/es/layout/layout";
import Title from "antd/es/typography/Title";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { ReactNode, useMemo } from "react";
import { Trans } from "react-i18next";
import { Link, useNavigate } from "react-router";
import Logo from "../../icon.svg?react";
import { OverviewCards } from "../insights/components/overviewCards";
import { useInsightsOverview } from "../insights/hooks";
import { ISpool } from "../spools/model";

dayjs.extend(utc);

const { useToken } = theme;

interface ResourceStatsCardProps {
  loading: boolean;
  value: number;
  resource: string;
  icon: ReactNode;
  title: string;
}

function ResourceStatsCard({ loading, value, resource, icon, title }: Readonly<ResourceStatsCardProps>) {
  return (
    <Col xs={12} md={6}>
      <Card
        loading={loading}
        actions={[
          <Link to={`/${resource}`} key="resource">
            <UnorderedListOutlined />
          </Link>,
          <Link to={`/${resource}/create`} key="create">
            <PlusOutlined />
          </Link>,
        ]}
      >
        <Statistic title={title} value={value} prefix={icon} />
      </Card>
    </Col>
  );
}

export const Home = () => {
  const { token } = useToken();
  const t = useTranslate();
  const navigate = useNavigate();
  const insightsFilters = useMemo(
    () => ({ threshold_g: 200, days: 30, allow_archived: false }),
    [],
  );
  const overview = useInsightsOverview(insightsFilters);

  const spools = useList<ISpool>({
    resource: "spool",
    pagination: { pageSize: 1 },
  });
  const filaments = useList<ISpool>({
    resource: "filament",
    pagination: { pageSize: 1 },
  });
  const vendors = useList<ISpool>({
    resource: "vendor",
    pagination: { pageSize: 1 },
  });

  const hasSpools = !spools.result || spools.result.data.length > 0;

  return (
    <Content
      style={{
        padding: "24px 16px",
        minHeight: 280,
        maxWidth: 1120,
        margin: "0 auto",
        backgroundColor: "transparent",
        color: token.colorText,
        fontFamily: token.fontFamily,
        fontSize: token.fontSizeLG,
        lineHeight: 1.5,
      }}
    >
      <Space direction="vertical" size="large" style={{ display: "flex" }}>
        <Card>
          <Row gutter={[24, 24]} align="middle">
            <Col xs={24} xl={14}>
              <Title
                style={{
                  display: "flex",
                  alignItems: "center",
                  fontSize: token.fontSizeHeading1,
                  marginBottom: 8,
                }}
              >
                <div
                  style={{
                    display: "inline-block",
                    height: "1.5em",
                    marginRight: "0.5em",
                  }}
                >
                  <Logo />
                </div>
                Spoolman
              </Title>
              <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 8 }}>
                {t("home.dashboard_title")}
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 16, maxWidth: 680 }}>
                {t("home.dashboard_description")}
              </Typography.Paragraph>
              <Space wrap>
                <Button type="primary" icon={<DashboardOutlined />} onClick={() => navigate("/insights")}>
                  {t("home.open_insights")}
                </Button>
                <Button icon={<PlusOutlined />} onClick={() => navigate("/spool/create")}>
                  {t("home.add_spool")}
                </Button>
              </Space>
            </Col>
            <Col xs={24} xl={10}>
              <Card size="small" style={{ backgroundColor: token.colorFillAlter, borderColor: token.colorBorderSecondary }}>
                <Typography.Text strong>{t("home.insights_card_title")}</Typography.Text>
                <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                  {t("home.insights_card_description")}
                </Typography.Paragraph>
              </Card>
            </Col>
          </Row>
        </Card>

        {hasSpools && <OverviewCards overview={overview.data} loading={overview.isLoading} onOpenLowStock={() => navigate("/insights")} />}

        <Row justify="center" gutter={[16, 16]}>
          <ResourceStatsCard
            resource="spool"
            title={t("spool.spool")}
            value={spools.result?.total || 0}
            loading={spools.query.isLoading}
            icon={<FileOutlined />}
          />
          <ResourceStatsCard
            resource="filament"
            title={t("filament.filament")}
            value={filaments.result?.total || 0}
            loading={filaments.query.isLoading}
            icon={<HighlightOutlined />}
          />
          <ResourceStatsCard
            resource="vendor"
            title={t("vendor.vendor")}
            value={vendors.result?.total || 0}
            loading={vendors.query.isLoading}
            icon={<UserOutlined />}
          />
        </Row>
        {!hasSpools && (
          <Card>
            <p style={{ marginTop: 0 }}>{t("home.welcome")}</p>
            <p style={{ marginBottom: 0 }}>
              <Trans
                i18nKey="home.description"
                components={{
                  helpPageLink: <Link to="/help" />,
                }}
              />
            </p>
          </Card>
        )}
      </Space>
    </Content>
  );
};

export default Home;
