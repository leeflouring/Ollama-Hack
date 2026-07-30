import { useState, useEffect } from "react";
import { Button } from "@heroui/button";
import { Input } from "@heroui/input";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from "@heroui/modal";
import { Tooltip } from "@heroui/tooltip";
import { Form } from "@heroui/form";
import { Snippet } from "@heroui/snippet";
import { Link } from "@heroui/link";
import { Image } from "@heroui/image";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
} from "@heroui/drawer";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "@heroui/use-theme";
import { SortDescriptor } from "@react-types/shared";

import { useAuth } from "@/contexts/AuthContext";
import {
  useCustomQuery,
  useCustomMutation,
  usePaginationUrlState,
  PaginationValidationConfig,
} from "@/hooks";
import { apiKeyApi } from "@/api";
import {
  ApiKeyCreate,
  ApiKeyInfo,
  ApiKeyResponse,
  PageResponse,
  SortOrder,
} from "@/types";
import DashboardLayout from "@/layouts/Main";
import {
  DeleteIcon,
  PlusIcon,
  StatisticsIcon,
  QuestionMarkIcon,
  LeftArrowIcon,
  LogoIcon,
  LinkIcon,
  BoolAtlasIcon,
  BookIcon,
} from "@/components/icons";
import { DataTable } from "@/components/DataTable";
import { useDialog } from "@/contexts/DialogContext";
import { StatsDrawer } from "@/components/apikeys";

SyntaxHighlighter.registerLanguage("bash", bash);

