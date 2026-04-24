"use client";

import React, { useState, useEffect } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { Search, Users, Loader2, ImageOff, ArrowDownAZ, ArrowDownZA, SortAsc, User } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useDebounce } from '@/lib/hooks';

export default function ActorsPage() {
  const { ref, inView } = useInView();
  
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 500);
  const [sortBy, setSortBy] = useState('total_videos'); // 'actress_name' | 'total_videos'

  const fetchActors = async ({ pageParam = 1 }) => {
    // 调用我们库存的演员接口 (从 Emby 快照读取)
    const res: any = await api.get('/inventory/actors', { 
      params: { 
        page: pageParam, 
        page_size: 48,
        search: debouncedSearch || undefined,
        sort_by: sortBy,
        sort_order: sortBy === 'total_videos' ? 'desc' : 'asc'
      } 
    });
    return res;
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status
  } = useInfiniteQuery({
    queryKey: ['inventory-actors', debouncedSearch, sortBy],
    queryFn: fetchActors,
    initialPageParam: 1,
    getNextPageParam: (lastPage: any) => {
      const currentPage = lastPage.page || 1;
      const totalPages = lastPage.total_pages || 1;
      return currentPage < totalPages ? currentPage + 1 : undefined;
    },
  });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage, isFetchingNextPage]);

  const actors = data?.pages.flatMap((page: any) => page.data || []) || [];
  const total = data?.pages[0]?.total || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* 头部导航区域 */}
      <div className="sticky top-0 z-30 flex flex-col md:flex-row md:items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-indigo-500" />
            演员图鉴
          </h1>
          <p className="text-sm text-zinc-500 mt-1">您的 Emby 媒体库中共有 {total} 位演员。</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索演员..." 
              className="w-64 bg-white/5 border border-white/5 rounded-xl py-2 pl-10 pr-4 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:bg-white/10 transition-all placeholder:text-zinc-600"
            />
          </div>
          
          <button 
            onClick={() => setSortBy(prev => prev === 'total_videos' ? 'actress_name' : 'total_videos')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-sm font-medium text-zinc-300 hover:bg-white/10 transition-colors active:scale-95"
          >
            {sortBy === 'total_videos' ? <ArrowDownZA className="h-4 w-4" /> : <ArrowDownAZ className="h-4 w-4" />}
            <span className="hidden md:inline">{sortBy === 'total_videos' ? '按作品数量' : '按名称'}</span>
          </button>
        </div>
      </div>

      {/* 演员网格区域 */}
      <div className="flex-1 p-8">
        {status === 'pending' ? (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="flex flex-col items-center gap-3">
                <div className="h-28 w-28 bg-zinc-900 animate-pulse rounded-full" />
                <div className="h-4 w-20 bg-zinc-900 animate-pulse rounded" />
              </div>
            ))}
          </div>
        ) : actors.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-10">
            <Users className="h-12 w-12 opacity-30" />
            <p>未找到演员。</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">
            {actors.map((actor: any) => (
              <ActorCard key={actor.actress_id} actor={actor} />
            ))}
          </div>
        )}

        {/* 加载触发器 */}
        <div ref={ref} className="h-24 flex items-center justify-center mt-4">
          {isFetchingNextPage && (
            <div className="flex items-center gap-2 text-zinc-500 bg-white/5 px-4 py-2 rounded-full border border-white/5">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
              <span className="text-xs font-bold tracking-widest uppercase">加载更多...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const ActorCard = ({ actor }: { actor: any }) => {
  const [imgError, setImgError] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="group flex flex-col items-center gap-3 cursor-pointer"
    >
      <div className="relative">
        <div className="h-28 w-28 md:h-32 md:w-32 rounded-full overflow-hidden bg-zinc-800 border-4 border-zinc-900 shadow-xl transition-all duration-300 group-hover:border-indigo-500/50 group-hover:shadow-indigo-500/20 flex items-center justify-center">
          {actor.avatar_url && !imgError ? (
            <img 
              src={actor.avatar_url} 
              alt={actor.display_name} 
              onError={() => setImgError(true)}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
              loading="lazy"
            />
          ) : (
            <User className="h-10 w-10 text-zinc-600" strokeWidth={1.5} />
          )}
        </div>
        
        {/* 影片数量角标 */}
        {actor.total_videos > 0 && (
          <div className="absolute -bottom-1 -right-1 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full border-2 border-zinc-950 shadow-lg">
            {actor.total_videos}
          </div>
        )}
      </div>

      <div className="flex flex-col items-center">
        <span className="text-sm font-semibold text-zinc-200 group-hover:text-indigo-400 transition-colors line-clamp-1 text-center">
          {actor.display_name}
        </span>
        {actor.missing_count > 0 && (
          <span className="text-[10px] font-medium text-rose-400/80 mt-0.5 bg-rose-500/10 px-2 rounded-md">
            {actor.missing_count} 部缺失
          </span>
        )}
      </div>
    </motion.div>
  );
};
