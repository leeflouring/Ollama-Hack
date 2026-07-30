import { Input } from "@heroui/input";
import { useEffect, useRef, useState } from "react";

import { SearchIcon } from "./icons";

interface SearchInputProps {
  searchTerm: string;
  placeholder: string;
  setSearchTerm: (value: string) => void;
  handleSearch: (e: React.FormEvent) => void;
  autoSearchDelay?: number; // 自动搜索延迟（毫秒）
}

const SearchForm = ({
  placeholder,
  searchTerm,
  setSearchTerm,
  handleSearch,
  autoSearchDelay = 0, // 默认不自动搜索
}: SearchInputProps) => {
  const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 当外部的 searchTerm 改变时，更新本地的 searchTerm
  useEffect(() => {
    setLocalSearchTerm(searchTerm);
  }, [searchTerm]);

  useEffect(
    () => () => {
      if (searchTimer.current) {
        clearTimeout(searchTimer.current);
      }
    },
    [],
  );

  // 处理搜索输入变化并支持自动搜索
  const handleSearchChange = (value: string) => {
    setLocalSearchTerm(value);
    setSearchTerm(value);

    if (searchTimer.current) {
      clearTimeout(searchTimer.current);
    }

    // 如果设置了自动搜索延迟，启用防抖自动搜索
    if (autoSearchDelay > 0) {
      searchTimer.current = setTimeout(() => {
        searchTimer.current = null;
        const syntheticEvent = {
          preventDefault: () => {},
        } as React.FormEvent;

        handleSearch(syntheticEvent);
      }, autoSearchDelay);
    }
  };

  return (
    <form className="w-full sm:w-auto flex" onSubmit={handleSearch}>
      <Input
        isClearable
        className="mr-2"
        color="primary"
        placeholder={placeholder}
        startContent={
          <SearchIcon className="text-black/50 mb-0.5 dark:text-white/90 text-slate-400 pointer-events-none flex-shrink-0" />
        }
        value={localSearchTerm}
        variant="bordered"
        onChange={(e) => handleSearchChange(e.target.value)}
        onClear={() => {
          if (searchTimer.current) {
            clearTimeout(searchTimer.current);
            searchTimer.current = null;
          }
          setLocalSearchTerm("");
          setSearchTerm("");
        }}
      />
    </form>
  );
};

export default SearchForm;
