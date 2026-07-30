import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
} from "@heroui/drawer";
import { Popover, PopoverContent, PopoverTrigger } from "@heroui/popover";
import { Card, CardHeader, CardBody } from "@heroui/card";
import { Divider } from "@heroui/divider";
import { Tooltip } from "@heroui/tooltip";
import { useState } from "react";
import { Button } from "@heroui/button";

import { LeftArrowIcon } from "../icons";
import StatusTimeline from "../StatusTimeline";

import { useCustomQuery } from "@/hooks";
import { aiModelApi } from "@/api";
import {
  AIModelInfoWithEndpoint,
  ModelFromEndpointInfo,
  AIModelStatusEnum,
} from "@/types";
import StatusBadge from "@/components/StatusBadge";
import { DataTable } from "@/components/DataTable";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";

interface ModelDetailProps {
  id: string | number;
  isOpen: boolean;
  onClose: () => void;
}

const ModelDetailDrawer = ({ id, isOpen, onClose }: ModelDetailProps) => {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(5);

  // 获取模型详情
  const {
    data: model,
    isLoading,
    error,
  } = useCustomQuery<AIModelInfoWithEndpoint>(
    ["model-drawer", id, page, size],
    () => aiModelApi.getAIModelById(Number(id), page, size),
    { staleTime: 30000, enabled: !!id && isOpen },
  );

  // 处理页码变化
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString + "Z").toLocaleString();
  };

  // 定义表格列
  const columns = [
    // { key: "endpoint", label: "端点" },
    { key: "url", label: "URL" },
    { key: "status", label: "状态" },
    { key: "performance", label: "性能" },
    // { key: "actions", label: "操作" },
  ];

  // 渲染单元格内容
  const renderCell = (endpoint: ModelFromEndpointInfo, columnKey: string) => {
    switch (columnKey) {
      case "url":
        return (
          <span className="whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
            {endpoint.url}
          </span>
        );
      case "status":
        return (
          <Popover showArrow placement="top">
            <PopoverTrigger>
              <Button isIconOnly className="p-0 h-auto w-auto" variant="light">
                <StatusBadge status={endpoint.status} />
              </Button>
            </PopoverTrigger>
            <PopoverContent>
              <StatusTimeline
                performanceTests={endpoint.model_performances}
                type="model"
              />
            </PopoverContent>
          </Popover>
        );
      case "performance":
        return endpoint.status === AIModelStatusEnum.AVAILABLE ? (
          <Tooltip content="生成速度（每秒token数）">
            <div>
              {endpoint.token_per_second
                ? `${endpoint.token_per_second.toFixed(1)} tps`
                : "未测试"}
            </div>
          </Tooltip>
        ) : (
          "不可用"
        );
      //   case "actions":
      //     return (
      //       <Button
      //         isIconOnly
      //         className="text-lg text-default-400 active:opacity-50"
      //         size="sm"
      //         variant="light"
      //       >
      //         <EyeIcon />
      //       </Button>
      //     );
      default:
        return null;
    }
  };

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
          error={new Error((error as Error)?.message || "加载模型详情失败")}
        />
      );
    }

    if (!model) {
      return (
        <div className="text-center py-8">
          <p>未找到模型信息</p>
        </div>
      );
    }

    return (
      <>
        <div className="grid grid-cols-1 gap-6 mb-6">
          {/* 模型基本信息卡片 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 p-4">
              <h3 className="text-xl font-bold">模型信息</h3>
              <div className="flex flex-row gap-2 items-center justify-end w-auto">
                <StatusBadge
                  status={
                    model.avaliable_endpoint_count > 0
                      ? AIModelStatusEnum.AVAILABLE
                      : AIModelStatusEnum.UNAVAILABLE
                  }
                />
              </div>
            </CardHeader>
            <Divider />
            <CardBody className="p-4">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm text-gray-500 dark:text-gray-400">
                    ID
                  </h4>
                  <p>{model.id}</p>
                </div>
                <div>
                  <h4 className="text-sm text-gray-500 dark:text-gray-400">
                    名称
                  </h4>
                  <p>{model.name}</p>
                </div>
                <div>
                  <h4 className="text-sm text-gray-500 dark:text-gray-400">
                    标签
                  </h4>
                  <p>{model.tag}</p>
                </div>
                <div>
                  <h4 className="text-sm text-gray-500 dark:text-gray-400">
                    创建时间
                  </h4>
                  <p>
                    {model.created_at ? formatDate(model.created_at) : "未知"}
                  </p>
                </div>
                <div>
                  <h4 className="text-sm text-gray-500 dark:text-gray-400">
                    可用端点数
                  </h4>
                  <p>
                    {model.avaliable_endpoint_count} /{" "}
                    {model.total_endpoint_count}
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* 可用端点列表卡片 */}
          <Card>
            <CardHeader className="p-4">
              <h3 className="text-xl font-bold">可用端点</h3>
            </CardHeader>
            <Divider />
            <CardBody className="p-4">
              {model.endpoints.items.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-gray-500 dark:text-gray-400">
                    没有可用的端点
                  </p>
                </div>
              ) : (
                <DataTable
                  columns={columns}
                  data={model.endpoints.items}
                  emptyContent={
                    <p className="text-gray-500 dark:text-gray-400">
                      没有可用的端点
                    </p>
                  }
                  isLoading={isLoading}
                  page={page}
                  pages={Math.ceil((model.endpoints.total || 0) / size)}
                  removeWrapper={true}
                  renderCell={renderCell}
                  selectedSize={size}
                  setSize={setSize}
                  showCustomPageSize={false}
                  title="可用端点"
                  total={model.endpoints.total}
                  onPageChange={handlePageChange}
                />
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
        {() => (
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
            </DrawerHeader>
            <DrawerBody className="pt-16">{renderContent()}</DrawerBody>
          </>
        )}
      </DrawerContent>
    </Drawer>
  );
};

export default ModelDetailDrawer;
