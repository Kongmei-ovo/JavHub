"use client";

import React, { useState, useEffect } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { Search, Loader2, XCircle, Globe, SlidersHorizontal, ChevronDown, ChevronUp, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { VideoCard } from '@/components/video/VideoCard';
import { VideoDetailModal } from '@/components/video/VideoDetailModal';
import { api } from '@/lib/api';
import type { Movie } from '@/types/jav';
import { useDebounce } from '@/lib/hooks';
import { cn } from '@/lib/utils';

interface SearchFilters {
  q: string;
  maker_name: string;
  actress_name: string;
  series_name: string;
  category_name: string; // Space separated tags
  year: string;
  service_code: string;
  sort_by: string;
}

const DEFAULT_FILTERS: SearchFilters = {
  q: '',
  maker_name: '',
  actress_name: '',
  series_name: '',
  category_name: '',
  year: '',
  service_code: '',
  sort_by: 'release_date:desc',
};

export default function SearchPage() {
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const { ref, inView } = useInView();
  
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS);
  
  // Tag input state
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // 800ms 防抖整个 filter 对象，避免频繁触发在线搜索
  const debouncedFilters = useDebounce(filters, 800);

  const fetchVideos = async ({ pageParam = 1 }) => {
    // 只要有任意过滤条件，就调用搜索接口；否则调用列表接口
    const hasSearchFilters = Boolean(
      debouncedFilters.q || 
      debouncedFilters.maker_name || 
      debouncedFilters.actress_name || 
      debouncedFilters.series_name || 
      debouncedFilters.category_name || 
      debouncedFilters.year || 
      debouncedFilters.service_code ||
      tags.length > 0
    );

    const endpoint = hasSearchFilters ? '/v1/videos/search' : '/v1/videos';
    
    // 构造请求参数
    const params: any = { 
      page: pageParam, 
      page_size: 48,
      sort_by: debouncedFilters.sort_by
    };

    if (hasSearchFilters) {
      if (debouncedFilters.q) params.q = debouncedFilters.q;
      if (debouncedFilters.maker_name) params.maker_name = debouncedFilters.maker_name;
      if (debouncedFilters.actress_name) params.actress_name = debouncedFilters.actress_name;
      if (debouncedFilters.series_name) params.series_name = debouncedFilters.series_name;
      if (debouncedFilters.year) params.year = debouncedFilters.year;
      if (debouncedFilters.service_code) params.service_code = debouncedFilters.service_code;
      
      const allTags = [...tags];
      if (allTags.length > 0) {
        params.category_name = allTags.join(' ');
      }
    }

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
    queryKey: ['online-search', debouncedFilters, tags],
    queryFn: fetchVideos,
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

  const handleFilterChange = (key: keyof SearchFilters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const newTag = tagInput.trim();
      if (newTag && !tags.includes(newTag)) {
        setTags([...tags, newTag]);
      }
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  const clearAllFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setTags([]);
    setTagInput('');
  };

  const videos = data?.pages.flatMap((page: any) => page.data || []) || [];
  const total = data?.pages[0]?.total_count || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* 头部与检索控制区 */}
      <div className="sticky top-0 z-30 flex flex-col px-8 py-6 bg-zinc-950/90 backdrop-blur-xl border-b border-white/5 gap-4">
        
        {/* Top Row: Title & Main Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Globe className="h-6 w-6 text-indigo-500" />
              在线检索库
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              找到 <span className="text-zinc-200 font-bold">{total}</span> 个在线检索结果。
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative group w-full md:w-80 lg:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
              <input 
                type="text" 
                value={filters.q}
                onChange={(e) => handleFilterChange('q', e.target.value)}
                placeholder="搜索番号或标题关键字..." 
                className="w-full bg-white/5 border border-white/5 rounded-xl py-2.5 pl-10 pr-8 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:bg-white/10 transition-all placeholder:text-zinc-600 shadow-inner"
              />
              {filters.q && (
                <button 
                  onClick={() => handleFilterChange('q', '')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  <XCircle className="h-4 w-4" />
                </button>
              )}
            </div>
            
            <button 
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all active:scale-95 shrink-0",
                showFilters 
                  ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400" 
                  : "bg-white/5 border-white/5 text-zinc-300 hover:bg-white/10"
              )}
            >
              <SlidersHorizontal className="h-4 w-4" />
              <span className="hidden sm:inline">高级筛选</span>
              {showFilters ? <ChevronUp className="h-3 w-3 opacity-50" /> : <ChevronDown className="h-3 w-3 opacity-50" />}
            </button>
          </div>
        </div>

        {/* Collapsible Advanced Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="pt-4 pb-2 border-t border-white/5 mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                
                {/* 演员 */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">女优名称</label>
                  <input 
                    type="text" value={filters.actress_name} onChange={(e) => handleFilterChange('actress_name', e.target.value)}
                    placeholder="例如: 三上悠亚" 
                    className="bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>

                {/* 制作商 */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">制作商 (Maker)</label>
                  <input 
                    type="text" value={filters.maker_name} onChange={(e) => handleFilterChange('maker_name', e.target.value)}
                    placeholder="例如: S1 NO.1 STYLE" 
                    className="bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>

                {/* 系列 */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">系列 (Series)</label>
                  <input 
                    type="text" value={filters.series_name} onChange={(e) => handleFilterChange('series_name', e.target.value)}
                    placeholder="输入系列名称" 
                    className="bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>

                {/* 年份与版本 */}
                <div className="flex gap-4">
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">年份</label>
                    <input 
                      type="number" value={filters.year} onChange={(e) => handleFilterChange('year', e.target.value)}
                      placeholder="YYYY" min="1900" max="2100"
                      className="bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">版本类型</label>
                    <select 
                      value={filters.service_code} onChange={(e) => handleFilterChange('service_code', e.target.value)}
                      className="bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none appearance-none"
                    >
                      <option value="">全部</option>
                      <option value="digital">数字版</option>
                      <option value="mono">单体版</option>
                      <option value="rental">租赁版</option>
                    </select>
                  </div>
                </div>

                {/* 标签/题材 (占两列) */}
                <div className="flex flex-col gap-1.5 lg:col-span-2">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">题材标签 (空格分隔输入)</label>
                  <div className="flex flex-wrap items-center gap-2 bg-zinc-900 border border-white/5 rounded-lg px-2 py-1.5 min-h-[38px] focus-within:ring-1 focus-within:ring-indigo-500 transition-shadow">
                    <AnimatePresence>
                      {tags.map(tag => (
                        <motion.span 
                          key={tag}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                          className="flex items-center gap-1 bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-md text-xs font-medium border border-indigo-500/20"
                        >
                          {tag}
                          <button onClick={() => removeTag(tag)} className="hover:text-white transition-colors">
                            <X className="h-3 w-3" />
                          </button>
                        </motion.span>
                      ))}
                    </AnimatePresence>
                    <input 
                      type="text" 
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={handleAddTag}
                      placeholder={tags.length === 0 ? "输入标签后按空格或回车添加..." : ""}
                      className="flex-1 bg-transparent text-sm text-zinc-200 outline-none min-w-[120px] px-1 placeholder:text-zinc-600"
                    />
                  </div>
                </div>

                {/* 排序方式 */}
                <div className="flex flex-col gap-1.5 lg:col-span-2">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">排序规则</label>
                  <div className="flex items-center gap-2">
                    <select 
                      value={filters.sort_by} onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                      className="flex-1 bg-zinc-900 border border-white/5 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:ring-1 focus:ring-indigo-500 outline-none appearance-none"
                    >
                      <option value="release_date:desc">发售日期 (最新)</option>
                      <option value="release_date:asc">发售日期 (最早)</option>
                      <option value="title_ja:asc">标题 (A-Z)</option>
                      <option value="title_ja:desc">标题 (Z-A)</option>
                      <option value="runtime_mins:desc">时长 (最长)</option>
                      <option value="random">随机推荐</option>
                    </select>

                    <button 
                      onClick={clearAllFilters}
                      className="px-4 py-2 bg-white/5 hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 rounded-lg text-sm font-medium transition-colors border border-transparent hover:border-rose-500/20"
                    >
                      重置条件
                    </button>
                  </div>
                </div>

              </div>
            </motion.div>
          )}
        </AnimatePresence>
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
            <Globe className="h-12 w-12 opacity-30" />
            <p>未找到符合条件的影片，请尝试调整检索条件。</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
            {videos.map((movie: Movie, idx: number) => (
              <VideoCard 
                key={`${movie.content_id}-${idx}`} 
                movie={movie} 
                onClick={(m) => setSelectedMovie(m)} 
              />
            ))}
          </div>
        )}

        {/* Infinite Load Trigger */}
        <div ref={ref} className="h-24 flex items-center justify-center mt-4">
          {isFetchingNextPage && (
            <div className="flex items-center gap-2 text-zinc-500 bg-white/5 px-4 py-2 rounded-full border border-white/5 shadow-lg">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
              <span className="text-xs font-bold tracking-widest uppercase">加载更多...</span>
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
