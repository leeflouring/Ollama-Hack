import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * 使用URL参数管理状态的Hook
 * @param param0 参数配置
 * @returns 状态和更新函数
 */
export function useUrlState<T>(
  initialState: T,
  options: {
    paramName: string;
    serialize?: (value: T) => string;
    deserialize?: (value: string) => T;
    replaceState?: boolean;
  },
) {
  const {
    paramName,
    serialize = JSON.stringify,
    deserialize = JSON.parse,
    replaceState = false,
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  // 从URL参数获取初始值，如果不存在则使用initialState
  const getInitialValue = useCallback(() => {
    const paramValue = searchParams.get(paramName);

    if (paramValue) {
      try {
        return deserialize(paramValue);
      } catch {
        return initialState;
      }
    }

    return initialState;
  }, [deserialize, initialState, paramName, searchParams]);

  const [state, setState] = useState<T>(getInitialValue);

  // 更新状态时同步到URL参数
  const updateState = useCallback(
    (newState: T | ((prevState: T) => T)) => {
      setState((prevState) => {
        const nextState =
          typeof newState === "function"
            ? (newState as (prevState: T) => T)(prevState)
            : newState;

        try {
          const serialized = serialize(nextState);

          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);

              if (serialized === serialize(initialState)) {
                next.delete(paramName);
              } else {
                next.set(paramName, serialized);
              }

              return next;
            },
            { replace: replaceState },
          );
        } catch {
          // 忽略错误
        }

        return nextState;
      });
    },
    [initialState, paramName, replaceState, serialize, setSearchParams],
  );

  // 当URL参数变化时更新状态
  useEffect(() => {
    const paramValue = searchParams.get(paramName);

    if (paramValue) {
      try {
        const parsedValue = deserialize(paramValue);

        setState(parsedValue);
      } catch {
        // 忽略错误
      }
    } else if (searchParams.toString() !== "") {
      // 只有当存在其他参数且当前参数不存在时，才重置为初始值
      setState(initialState);
    }
  }, [searchParams, paramName, deserialize, initialState]);

  return [state, updateState] as const;
}

/**
 * 分页参数验证配置接口
 */
export interface PaginationValidationConfig {
  // 页码验证
  page?: {
    min?: number; // 最小页码，默认为1
    max?: number; // 最大页码，如果提供了totalPages则会自动计算
  };
  // 每页条数验证
  pageSize?: {
    min?: number; // 最小每页条数
    max?: number; // 最大每页条数
  };
  // 排序字段验证
  orderBy?: {
    allowedFields?: string[]; // 允许的排序字段列表
    defaultField?: string; // 默认排序字段
  };
  // 总页数，用于页码回退功能
  totalPages?: number;
}

/**
 * 更通用的URL参数状态Hook，可以同时管理多个参数
 */
