import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";

// 定义 API 响应的基本结构
export interface ApiResponse<T = any> {
  data: T;
  success: boolean;
  message?: string;
}

// 扩展AxiosError接口以包含detail字段
export interface EnhancedAxiosError extends AxiosError {
  detail?: string;
}

// 将查询参数对象转换为URL查询字符串
export const buildQueryString = (params: Record<string, any>): string => {
  const query = Object.entries(params)
    .filter(
      ([_, value]) => value !== undefined && value !== null && value !== "",
    )
    .map(
      ([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(value)}`,
    )
    .join("&");

  return query ? `?${query}` : "";
};

export class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL = "") {
    this.client = axios.create({
      baseURL,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // 请求拦截器 - 添加认证 token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("auth_token");

        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
      },
      (error) => Promise.reject(error),
    );

    // 响应拦截器 - 处理错误和刷新 token
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & {
          _retry?: boolean;
        };

        // 处理错误响应中的detail字段
        if (error.response?.data) {
          const responseData = error.response.data;

          // 检查是否包含detail字段
          if (typeof responseData === "object" && "detail" in responseData) {
            const detail = responseData.detail;

            if (typeof detail === "string") {
              (error as EnhancedAxiosError).detail = detail;
            }
          }
        }

        // 处理 401 错误（未授权）
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          window.location.pathname !== "/init" &&
          window.location.pathname !== "/login"
        ) {
          // 如果需要实现 token 刷新，可以在这里添加逻辑
          // 当前简单实现：401 就清除 token 并跳转到登录页
          localStorage.removeItem("auth_token");
          window.location.href = "/login";

          return Promise.reject(error);
        }

        return Promise.reject(error);
      },
    );
  }

  // 通用 GET 请求
  public async get<T = any>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response: AxiosResponse = await this.client.get(url, config);

    return response.data;
  }

  // 通用 POST 请求
  public async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response: AxiosResponse = await this.client.post(url, data, config);

    return response.data;
  }

  // 通用 PUT 请求
  public async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response: AxiosResponse = await this.client.put(url, data, config);

    return response.data;
  }

  // 通用 PATCH 请求
  public async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response: AxiosResponse = await this.client.patch(url, data, config);

    return response.data;
  }

  // 通用 DELETE 请求
  public async delete<T = any>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    const response: AxiosResponse = await this.client.delete(url, config);

    return response.data;
  }
}
// 创建默认客户端实例
export const apiClient = new ApiClient(import.meta.env.VITE_API_BASE_URL);

export default apiClient;
