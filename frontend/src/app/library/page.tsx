"use client";

import React, { useState, useEffect } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { Search, Filter, Loader2, XCircle } from 'lucide-react';
import { VideoCard } from '@/components/video/VideoCard';
import { VideoDetailModal } from '@/components/video/VideoDetailModal';
import { api } from '@/lib/api';
import type { Movie } from '@/types/jav';
import { useLibraryStore } from '@/store/useLibraryStore';
import { useDebounce } from '@/lib/hooks';

export default function LibraryPage() {
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const { ref, inView } = useInView();
  
  // Zustand State
  const { searchQuery, setSearchQuery } = useLibraryStore();
  const debouncedSearch = useDebounce(searchQuery, 500);

  const fetchVideos = async ({ pageParam = 1 }) => {
    // 调用库存接口 (Emby 库中的内容)
    const endpoint = '/inventory/videos';
    const params = debouncedSearch 
      ? { search: debouncedSearch, page: pageParam, page_size: 48 }
      : { page: pageParam, page_size: 48 };

    const res: any = await api.get(endpoint, { params });
    return res;
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status
  } = useInfiniteQuery({
    queryKey: ['videos', debouncedSearch], // 搜索词改变时重置并重新 fetch
    queryFn: fetchVideos,
    initialPageParam: 1,
    getNextPageParam: (lastPage: any) => {
      // 后端返回的数据中通常包含当前页和总页数
      const currentPage = lastPage.page || 1;
      const totalPages = lastPage.total_pages || 1;
      return currentPage < totalPages ? currentPage + 1 : undefined;
    },
  });

  // 监听滚动到底部
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage, isFetchingNextPage]);

  // 提取视频列表和总数
  const videos = data?.pages.flatMap((page: any) => page.data || []) || [];
  const total = data?.pages[0]?.total_count || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Sub-Header / Toolbar */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Library</h1>
          <p className="text-sm text-zinc-500 mt-1">Explore your collection of {total} titles.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search content, actors..." 
              className="w-64 bg-white/5 border border-white/5 rounded-xl py-2 pl-10 pr-8 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:bg-white/10 transition-all placeholder:text-zinc-600"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <XCircle className="h-4 w-4" />
              </button>
            )}
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-sm font-medium text-zinc-300 hover:bg-white/10 transition-colors cursor-pointer active:scale-95">
            <Filter className="h-4 w-4" />
            <span>Filter</span>
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="flex-1 p-8">
        {status === 'pending' ? (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-3">
                <div className="aspect-[2/3] w-full bg-zinc-900 animate-pulse rounded-2xl" />
                <div className="h-4 w-3/4 bg-zinc-900 animate-pulse rounded" />
                <div className="h-3 w-1/2 bg-zinc-900 animate-pulse rounded" />
              </div>
            ))}
          </div>
        ) : videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <Search className="h-12 w-12 opacity-30" />
            <p>未找到“{searchQuery}”的相关结果。</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
            {videos.map((movie: Movie) => (
              <VideoCard 
                key={movie.content_id} 
                movie={movie} 
                onClick={(m) => setSelectedMovie(m)} 
              />
            ))}
          </div>
        )}

        {/* Infinite Load Trigger */}
        <div ref={ref} className="h-24 flex items-center justify-center mt-4">
          {isFetchingNextPage && (
            <div className="flex items-center gap-2 text-zinc-500 bg-white/5 px-4 py-2 rounded-full border border-white/5">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
              <span className="text-xs font-bold tracking-widest uppercase">Loading More...</span>
            </div>
          )}
        </div>
      </div>

      {/* Global Detail Modal */}
      <VideoDetailModal 
        movie={selectedMovie} 
        isOpen={!!selectedMovie} 
        onClose={() => setSelectedMovie(null)} 
      />
    </div>
  );
}