export function usePaginationUrlState<SortType = string>(
  initialState: {
    page?: number;
    pageSize?: number;
    search?: string;
    orderBy?: SortType;
    order?: string;
    isAvailable?: boolean;
    [key: string]: any;
  },
  validationConfig?: PaginationValidationConfig,
) {
  const [searchParams, setSearchParams] = useSearchParams();

  // 从URL获取初始状态
  const getInitialStateFromUrl = () => {
    const stateFromUrl = { ...initialState };

    // 解析页码
    const page = searchParams.get("page");

    if (page && !isNaN(Number(page))) {
      stateFromUrl.page = Number(page);
    }

    // 解析每页条数
    const pageSize = searchParams.get("pageSize");

    if (pageSize && !isNaN(Number(pageSize))) {
      stateFromUrl.pageSize = Number(pageSize);
    }

    // 解析搜索词
    const search = searchParams.get("search");

    if (search) {
      stateFromUrl.search = search;
    }

    // 解析排序字段
    const orderBy = searchParams.get("orderBy");

    if (orderBy) {
      if (validationConfig?.orderBy?.allowedFields?.includes(orderBy)) {
        stateFromUrl.orderBy = orderBy as SortType;
      } else {
        stateFromUrl.orderBy = validationConfig?.orderBy?.defaultField;
      }
    }

    // 解析排序方向
    const order = searchParams.get("order");

    if (order) {
      stateFromUrl.order = order;
    }

    // 处理其他自定义参数
    Object.keys(initialState).forEach((key) => {
      if (!["page", "pageSize", "search", "orderBy", "order"].includes(key)) {
        const value = searchParams.get(key);

        if (value) {
          try {
            stateFromUrl[key] = JSON.parse(value);
          } catch {
            stateFromUrl[key] = value;
          }
        }
      }
    });

    // 应用验证规则
    if (validationConfig) {
      // 验证页码
      if (validationConfig.page && typeof stateFromUrl.page === "number") {
        const { min = 1, max } = validationConfig.page;

        // 确保页码不小于最小值
        if (stateFromUrl.page < min) {
          stateFromUrl.page = min;
        }

        // 如果提供了最大值，确保页码不超过最大值
        if (max !== undefined && stateFromUrl.page > max) {
          stateFromUrl.page = max;
        }

        // 如果提供了总页数，确保页码不超过总页数
        if (
          validationConfig.totalPages !== undefined &&
          stateFromUrl.page > validationConfig.totalPages
        ) {
          stateFromUrl.page = Math.max(1, validationConfig.totalPages);
        }
      }

      // 验证每页条数
      if (
        validationConfig.pageSize &&
        typeof stateFromUrl.pageSize === "number"
      ) {
        const { min, max } = validationConfig.pageSize;

        // 应用最小值和最大值限制
        if (min !== undefined && stateFromUrl.pageSize < min) {
          stateFromUrl.pageSize = min;
        }
        if (max !== undefined && stateFromUrl.pageSize > max) {
          stateFromUrl.pageSize = max;
        }
      }
    }

    return stateFromUrl;
  };

  const [state, setState] = useState(getInitialStateFromUrl());

  // 验证并调整状态
  const validateState = useCallback(
    (newState: typeof state) => {
      if (!validationConfig) return newState;

      const validatedState = { ...newState };

      // 验证页码
      if (validationConfig.page && typeof validatedState.page === "number") {
        const { min = 1, max } = validationConfig.page;

        // 确保页码不小于最小值
        if (validatedState.page < min) {
          validatedState.page = min;
        }

        // 如果提供了最大值，确保页码不超过最大值
        if (max !== undefined && validatedState.page > max) {
          validatedState.page = max;
        }

        // 如果提供了总页数，确保页码不超过总页数
        if (
          validationConfig.totalPages !== undefined &&
          validatedState.page > validationConfig.totalPages
        ) {
          validatedState.page = Math.max(1, validationConfig.totalPages);
        }
      }

      // 验证每页条数
      if (
        validationConfig.pageSize &&
        typeof validatedState.pageSize === "number"
      ) {
        const { min, max } = validationConfig.pageSize;

        // 应用最小值和最大值限制
        if (min !== undefined && validatedState.pageSize < min) {
          validatedState.pageSize = min;
        }
        if (max !== undefined && validatedState.pageSize > max) {
          validatedState.pageSize = max;
        }
      }

      return validatedState;
    },
    [validationConfig],
  );

  // 状态变化时更新URL
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);

    // 处理所有状态参数
    Object.entries(state).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        newParams.delete(key);
      } else if (typeof value === "object") {
        newParams.set(key, JSON.stringify(value));
      } else {
        newParams.set(key, String(value));
      }
    });

    setSearchParams(newParams);
  }, [state, setSearchParams]);

  // 当URL参数变化时更新状态
  useEffect(() => {
    setState(getInitialStateFromUrl());
  }, [searchParams]);

  // 当totalPages变化时检查页码是否需要回退
  useEffect(() => {
    if (
      validationConfig?.totalPages !== undefined &&
      typeof state.page === "number"
    ) {
      if (state.page > validationConfig.totalPages) {
        setState((prev) => ({
          ...prev,
          page: Math.max(1, validationConfig.totalPages!),
        }));
      }
    }
  }, [validationConfig?.totalPages, state.page]);

  // 提供更新各个状态的专用方法
  const setPage = useCallback(
    (page: number) => {
      setState((prev) => {
        const newState = { ...prev, page };

        return validateState(newState);
      });
    },
    [validateState],
  );

  const setPageSize = useCallback(
    (pageSize: number) => {
      setState((prev) => {
        const newState = { ...prev, pageSize, page: 1 }; // 重置到第一页

        return validateState(newState);
      });
    },
    [validateState],
  );

  const setSearch = useCallback(
    (search: string) => {
      setState((prev) => {
        const newState = { ...prev, search, page: 1 }; // 重置到第一页

        return validateState(newState);
      });
    },
    [validateState],
  );

  const setOrderBy = useCallback(
    (orderBy: SortType) => {
      setState((prev) => {
        const newState = { ...prev, orderBy };

        return validateState(newState);
      });
    },
    [validateState],
  );

  const setOrder = useCallback(
    (order: string) => {
      setState((prev) => {
        const newState = { ...prev, order };

        return validateState(newState);
      });
    },
    [validateState],
  );

  const setCustomParam = useCallback(
    (key: string, value: any) => {
      setState((prev) => {
        const newState = { ...prev, [key]: value };

        return validateState(newState);
      });
    },
    [validateState],
  );

  return {
    ...state,
    setState: useCallback(
      (newState: typeof state) => {
        setState(validateState(newState));
      },
      [validateState],
    ),
    setPage,
    setPageSize,
    setSearch,
    setOrderBy,
    setOrder,
    setCustomParam,
  };
}

export default useUrlState;
