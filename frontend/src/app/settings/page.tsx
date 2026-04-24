"use client";

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings, Save, Loader2, Server, Bell, Bot, Film } from 'lucide-react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<any>({});

  const { data, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: async () => {
      const res: any = await api.get('/v1/config');
      return res.data || {};
    },
  });

  useEffect(() => {
    if (data) {
      // 拍平配置，方便表单绑定
      setFormData({
        emby_api_url: data.emby?.api_url || '',
        emby_api_key: data.emby?.api_key || '',
        openlist_api_url: data.openlist?.api_url || '',
        openlist_username: data.openlist?.username || '',
        openlist_password: data.openlist?.password || '',
        openlist_default_path: data.openlist?.default_path || '',
        telegram_bot_token: data.telegram?.bot_token || '',
        telegram_allowed_users: (data.telegram?.allowed_user_ids || []).join(', '),
        notification_enabled: data.notification?.enabled || false,
        notification_telegram: data.notification?.telegram || false,
        crawler_request_interval: data.crawler?.request_interval || 3,
        scheduler_check_hour: data.scheduler?.subscription_check_hour || 2,
      });
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (newConfig: any) => api.put('/v1/config', newConfig),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      alert('设置保存成功！');
    },
    onError: () => {
      alert('保存设置失败。');
    }
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setFormData((prev: any) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...formData,
      telegram_allowed_users: formData.telegram_allowed_users
        ? formData.telegram_allowed_users.split(',').map((s: string) => s.trim()).filter(Boolean)
        : [],
      crawler_request_interval: Number(formData.crawler_request_interval),
      scheduler_check_hour: Number(formData.scheduler_check_hour),
    };
    saveMutation.mutate(payload);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Settings className="h-6 w-6 text-indigo-500" />
            核心设置
          </h1>
          <p className="text-sm text-zinc-500 mt-1">配置外部系统集成、消息通知及后台任务策略。</p>
        </div>
        
        <button 
          onClick={handleSubmit}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg shadow-indigo-500/20 active:scale-95 disabled:opacity-50"
        >
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          <span>保存修改</span>
        </button>
      </div>

      <div className="flex-1 p-8 max-w-4xl mx-auto w-full space-y-8">
        <form className="space-y-8" onSubmit={handleSubmit}>
          
          {/* Emby Section */}
          <Section icon={<Server />} title="Emby 媒体库集成" desc="连接本地或远程的 Emby 服务器。">
            <InputRow label="API 地址" name="emby_api_url" value={formData.emby_api_url} onChange={handleChange} placeholder="http://192.168.1.100:8096" />
            <InputRow label="API 密钥" name="emby_api_key" value={formData.emby_api_key} onChange={handleChange} type="password" placeholder="Emby API Key" />
          </Section>

          {/* OpenList Section */}
          <Section icon={<Server />} title="AList / OpenList 集成" desc="配置下载文件统一管理和存储目标路径。">
            <InputRow label="API 地址" name="openlist_api_url" value={formData.openlist_api_url} onChange={handleChange} placeholder="http://localhost:5244" />
            <div className="grid grid-cols-2 gap-4">
              <InputRow label="用户名" name="openlist_username" value={formData.openlist_username} onChange={handleChange} />
              <InputRow label="密码" name="openlist_password" value={formData.openlist_password} onChange={handleChange} type="password" />
            </div>
            <InputRow label="默认存储路径" name="openlist_default_path" value={formData.openlist_default_path} onChange={handleChange} placeholder="/downloads/AV" />
          </Section>

          {/* Telegram Section */}
          <Section icon={<Bot />} title="Telegram Bot" desc="配置用于远程控制与消息推送的 Bot。">
            <InputRow label="Bot 令牌 (Token)" name="telegram_bot_token" value={formData.telegram_bot_token} onChange={handleChange} type="password" />
            <InputRow label="允许访问的用户 IDs (以逗号分隔)" name="telegram_allowed_users" value={formData.telegram_allowed_users} onChange={handleChange} placeholder="123456789, 987654321" />
          </Section>

          {/* Notifications */}
          <Section icon={<Bell />} title="通知推送" desc="管理全局和各渠道的通知开关。">
            <div className="flex flex-col gap-3">
              <CheckboxRow label="启用全局通知推送" name="notification_enabled" checked={formData.notification_enabled} onChange={handleChange} />
              <CheckboxRow label="通过 Telegram 发送消息" name="notification_telegram" checked={formData.notification_telegram} onChange={handleChange} disabled={!formData.notification_enabled} />
            </div>
          </Section>

          {/* Scheduler & Crawler */}
          <Section icon={<Film />} title="高级爬虫与调度任务" desc="精细化调整刮削器频率和订阅检查周期。">
            <div className="grid grid-cols-2 gap-4">
              <InputRow label="爬虫请求延迟 (秒)" name="crawler_request_interval" value={formData.crawler_request_interval} onChange={handleChange} type="number" min="1" max="10" />
              <InputRow label="自动订阅检查触发时间 (0-23点)" name="scheduler_check_hour" value={formData.scheduler_check_hour} onChange={handleChange} type="number" min="0" max="23" />
            </div>
          </Section>

        </form>
      </div>
    </div>
  );
}

const Section = ({ icon, title, desc, children }: any) => (
  <section className="bg-zinc-900 border border-white/5 rounded-2xl p-6 shadow-xl">
    <div className="flex items-center gap-3 mb-6">
      <div className="p-2.5 bg-zinc-950 rounded-xl text-indigo-400 border border-white/5">{icon}</div>
      <div>
        <h2 className="text-lg font-bold text-zinc-100">{title}</h2>
        <p className="text-[13px] text-zinc-500">{desc}</p>
      </div>
    </div>
    <div className="space-y-4">
      {children}
    </div>
  </section>
);

const InputRow = ({ label, ...props }: any) => (
  <div className="flex flex-col gap-1.5">
    <label className="text-[13px] font-bold uppercase tracking-widest text-zinc-500">{label}</label>
    <input 
      {...props} 
      className="bg-zinc-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all disabled:opacity-50"
    />
  </div>
);

const CheckboxRow = ({ label, ...props }: any) => (
  <label className="flex items-center gap-3 cursor-pointer group">
    <div className="relative flex items-center justify-center">
      <input type="checkbox" {...props} className="peer sr-only" />
      <div className="w-10 h-5 bg-zinc-950 border border-white/10 rounded-full peer-checked:bg-indigo-600 transition-all peer-disabled:opacity-50" />
      <div className="absolute left-1 w-3 h-3 bg-zinc-400 rounded-full peer-checked:translate-x-5 peer-checked:bg-white transition-all shadow-md peer-disabled:opacity-50" />
    </div>
    <span className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">{label}</span>
  </label>
);
