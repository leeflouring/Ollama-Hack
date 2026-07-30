import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
} from "@heroui/drawer";
import { Card, CardHeader, CardBody } from "@heroui/card";
import { Divider } from "@heroui/divider";
import { Tooltip } from "@heroui/tooltip";
import { Button } from "@heroui/button";

import { LeftArrowIcon } from "../icons";

import RequestsChart from "./RequestsChart";

import { useCustomQuery } from "@/hooks";
import { apiKeyApi } from "@/api";
import { ApiKeyUsageStats } from "@/types";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";

interface ApiKeyStatsDrawerProps {
  id: string | number;
  isOpen: boolean;
  onClose: () => void;
  apiKeyName?: string;
}

const ApiKeyStatsDrawer = ({
  id,
  isOpen,
  onClose,
  apiKeyName = "API 密钥",
}: ApiKeyStatsDrawerProps) => {
  // 获取API密钥使用统计
  const {
    data: stats,
    isLoading,
    error,
  } = useCustomQuery<ApiKeyUsageStats>(
    ["apikey-stats", id],
    () => apiKeyApi.getApiKeyStats(Number(id)),
    { staleTime: 30000, enabled: !!id && isOpen },
  );

  // 渲染抽屉内容
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="large" />
        </div>
      );
    }

    if (error) {
      return (
        <ErrorDisplay
          error={
            new Error((error as Error)?.message || "加载API密钥使用统计失败")
          }
        />
      );
    }

    if (!stats) {
      return (
        <div className="text-center py-8">
          <p>未找到API密钥使用统计</p>
        </div>
      );
    }

    return (
      <>
        <div className="grid grid-cols-1 gap-6 mb-6">
          {/* API密钥使用统计卡片 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 p-4">
              <h3 className="text-xl font-bold">使用统计</h3>
            </CardHeader>
            <Divider />
            <CardBody className="p-4 grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              <Card className="p-4 rounded-lg text-center">
                <h4 className="text-default-500 text-sm mb-1">总请求数</h4>
                <p className="text-2xl font-bold">
                  {stats.total_requests.toLocaleString()}
                </p>
              </Card>
              <Card className="p-4 rounded-lg text-center">
                <h4 className="text-default-500 text-sm mb-1">
                  最近30天请求数
                </h4>
                <p className="text-2xl font-bold">
                  {stats.last_30_days_requests.toLocaleString()}
                </p>
              </Card>
              <Card className="p-4 rounded-lg text-center">
                <h4 className="text-default-500 text-sm mb-1">今日请求数</h4>
                <p className="text-2xl font-bold">
                  {stats.requests_today.toLocaleString()}
                </p>
              </Card>
              <Tooltip content="成功请求占总请求的百分比">
                <Card className="p-4 rounded-lg text-center">
                  <h4 className="text-default-500 text-sm mb-1">成功率</h4>
                  <p className="text-2xl font-bold">
                    {stats.total_requests > 0
                      ? `${((stats.successful_requests / stats.total_requests) * 100).toFixed(1)}%`
                      : "0%"}
                  </p>
                </Card>
              </Tooltip>
              <Card className="p-4 rounded-lg text-center">
                <h4 className="text-default-500 text-sm mb-1">成功请求数</h4>
                <p className="text-2xl font-bold">
                  {stats.successful_requests.toLocaleString()}
                </p>
              </Card>
              <Card className="p-4 rounded-lg text-center">
                <h4 className="text-default-500 text-sm mb-1">失败请求数</h4>
                <p className="text-2xl font-bold">
                  {stats.failed_requests.toLocaleString()}
                </p>
              </Card>
            </CardBody>
          </Card>

          {/* 每日请求图表卡片 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 p-4">
              <h3 className="text-xl font-bold">每日请求数</h3>
            </CardHeader>
            <Divider />
            <CardBody className="p-4">
              {stats.requests_per_day && stats.requests_per_day.length > 0 ? (
                <div className="w-full h-72 p-2">
                  <RequestsChart data={stats.requests_per_day} />
                </div>
              ) : (
                <div className="py-8 text-center">
                  <p className="text-gray-500 dark:text-gray-400">
                    暂无每日请求数据
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </>
    );
  };

  return (
    <Drawer
      backdrop="blur"
      classNames={{
        base: "data-[placement=right]:sm:m-2 data-[placement=left]:sm:m-2 rounded-medium",
      }}
      isOpen={isOpen}
      placement="right"
      size="lg"
      onOpenChange={onClose}
    >
      <DrawerContent>
        <>
          <DrawerHeader className="absolute top-0 inset-x-0 z-50 flex flex-row gap-2 px-2 py-2 border-b border-default-200/50 justify-between bg-content1/50 backdrop-saturate-150 backdrop-blur-lg">
            <Tooltip content="关闭">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={onClose}
              >
                <LeftArrowIcon />
              </Button>
            </Tooltip>
            <div>
              <h2 className="text-xl font-medium text-foreground">
                {apiKeyName} 使用统计
              </h2>
            </div>
            <div />
          </DrawerHeader>
          <DrawerBody className="pt-16">{renderContent()}</DrawerBody>
        </>
      </DrawerContent>
    </Drawer>
  );
};

export default ApiKeyStatsDrawer;
