import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  Users, 
  Newspaper, 
  TrendingUp, 
  Trash2, 
  ExternalLink, 
  CheckCircle, 
  Clock, 
  User, 
  Phone, 
  Search,
  RefreshCw,
  Send
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('messages');
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState({ total_users: 0, total_news: 0, total_views: 0, total_messages: 0 });
  const [news, setNews] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState({});
  const [sendingReply, setSendingReply] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMessages = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/messages');
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/users');
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchNews = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/news');
      if (res.ok) {
        const data = await res.json();
        setNews(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    if (activeTab === 'messages') fetchMessages();
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'news') fetchNews();
    const interval = setInterval(() => {
      fetchStats();
      if (activeTab === 'messages') fetchMessages();
    }, 10000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const handleDeleteMessage = async (id) => {
    if (!confirm('آیا از حذف این پیام اطمینان دارید؟')) return;
    try {
      const res = await fetch(`/api/messages/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setMessages(messages.filter((m) => m.id !== id));
        fetchStats();
      }
    } catch (e) {
      alert('خطا در حذف پیام');
    }
  };

  const handleSendReply = async (msg) => {
    const text = replyText[msg.id];
    if (!text || !text.trim()) return;
    try {
      setSendingReply(msg.id);
      const res = await fetch(`/api/messages/${msg.id}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reply: text })
      });
      if (res.ok) {
        alert('پاسخ با موفقیت به تلگرام کاربر ارسال شد.');
        setReplyText({ ...replyText, [msg.id]: '' });
        fetchMessages();
      } else {
        alert('خطا در ارسال پاسخ');
      }
    } catch (e) {
      alert('خطا در اتصال به سرور');
    } finally {
      setSendingReply(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans" dir="rtl">
      {/* Top Navbar */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50 px-6 py-4 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 font-bold text-xl">
            🤖
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              پنل مدیریت اخبار هوش مصنوعی
            </h1>
            <p className="text-xs text-slate-400">سیستم مدیریت پیام‌ها و ربات تلگرام</p>
          </div>
        </div>

        <button 
          onClick={() => { fetchStats(); if (activeTab === 'messages') fetchMessages(); }} 
          className="flex items-center gap-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-lg transition border border-slate-700 active:scale-95 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          بروزرسانی زنده
        </button>
      </header>

      {/* Main Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-black">{stats.total_messages || messages.length}</div>
              <div className="text-xs text-slate-400">پیام‌های ارتباط با ما</div>
            </div>
          </div>

          <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-black">{stats.total_users}</div>
              <div className="text-xs text-slate-400">کاربران احراز هویت شده</div>
            </div>
          </div>

          <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Newspaper className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-black">{stats.total_news}</div>
              <div className="text-xs text-slate-400">اخبار اختصاصی ادمین</div>
            </div>
          </div>

          <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-black">{stats.total_views}</div>
              <div className="text-xs text-slate-400">بازدیدهای یکتا</div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 gap-2">
          <button
            onClick={() => setActiveTab('messages')}
            className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition cursor-pointer ${
              activeTab === 'messages'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            پیام‌های ارتباط با ما
            {messages.length > 0 && (
              <span className="bg-cyan-500/20 text-cyan-300 text-xs px-2 py-0.5 rounded-full font-bold">
                {messages.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition cursor-pointer ${
              activeTab === 'users'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-4 h-4" />
            لیست کاربران
          </button>

          <button
            onClick={() => setActiveTab('news')}
            className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition cursor-pointer ${
              activeTab === 'news'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Newspaper className="w-4 h-4" />
            اخبار ثبت‌شده
          </button>
        </div>

        {/* Content Section */}
        {activeTab === 'messages' && (
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-300">هنوز پیامی ثبت نشده است</h3>
                <p className="text-xs text-slate-500 mt-1">پیام‌هایی که کاربران از طریق دکمه «ارتباط با ما» ارسال کنند اینجا نمایش داده می‌شود.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {messages.map((msg) => (
                  <div key={msg.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400 font-bold">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-semibold text-sm text-slate-100 flex items-center gap-2">
                            {msg.full_name}
                            {msg.username && (
                              <span className="text-xs text-cyan-400 font-normal">@{msg.username}</span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                            {msg.phone && (
                              <span className="flex items-center gap-1">
                                <Phone className="w-3 h-3 text-slate-500" />
                                <span dir="ltr">{msg.phone}</span>
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-500" />
                              <span dir="ltr">{msg.created_at}</span>
                            </span>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteMessage(msg.id)}
                        className="text-slate-400 hover:text-red-400 p-2 rounded-lg hover:bg-red-500/10 transition cursor-pointer"
                        title="حذف پیام"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/60 whitespace-pre-wrap">
                      {msg.message}
                    </div>

                    {/* Reply Section */}
                    <div className="pt-2 flex flex-col sm:flex-row gap-2">
                      <input
                        type="text"
                        value={replyText[msg.id] || ''}
                        onChange={(e) => setReplyText({ ...replyText, [msg.id]: e.target.value })}
                        placeholder="پاسخ مستقیم به تلگرام این کاربر..."
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                      />
                      <button
                        onClick={() => handleSendReply(msg)}
                        disabled={sendingReply === msg.id || !replyText[msg.id]?.trim()}
                        className="flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs px-4 py-2 rounded-xl transition font-medium cursor-pointer"
                      >
                        <Send className="w-3.5 h-3.5" />
                        {sendingReply === msg.id ? 'در حال ارسال...' : 'ارسال پاسخ'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-right text-sm">
                <thead className="bg-slate-800/50 text-xs text-slate-400 uppercase border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-4">شناسه</th>
                    <th className="px-5 py-4">نام</th>
                    <th className="px-5 py-4">یوزرنیم</th>
                    <th className="px-5 py-4">شماره تلفن</th>
                    <th className="px-5 py-4">تاریخ ثبت‌نام</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="text-center py-8 text-slate-500">کاربری یافت نشد</td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.user_id} className="hover:bg-slate-800/30 transition">
                        <td className="px-5 py-4 text-xs font-mono text-slate-400">{u.user_id}</td>
                        <td className="px-5 py-4 font-medium text-slate-200">{u.first_name || '-'}</td>
                        <td className="px-5 py-4 text-cyan-400 text-xs">
                          {u.username ? `@${u.username}` : '-'}
                        </td>
                        <td className="px-5 py-4 text-xs font-mono text-slate-300" dir="ltr">
                          {u.phone || '-'}
                        </td>
                        <td className="px-5 py-4 text-xs text-slate-400" dir="ltr">{u.created_at}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'news' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {news.length === 0 ? (
              <div className="col-span-2 text-center py-16 bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-500">
                خبری ثبت نشده است
              </div>
            ) : (
              news.map((item) => (
                <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-xs text-cyan-400 mb-2">
                      <span>دسته: {item.category}</span>
                      <span className="text-slate-400">👁 {item.views || 0} بازدید</span>
                    </div>
                    <h4 className="font-semibold text-sm text-slate-100">{item.title}</h4>
                    {item.body && <p className="text-xs text-slate-400 mt-2 line-clamp-3">{item.body}</p>}
                  </div>
                  {item.link && (
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-400 hover:underline flex items-center gap-1 self-start"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      مشاهده لینک خبر
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
