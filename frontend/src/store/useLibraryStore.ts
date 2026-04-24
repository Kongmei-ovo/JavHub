import { create } from 'zustand';

interface LibraryState {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  // 可以添加更多的过滤条件，例如：maker_name, actress_name, sort_by 等
}

export const useLibraryStore = create<LibraryState>((set) => ({
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
