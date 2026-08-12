// 分页响应通用类型
export interface PageResponse<T> {
  items: T[];
  total?: number;
  page?: number;
  size?: number;
  pages?: number;
}

// API 请求通用参数
export interface PaginationParams {
  page?: number;
  size?: number;
}

// 排序方向枚举
export enum SortOrder {
  ASC = "asc",
  DESC = "desc",
}

// 通用查询参数接口
export interface QueryParams extends PaginationParams {
  search?: string;
  order_by?: string;
  order?: SortOrder;
  status?: EndpointStatusEnum;
  is_available?: boolean;
}

// API 错误响应
export interface ApiError {
  status: number;
  message: string;
  details?: unknown;
}

// API 状态枚举
export enum ApiStatus {
  IDLE = "idle",
  LOADING = "loading",
  SUCCESS = "success",
  ERROR = "error",
}

// 通用状态类型
export type ApiState<T> = {
  data: T | null;
  status: ApiStatus;
  error: ApiError | null;
};

// 枚举类型
export enum AIModelStatusEnum {
  AVAILABLE = "available",
  UNAVAILABLE = "unavailable",
  FAKE = "fake",
  MISSING = "missing",
}

export enum EndpointStatusEnum {
  AVAILABLE = "available",
  UNAVAILABLE = "unavailable",
  FAKE = "fake",
}

// 任务状态枚举
export enum TaskStatusEnum {
  PENDING = "pending",
  RUNNING = "running",
  DONE = "done",
  FAILED = "failed",
}
