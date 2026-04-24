"use client";

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tags, Loader2, BarChart3 } from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import Link from 'next/link';

interface CategoryStat {
  id: number;
  name_en: string;
  name_ja: string;
  video_count: number;
}

export default function GenresPage() {
  const { data: genres = [], isLoading } = useQuery({
    queryKey: ['genres-stats'],
    queryFn: async () => {
      const res: any = await api.get('/v1/categories/stats');
      // 后端返回一个列表，或者 { data: ... }
      return Array.isArray(res) ? res : res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // 按视频数量降序排列
  const sortedGenres = [...genres].sort((a, b) => b.video_count - a.video_count);

  return (
    <div className="flex flex-col min-h-screen">
      {/* 头部 */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Tags className="h-6 w-6 text-indigo-500" />
            标签与分类
          </h1>
          <p className="text-sm text-zinc-500 mt-1">通过 {genres.length} 个不同的标签探索视频。</p>
        </div>
      </div>

      <div className="flex-1 p-8">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
            {Array.from({ length: 30 }).map((_, i) => (
              <div key={i} className="h-16 bg-zinc-900 animate-pulse rounded-xl" />
            ))}
          </div>
        ) : genres.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <Tags className="h-12 w-12 opacity-30" />
            <p>暂无分类标签。</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
            {sortedGenres.map((genre: CategoryStat) => (
              <Link key={genre.id} href={`/search?genre=${genre.name_ja}`}>
                <motion.div
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  whileHover={{ y: -2, scale: 1.02 }}
                  className="group flex items-center justify-between p-4 bg-zinc-900 border border-white/5 rounded-xl hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10 cursor-pointer transition-all"
                >
                  <span className="text-sm font-semibold text-zinc-300 group-hover:text-white truncate pr-2">
                    {genre.name_ja}
                  </span>
                  
                  <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-500 bg-zinc-950 px-2 py-1 rounded-md border border-white/5">
                    <BarChart3 className="h-3 w-3" />
                    <span>{genre.video_count}</span>
                  </div>
                </motion.div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
