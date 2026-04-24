"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Search,
  Download,
  Users,
  Tags,
  History,
  Settings,
  Library,
  Star,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { name: '媒体库', icon: Library, href: '/library' },
  { name: '在线检索', icon: Search, href: '/search' },
  { name: '题材分类', icon: Tags, href: '/genres' },
  { name: '女优相册', icon: Users, href: '/actors' },
  { name: '下载任务', icon: Download, href: '/downloads' },
  { name: '我的订阅', icon: Star, href: '/favorites' },
  { name: '重复文件', icon: AlertCircle, href: '/duplicates' },
  { name: '系统日志', icon: History, href: '/logs' },
  { name: '核心设置', icon: Settings, href: '/settings' },
];

export const Sidebar = () => {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-screen w-60 bg-bg-base border-r border-border-subtle p-5 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-2 py-5">
        <div className="h-9 w-9 bg-accent rounded-xl flex items-center justify-center shadow-glow">
          <Library className="text-white h-5 w-5" />
        </div>
        <span className="text-xl font-bold tracking-tight text-white italic">JavHub</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto pr-1 custom-scrollbar">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (pathname === '/' && item.href === '/library');
          return (
            <Link key={item.name} href={item.href}>
              <div
                className={cn(
                  "relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-smooth",
                  isActive
                    ? "text-white bg-bg-surface"
                    : "text-zinc-500 hover:text-zinc-200 hover:bg-bg-hover"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute inset-0 bg-accent/10 rounded-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <item.icon className={cn(
                  "h-[18px] w-[18px] z-10",
                  isActive ? "text-accent" : "text-zinc-600"
                )} />
                <span className="z-10">{item.name}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="mt-auto pt-4 border-t border-border-subtle">
        <div className="flex items-center gap-3 px-2 py-3 rounded-xl hover:bg-bg-hover transition-smooth cursor-pointer">
          <div className="h-8 w-8 rounded-full bg-bg-surface border border-border-subtle" />
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-medium text-zinc-200 truncate">管理员</span>
            <span className="text-[10px] text-zinc-600 font-mono">v2.0 Next.js</span>
          </div>
        </div>
      </div>
    </div>
  );
};