const ApiKeysPage = () => {
  const { theme } = useTheme();
  const { isAdmin } = useAuth();
  const { confirm } = useDialog();

  // 验证配置
  const [validationConfig, setValidationConfig] =
    useState<PaginationValidationConfig>({
      page: { min: 1 },
      pageSize: { min: 5, max: 100 },
      totalPages: 1,
      orderBy: {
        allowedFields: ["id", "name", "created_at", "last_used_at"],
        defaultField: "id",
      },
    });

  // 使用URL参数管理状态，替代多个单独的useState
  const {
    page,
    pageSize: size,
    search: searchTerm,
    orderBy,
    order,
    setPage,
    setPageSize: setSize,
    setSearch: setSearchTerm,
    setOrderBy,
    setOrder,
  } = usePaginationUrlState(
    {
      page: 1,
      pageSize: 10,
      search: "",
      orderBy: undefined,
      order: undefined,
    },
    validationConfig,
  );

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState("");
  const [createdApiKey, setCreatedApiKey] = useState<ApiKeyResponse | null>(
    null,
  );
  const [isCreating, setIsCreating] = useState(false);
  const [isHelpDrawerOpen, setIsHelpDrawerOpen] = useState(false);

  // 统计抽屉状态
  const [isStatsDrawerOpen, setIsStatsDrawerOpen] = useState(false);
  const [selectedApiKeyId, setSelectedApiKeyId] = useState<number | null>(null);
  const [selectedApiKeyName, setSelectedApiKeyName] = useState<string>("");

  // 排序状态
  const [sortDescriptor, setSortDescriptor] = useState<SortDescriptor>({
    column: orderBy || "id",
    direction:
      order === SortOrder.ASC
        ? "ascending"
        : order === SortOrder.DESC
          ? "descending"
          : "ascending",
  });

  // 处理排序
  const handleSort = (descriptor: SortDescriptor) => {
    setSortDescriptor(descriptor);
    setOrderBy(descriptor.column?.toString());
    setOrder(
      descriptor.direction === "ascending" ? SortOrder.ASC : SortOrder.DESC,
    );
  };

  // 获取 API 密钥列表
  const {
    data: apiKeys,
    isLoading,
    error,
    refetch,
  } = useCustomQuery<PageResponse<ApiKeyInfo>>(
    ["apikeys", page, size, searchTerm, orderBy, order],
    () =>
      apiKeyApi.getApiKeys({
        page,
        size,
        search: searchTerm,
        order_by: orderBy,
        order,
      }),
    { staleTime: 30000 },
  );

  // 当总页数变化时，更新验证配置
  useEffect(() => {
    if (apiKeys?.pages) {
      setValidationConfig((prev) => ({
        ...prev,
        totalPages: apiKeys.pages,
      }));
    }
  }, [apiKeys?.pages]);

  // 创建 API 密钥
  const createApiKeyMutation = useCustomMutation<ApiKeyResponse, ApiKeyCreate>(
    (data) => apiKeyApi.createApiKey(data),
    {
      onSuccess: (data) => {
        setCreatedApiKey(data);
        refetch();
        setIsCreating(false);
      },
      onError: () => {
        setIsCreating(false);
      },
    },
  );

  // 处理搜索
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // 搜索时重置页码
    setPage(1);
    refetch();
  };

  // 处理页码变化
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 处理创建 API 密钥
  const handleCreateApiKey = () => {
    setIsCreating(true);
    createApiKeyMutation.mutate({ name: newApiKeyName });
  };

  // 处理关闭创建成功对话框
  const handleCloseSuccessModal = () => {
    setCreatedApiKey(null);
    setNewApiKeyName("");
    setIsCreateModalOpen(false);
  };

  // 处理删除 API 密钥
  const handleDeleteApiKey = (id: number) => {
    confirm("确定要删除此 API 密钥吗？此操作不可逆。", async () => {
      try {
        await apiKeyApi.deleteApiKey(id);
        refetch();
      } catch (err) {
        addToast({
          title: "删除 API 密钥失败",
          description: (err as Error).message || "请重试",
          color: "danger",
        });
      }
    });
  };

  // 打开API密钥统计抽屉
  const openApiKeyStats = (apiKey: ApiKeyInfo) => {
    setSelectedApiKeyId(apiKey.id);
    setSelectedApiKeyName(apiKey.name);
    setIsStatsDrawerOpen(true);
  };

  // 关闭API密钥统计抽屉
  const closeApiKeyStats = () => {
    setIsStatsDrawerOpen(false);
  };

  // 定义表格列
  const columns = [
    { key: "id", label: "ID", allowsSorting: true },
    { key: "name", label: "名称", allowsSorting: true },
    { key: "created_at", label: "创建时间", allowsSorting: true },
    { key: "last_used_at", label: "最后使用时间", allowsSorting: true },
    ...(isAdmin
      ? [{ key: "user_id", label: "用户", allowsSorting: true }]
      : []),
    { key: "actions", label: "操作" },
  ];

  // 渲染单元格内容
  const renderCell = (apiKey: ApiKeyInfo, columnKey: string) => {
    switch (columnKey) {
      case "id":
        return apiKey.id;
      case "name":
        return (
          <span className="whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
            {apiKey.name}
          </span>
        );
      case "created_at":
        return new Date(apiKey.created_at).toLocaleString();
      case "last_used_at":
        return apiKey.last_used_at
          ? new Date(apiKey.last_used_at).toLocaleString()
          : "从未使用";
      case "user_id":
        return apiKey.user_name || "-";
      case "actions":
        return (
          <div className="relative flex items-center gap-2">
            <Tooltip content="查看密钥用量">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => openApiKeyStats(apiKey)}
              >
                <StatisticsIcon />
              </Button>
            </Tooltip>
            <Tooltip color="danger" content="删除密钥">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => {
                  if (apiKey.id) {
                    handleDeleteApiKey(apiKey.id);
                  }
                }}
              >
                <DeleteIcon />
              </Button>
            </Tooltip>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <DashboardLayout current_root_href="/apikeys">
      <DataTable<ApiKeyInfo>
        addButtonProps={{
          tooltip: "创建 API 密钥",
          onClick: () => setIsCreateModalOpen(true),
          isIconOnly: true,
        }}
        autoSearchDelay={1000}
        columns={columns}
        data={apiKeys?.items || []}
        emptyContent={
          <>
            <p className="text-xl text-gray-600 dark:text-gray-400">
              暂无 API 密钥数据
            </p>
            <Tooltip
              color="primary"
              content="创建第一个 API 密钥"
              placement="bottom"
            >
              <Button
                isIconOnly
                className="mt-4"
                color="primary"
                onPress={() => setIsCreateModalOpen(true)}
              >
                <PlusIcon />
              </Button>
            </Tooltip>
          </>
        }
        error={error}
        isLoading={isLoading}
        page={page}
        pageSize={size}
        pages={apiKeys?.pages}
        renderCell={renderCell}
        searchPlaceholder="搜索 API 密钥..."
        searchTerm={searchTerm}
        selectedSize={size}
        setSearchTerm={setSearchTerm}
        setSize={setSize}
        sortDescriptor={sortDescriptor}
        title="API 密钥列表"
        topActionContent={
          <Tooltip color="default" content="使用方法">
            <Button
              isIconOnly
              color="default"
              variant="bordered"
              onPress={() => setIsHelpDrawerOpen(true)}
            >
              <QuestionMarkIcon />
            </Button>
          </Tooltip>
        }
        total={apiKeys?.total}
        onPageChange={handlePageChange}
        onSearch={handleSearch}
        onSortChange={handleSort}
      />

      {/* 创建 API 密钥对话框 */}
      <Modal
        isOpen={isCreateModalOpen}
        placement="center"
        onClose={() => setIsCreateModalOpen(false)}
      >
        <ModalContent>
          {(onClose) => (
            <Form className="w-full" onSubmit={handleCreateApiKey}>
              <ModalHeader>
                {createdApiKey ? "密钥创建成功" : "创建 API 密钥"}
              </ModalHeader>
              <ModalBody className="w-full">
                {createdApiKey ? (
                  <div>
                    <p className="mb-2">
                      请保存好您的 API 密钥，这是唯一可以看到它的机会：
                    </p>
                    <Snippet color="primary" symbol="">
                      {createdApiKey.key}
                    </Snippet>
                  </div>
                ) : (
                  <Input
                    fullWidth
                    isRequired
                    errorMessage={({ validationErrors }) => {
                      return validationErrors;
                    }}
                    label="API 密钥名称"
                    maxLength={128}
                    minLength={3}
                    placeholder="输入 API 密钥名称"
                    value={newApiKeyName}
                    onChange={(e) => setNewApiKeyName(e.target.value)}
                  />
                )}
              </ModalBody>
              <ModalFooter className="w-full">
                {createdApiKey ? (
                  <Button color="primary" onPress={handleCloseSuccessModal}>
                    确定
                  </Button>
                ) : (
                  <>
                    <Button
                      disabled={isCreating}
                      variant="light"
                      onPress={onClose}
                    >
                      取消
                    </Button>
                    <Button
                      color="primary"
                      disabled={isCreating}
                      isLoading={isCreating}
                      onPress={handleCreateApiKey}
                    >
                      创建
                    </Button>
                  </>
                )}
              </ModalFooter>
            </Form>
          )}
        </ModalContent>
      </Modal>

      {/* API密钥统计抽屉 */}
      {selectedApiKeyId && (
        <StatsDrawer
          apiKeyName={selectedApiKeyName}
          id={selectedApiKeyId}
          isOpen={isStatsDrawerOpen}
          onClose={closeApiKeyStats}
        />
      )}

      {/* 使用方法抽屉 */}
      <Drawer
        backdrop="blur"
        classNames={{
          base: "data-[placement=right]:sm:m-2 data-[placement=left]:sm:m-2  rounded-medium",
        }}
        isOpen={isHelpDrawerOpen}
        placement="right"
        size="2xl"
        onClose={() => setIsHelpDrawerOpen(false)}
      >
        <DrawerContent>
          <DrawerHeader className="absolute top-0 inset-x-0 z-50 flex flex-row gap-2 px-2 py-2 border-b border-default-200/50 justify-between bg-content1/50 backdrop-saturate-150 backdrop-blur-lg">
            <Tooltip content="关闭">
              <Button
                isIconOnly
                className="text-default-400 active:opacity-50 text-lg"
                variant="light"
                onPress={() => setIsHelpDrawerOpen(false)}
              >
                <LeftArrowIcon />
              </Button>
            </Tooltip>
          </DrawerHeader>
          <DrawerBody className="pt-16 w-full">
            <div className="flex w-full justify-center items-center pt-4">
              <LogoIcon className="w-32 h-32" />
            </div>
            <div className="flex flex-col gap-2 py-4">
              <h1 className="text-2xl font-bold leading-7">
                聚合 API 使用方法
              </h1>
              <div className="flex flex-col mt-4 gap-3 items-start">
                <h2 className="text-medium font-medium">什么是聚合 API ?</h2>
                <div className="text-medium text-default-500 flex flex-col gap-2">
                  <p>
                    聚合 API 是 <i>Ollama Hack</i> 的核心功能，旨在通过一个仿
                    Ollama 的 OpenAI 兼容 API，智能访问扫描到的高可用模型。
                  </p>
                </div>
              </div>
              <div className="flex flex-col mt-4 gap-3 items-start w-full">
                <h2 className="text-medium font-medium">如何使用聚合 API ?</h2>
                <div className="text-medium text-default-500 flex flex-col gap-2">
                  <p>
                    首先，你需要生成一个 API 密钥。注意，你只会在创建时看到 API
                    密钥，生成后将无法再次查看，请妥善保管。
                  </p>
                  <div className="flex flex-col gap-2 w-full justify-center items-center">
                    <Image
                      alt="API 密钥创建"
                      className="h-full"
                      src="/images/apikeys/apikey-create.png"
                    />
                    <Image
                      alt="API 密钥创建"
                      className="h-full"
                      src="/images/apikeys/apikey-created.png"
                    />
                  </div>
                  <p>
                    接下来你就可以使用这个 API 密钥来访问聚合 API 了。API
                    密钥可以通过请求头传递。
                  </p>
                  <p>例如，你可以这样访问聚合 API：</p>
                  <SyntaxHighlighter
                    language="bash"
                    style={theme === "light" ? oneLight : oneDark}
                    wrapLines={true}
                    wrapLongLines={true}
                  >
                    {`curl -X POST http://localhost:3000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <你的 API 密钥>" \\
  -d '{
    "model": "qwq:latest",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手"},
      {"role": "user", "content": "你好，请介绍一下自己"}
    ]
  }'`}
                  </SyntaxHighlighter>
                  <p>
                    聚合 API
                    会智能检测你使用的模型，并按照生成速度顺序尝试最优端点转发你的请求。所有的
                    API 都和 Ollama 的 API
                    兼容，包括流式生成等功能。你只需要按照 Ollama 的 API
                    文档来调用即可，下面提供了 Ollama 官方 API 文档以供参考。
                  </p>
                  <div className="flex justify-around w-full mt-4">
                    <div className="flex gap-3 items-center">
                      <div className="flex items-center justify-center border-1 border-default-200/50 rounded-small w-11 h-11">
                        <BookIcon className="w-6 h-6" />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <Link
                          isExternal
                          showAnchorIcon
                          anchorIcon={<LinkIcon />}
                          className="group gap-x-1 text-medium text-foreground font-medium"
                          href="https://github.com/ollama/ollama/blob/main/docs/api.md"
                          rel="noreferrer noopener"
                        >
                          Ollama API 文档
                        </Link>
                        <p className="text-small text-default-500">
                          Ollama 原生 API 文档
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3 items-center">
                      <div className="flex items-center justify-center border-1 border-default-200/50 rounded-small w-11 h-11">
                        <BoolAtlasIcon className="w-6 h-6" />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <Link
                          isExternal
                          showAnchorIcon
                          anchorIcon={<LinkIcon />}
                          className="group gap-x-1 text-medium text-foreground font-medium"
                          href="https://github.com/ollama/ollama/blob/main/docs/openai.md"
                          rel="noreferrer noopener"
                        >
                          OpenAI 兼容 API 文档
                        </Link>
                        <p className="text-small text-default-500">
                          OpenAI 兼容 API 文档
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </DashboardLayout>
  );
};

export default ApiKeysPage;
