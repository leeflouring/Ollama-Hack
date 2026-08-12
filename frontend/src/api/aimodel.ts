import apiClient, { buildQueryString } from "./client";

import {
  AIModelInfoWithEndpoint,
  AIModelInfoWithEndpointCount,
  PageResponse,
  QueryParams,
} from "@/types";

export const aiModelApi = {
  // 获取所有 AI 模型（带最近性能测试）
  getAIModels: (params: QueryParams = {}) => {
    const queryString = buildQueryString({
      page: params.page || 1,
      size: params.size || 50,
      search: params.search,
      order_by: params.order_by,
      order: params.order,
      is_available: params.is_available,
    });

    return apiClient.get<PageResponse<AIModelInfoWithEndpointCount>>(
      `/api/v2/ai_model/${queryString}`,
    );
  },

  // 获取单个 AI 模型详情（包含端点）
  getAIModelById: (
    modelId: number,
    page: number = 1,
    size: number = 50,
    minTps?: number,
  ) => {
    return apiClient.get<AIModelInfoWithEndpoint>(
      `/api/v2/ai_model/${modelId}${buildQueryString({
        page,
        size,
        min_tps: minTps,
      })}`,
    );
  },
};

export default aiModelApi;
