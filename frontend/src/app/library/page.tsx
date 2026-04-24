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

  const { searchQuery, setSearchQuery } = useLibraryStore();
  const debouncedSearch = useDebounce(searchQuery, 500);

  const fetchVideos = async ({ pageParam = 1 }) => {
    const endpoint = '/api/v1/videos';
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
    queryKey: ['videos', debouncedSearch],
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

  const videos = data?.pages.flatMap((page: any) => page.data || []) || [];
  const total = data?.pages[0]?.total_count || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Toolbar */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-bg-base/80 backdrop-blur-md border-b border-border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Library</h1>
          <p className="text-sm text-zinc-500 mt-1">{total.toLocaleString()} titles</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search titles, actors..."
              className="w-64 bg-bg-surface border border-transparent rounded-xl py-2 pl-10 pr-8 text-sm text-white focus:outline-none focus:border-accent/50 transition-smooth"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
              >
                <XCircle className="h-4 w-4" />
              </button>
            )}
          </div>
          <button className="btn bg-bg-surface text-zinc-300 hover:bg-bg-hover">
            <Filter className="h-4 w-4" />
            Filter
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 p-8">
        {status === 'pending' ? (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="aspect-[2/3] w-full bg-bg-surface animate-pulse rounded-2xl" />
                <div className="h-4 w-3/4 bg-bg-surface animate-pulse rounded" />
                <div className="h-3 w-1/2 bg-bg-surface animate-pulse rounded" />
              </div>
            ))}
          </div>
        ) : videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <Search className="h-12 w-12 opacity-30" />
            <p>No results for "{searchQuery}"</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
            {videos.map((movie: Movie) => (
              <VideoCard
                key={movie.content_id}
                movie={movie}
                onClick={(m) => setSelectedMovie(m)}
              />
            ))}
          </div>
        )}

        {/* Infinite Scroll Trigger */}
        <div ref={ref} className="h-24 flex items-center justify-center mt-4">
          {isFetchingNextPage && (
            <div className="flex items-center gap-2 text-zinc-500 bg-bg-surface px-4 py-2 rounded-full">
              <Loader2 className="h-4 w-4 animate-spin text-accent" />
              <span className="text-xs font-medium uppercase tracking-widest">Loading</span>
            </div>
          )}
        </div>
      </div>

      <VideoDetailModal
        movie={selectedMovie}
        isOpen={!!selectedMovie}
        onClose={() => setSelectedMovie(null)}
      />
    </div>
  );
}
