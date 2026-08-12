import React from "react";
import { Button } from "@heroui/button";
import { SortDescriptor } from "@heroui/table";
import { Tooltip } from "@heroui/tooltip";

import { DataTable } from "@/components/DataTable";
import StatusBadge from "@/components/StatusBadge";
import {
  AIModelInfoWithEndpointCount,
  AIModelStatusEnum,
  SortOrder,
} from "@/types";
import { EyeIcon } from "@/components/icons";

interface ModelTableProps {
  models: AIModelInfoWithEndpointCount[] | undefined;
  isLoading: boolean;
  error: any;
  page: number;
  pageSize: number;
  searchTerm: string;
  orderBy: string | undefined;
  order: SortOrder | undefined;
  setSearchTerm: (term: string) => void;
  setPageSize: (size: number) => void;
  setOrderBy?: (orderBy: string) => void;
  setOrder?: (order: SortOrder) => void;
  onOpenModelDetail: (modelId: number) => void;
  onPageChange: (page: number) => void;
  onSearch: (e: React.FormEvent) => void;
  totalPages?: number;
  totalItems?: number;
  topActionContent?: React.ReactNode;
}

const ModelTable: React.FC<ModelTableProps> = ({
  models,
  isLoading,
  error,
  page,
  pageSize,
  searchTerm,
  orderBy,
  order,
  setSearchTerm,
  setPageSize,
  setOrderBy,
  setOrder,
  onOpenModelDetail,
  onPageChange,
  onSearch,
  totalPages,
  totalItems,
  topActionContent,
}) => {
  // 获取模型状态
  const getModelStatus = (
    model: AIModelInfoWithEndpointCount,
  ): AIModelStatusEnum => {
    if (model.avaliable_endpoint_count === 0) {
      return AIModelStatusEnum.UNAVAILABLE;
    }

    return AIModelStatusEnum.AVAILABLE;
  };

  // 排序状态
  const [sortDescriptor, setSortDescriptor] = React.useState<SortDescriptor>({
    column: orderBy || "id",
    direction:
      order === SortOrder.ASC
        ? "ascending"
        : order === SortOrder.DESC
          ? "descending"
          : "ascending",
  });

  // 定义表格列
  const columns = [
    { key: "id", label: "ID", allowsSorting: true },
    { key: "name", label: "名称", allowsSorting: true },
    { key: "tag", label: "标签", allowsSorting: true },
    { key: "endpoint_count", label: "端点数量" },
    { key: "status", label: "状态" },
    { key: "created_at", label: "创建时间", allowsSorting: true },
    { key: "actions", label: "操作" },
  ];

  // 处理排序
  const handleSort = (descriptor: SortDescriptor) => {
    setSortDescriptor(descriptor);
    if (descriptor.column) {
      const newOrderBy = descriptor.column.toString();
      const newOrder =
        descriptor.direction === "ascending" ? SortOrder.ASC : SortOrder.DESC;

      // 更新父组件中的排序状态
      if (orderBy !== newOrderBy || order !== newOrder) {
        setOrderBy &&
          typeof setOrderBy === "function" &&
          setOrderBy(newOrderBy);
        setOrder && typeof setOrder === "function" && setOrder(newOrder);
      }
    }
  };

  // 渲染单元格内容
  const renderCell = (
    model: AIModelInfoWithEndpointCount,
    columnKey: string,
  ) => {
    switch (columnKey) {
      case "id":
        return model.id;
      case "name":
        return (
          <span className="whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
            {model.name}
          </span>
        );
      case "tag":
        return (
          <span className="whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
            {model.tag}
          </span>
        );
      case "endpoint_count":
        return (
          <>
            {model.avaliable_endpoint_count} / {model.total_endpoint_count}
          </>
        );
      case "status":
        return <StatusBadge status={getModelStatus(model)} />;
      case "created_at":
        return model.created_at
          ? new Date(model.created_at + "Z").toLocaleString()
          : "-";
      case "actions":
        return (
          <div className="relative flex items-center gap-2">
            <Tooltip content="查看模型">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => {
                  if (model.id) {
                    onOpenModelDetail(model.id);
                  }
                }}
              >
                <EyeIcon />
              </Button>
            </Tooltip>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <DataTable<AIModelInfoWithEndpointCount>
      autoSearchDelay={1000}
      columns={columns}
      data={models || []}
      emptyContent={
        <p className="text-xl text-gray-600 dark:text-gray-400">暂无模型数据</p>
      }
      error={error}
      isLoading={isLoading}
      page={page}
      pages={totalPages}
      renderCell={renderCell}
      searchPlaceholder="搜索模型..."
      searchTerm={searchTerm}
      selectedSize={pageSize}
      setSearchTerm={setSearchTerm}
      setSize={setPageSize}
      sortDescriptor={sortDescriptor}
      title="模型列表"
      topActionContent={topActionContent}
      total={totalItems}
      onPageChange={onPageChange}
      onSearch={onSearch}
      onSortChange={handleSort}
    />
  );
};

export default ModelTable;
