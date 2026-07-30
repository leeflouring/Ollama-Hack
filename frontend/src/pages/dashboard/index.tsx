import { Card } from "@heroui/card";
import { Progress } from "@heroui/progress";

import { useAuth } from "@/contexts/AuthContext";
import { useCustomQuery } from "@/hooks";
import { endpointApi, aiModelApi, planApi } from "@/api";
import {
  PageResponse,
  EndpointWithAIModelCount,
  AIModelInfoWithEndpointCount,
  PlanResponse,
  ApiError,
} from "@/types";
import DashboardLayout from "@/layouts/Main";
import ErrorDisplay from "@/components/ErrorDisplay";

const DashboardPage = () => {
  const { user } = useAuth();

  // 获取用户当前计划
  const {
    data: userPlan,
    isLoading: isLoadingPlan,
    error: planError,
  } = useCustomQuery<PlanResponse>(
    ["plan", "current"],
    () => planApi.getCurrentUserPlan(),
    { enabled: !!user },
  );

  // 管理员统计信息
  // const {
  //   data: users,
  //   isLoading: isLoadingUsers,
  //   error: usersError,
  // } = useCustomQuery<PageResponse<UserInfo>>(
  //   ["users", "stats"],
  //   () =>
  //     authApi.getUsers({
  //       page: 1,
  //       size: 1,
  //     }),
  //   { enabled: !!isAdmin },
  // );

  const {
    data: endpoints,
    isLoading: isLoadingEndpoints,
    error: endpointsError,
  } = useCustomQuery<PageResponse<EndpointWithAIModelCount>>(
    ["endpoints", "stats"],
    () =>
      endpointApi.getEndpoints({
        page: 1,
        size: 1,
      }),
    { enabled: true },
  );

  const {
    data: availableEndpoints,
    isLoading: isLoadingAvailableEndpoints,
    error: availableEndpointsError,
  } = useCustomQuery<PageResponse<EndpointWithAIModelCount>>(
    ["endpoints", "stats", "available"],
    () =>
      endpointApi.getEndpoints({
        page: 1,
        size: 1,
        status: "available",
      }),
    { enabled: true },
  );

  const {
    data: models,
    isLoading: isLoadingModels,
    error: modelsError,
  } = useCustomQuery<PageResponse<AIModelInfoWithEndpointCount>>(
    ["models", "stats"],
    () =>
      aiModelApi.getAIModels({
        page: 1,
        size: 1,
      }),
    { enabled: true },
  );

  const {
    data: availableModels,
    isLoading: isLoadingAvailableModels,
    error: availableModelsError,
  } = useCustomQuery<PageResponse<AIModelInfoWithEndpointCount>>(
    ["models", "stats", "available"],
    () =>
      aiModelApi.getAIModels({
        page: 1,
        size: 1,
        is_available: true,
      }),
    { enabled: true },
  );

  const isLoading =
    isLoadingPlan ||
    // (isAdmin && isLoadingUsers) ||
    isLoadingEndpoints ||
    isLoadingModels ||
    isLoadingAvailableEndpoints ||
    isLoadingAvailableModels;
  const error =
    planError ||
    // (isAdmin && usersError) ||
    endpointsError ||
    modelsError ||
    availableEndpointsError ||
    availableModelsError;

  // 创建用于 ErrorDisplay 的 Error 对象
  const getErrorForDisplay = () => {
    if (!error) return null;

    // 将 ApiError 转换为 Error 对象
    return new Error((error as ApiError)?.message || "发生了一个错误");
  };

  if (isLoading) {
    return (
      <DashboardLayout current_root_href="/">
        <div aria-busy="true" aria-label="正在加载控制台" className="space-y-6">
          <div className="h-48 animate-pulse rounded-[2rem] bg-default-200/60" />
          <div className="grid gap-6 md:grid-cols-2">
            <div className="h-56 animate-pulse rounded-3xl bg-default-200/60" />
            <div className="h-56 animate-pulse rounded-3xl bg-default-200/60" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout current_root_href="/">
      {error && <ErrorDisplay error={getErrorForDisplay()} />}

      <section
        aria-labelledby="dashboard-title"
        className="relative mb-8 overflow-hidden rounded-[2rem] border border-default-200/70 bg-content1/70 px-6 py-9 shadow-none backdrop-blur-sm sm:px-10 sm:py-12"
      >
        <div className="absolute -right-16 -top-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative max-w-2xl">
          <p className="mb-3 text-sm font-semibold tracking-[0.16em] text-primary">
            运行概览
          </p>
          <h1
            className="text-balance text-3xl font-semibold tracking-[-0.04em] sm:text-5xl"
            id="dashboard-title"
          >
            你好，{user?.username}
          </h1>
          <p className="mt-4 max-w-xl text-pretty leading-7 text-default-500">
            在一个控制台内查看 Ollama 端点健康状态、模型可用性和当前请求配额。
          </p>
        </div>
      </section>

      {/* 统计卡片 */}
      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card className="surface-panel rounded-3xl p-7">
          <div className="mb-8 flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-default-500">端点</p>
              <p className="metric-number mt-2 text-5xl font-semibold">
                {endpoints?.total || 0}
              </p>
            </div>
            <span className="rounded-xl bg-primary/10 px-3 py-2 text-xs font-semibold text-primary">
              ENDPOINTS
            </span>
          </div>
          <p className="mb-3 text-sm font-medium text-default-500">
            已添加的端点总数
          </p>
          <div className="flex flex-col justify-center gap-3">
            <Progress
              aria-label="可用端点比例"
              color="primary"
              formatOptions={{ style: "percent", maximumFractionDigits: 0 }}
              maxValue={100}
              value={
                endpoints?.total
                  ? ((availableEndpoints?.total || 0) / endpoints.total) * 100
                  : 0
              }
            />
            <div className="flex flex-row justify-between gap-2">
              <span className="text-sm font-medium text-default-500">
                可用端点
              </span>
              <span className="tabular-nums text-sm font-semibold">
                {availableEndpoints?.total || 0} / {endpoints?.total || 0}
              </span>
            </div>
          </div>
        </Card>

        <Card className="surface-panel rounded-3xl p-7 md:translate-y-4">
          <div className="mb-8 flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-default-500">AI 模型</p>
              <p className="metric-number mt-2 text-5xl font-semibold">
                {models?.total || 0}
              </p>
            </div>
            <span className="rounded-xl bg-primary/10 px-3 py-2 text-xs font-semibold text-primary">
              MODELS
            </span>
          </div>
          <p className="mb-3 text-sm font-medium text-default-500">
            扫描出的 AI 模型总数
          </p>
          <div className="flex flex-col justify-center gap-3">
            <Progress
              aria-label="可用 AI 模型比例"
              color="primary"
              formatOptions={{ style: "percent", maximumFractionDigits: 0 }}
              maxValue={100}
              value={
                models?.total
                  ? ((availableModels?.total || 0) / models.total) * 100
                  : 0
              }
            />
            <div className="flex flex-row justify-between gap-2">
              <span className="text-sm font-medium text-default-500">
                可用 AI 模型
              </span>
              <span className="tabular-nums text-sm font-semibold">
                {availableModels?.total || 0} / {models?.total || 0}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* 当前计划 */}
      {userPlan && (
        <section
          aria-labelledby="plan-title"
          className="surface-panel grid gap-8 rounded-3xl p-7 md:grid-cols-[1.2fr_1fr] md:p-9"
        >
          <div>
            <p className="text-sm font-semibold text-primary">当前计划</p>
            <h2
              className="mt-2 text-2xl font-semibold tracking-tight"
              id="plan-title"
            >
              {userPlan.name}
            </h2>
            <p className="mt-3 max-w-xl text-pretty leading-7 text-default-500">
              {userPlan.description || "此计划定义了当前账号的请求速率上限。"}
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-default-100/70 p-4">
              <dt className="text-sm text-default-500">每分钟请求</dt>
              <dd className="metric-number mt-2 text-2xl font-semibold">
                {userPlan.rpm}
              </dd>
            </div>
            <div className="rounded-2xl bg-default-100/70 p-4">
              <dt className="text-sm text-default-500">每天请求</dt>
              <dd className="metric-number mt-2 text-2xl font-semibold">
                {userPlan.rpd}
              </dd>
            </div>
          </dl>
        </section>
      )}
    </DashboardLayout>
  );
};

export default DashboardPage;
