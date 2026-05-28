import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import axios from 'axios';
import {
  Bell, Check, CheckCheck, X, Clock, Shield, Users, FileText,
  AlertTriangle, Store, Send, UserCheck
} from 'lucide-react';

const ICON_MAP = {
  marketplace: Store,
  enrollment: UserCheck,
  plan: Shield,
  exception: AlertTriangle,
  assignment: Users,
  irs: FileText,
  system: Bell,
};

function timeAgo(dateStr) {
  const now = new Date();
  const d = new Date(dateStr);
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString();
}

export default function NotificationBell() {
  const { token, API } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = useCallback(async () => {
    if (!token) return;
    try {
      const res = await axios.get(`${API}/notifications`, { headers });
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (err) {
      // silently fail
    }
  }, [API, token]);

  // Initial load + polling every 30 seconds
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const markAsRead = async (notifId) => {
    try {
      await axios.put(`${API}/notifications/${notifId}/read`, {}, { headers });
      setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {}
  };

  const markAllAsRead = async () => {
    try {
      await axios.put(`${API}/notifications/read-all`, {}, { headers });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {}
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => { setOpen(!open); if (!open) fetchNotifications(); }}
        className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
        data-testid="notification-bell"
      >
        <Bell className="w-5 h-5 text-slate-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-1 animate-in zoom-in-50" data-testid="unread-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 bottom-full mb-2 w-[380px] bg-white rounded-xl shadow-xl border border-slate-200 z-50 animate-in fade-in-0 slide-in-from-bottom-2 duration-200" data-testid="notification-dropdown">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold font-[Manrope]">Notifications</h3>
              {unreadCount > 0 && (
                <Badge className="bg-red-100 text-red-700 border-0 text-[10px] font-bold">{unreadCount} new</Badge>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold transition-colors flex items-center gap-1"
                data-testid="mark-all-read"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-12 text-center">
                <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No notifications yet</p>
              </div>
            ) : (
              notifications.map(notif => {
                const IconComp = ICON_MAP[notif.category] || ICON_MAP[notif.type] || Bell;
                return (
                  <div
                    key={notif.id}
                    className={`flex items-start gap-3 px-4 py-3 border-b border-slate-50 transition-colors hover:bg-slate-50/80 ${!notif.read ? 'bg-indigo-50/40' : ''}`}
                    data-testid={`notif-${notif.id}`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${!notif.read ? 'bg-indigo-100' : 'bg-slate-100'}`}>
                      <IconComp className={`w-4 h-4 ${!notif.read ? 'text-indigo-600' : 'text-slate-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs leading-relaxed ${!notif.read ? 'text-slate-900 font-semibold' : 'text-slate-600'}`}>
                        {notif.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{notif.message}</p>
                      <p className="text-[10px] text-slate-300 mt-1 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" /> {timeAgo(notif.created_at)}
                      </p>
                    </div>
                    {!notif.read && (
                      <button
                        onClick={(e) => { e.stopPropagation(); markAsRead(notif.id); }}
                        className="p-1 rounded hover:bg-slate-200 transition-colors flex-shrink-0"
                        title="Mark as read"
                      >
                        <Check className="w-3.5 h-3.5 text-slate-400" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2.5 border-t border-slate-100 text-center">
              <p className="text-[10px] text-slate-400">{notifications.length} notification{notifications.length !== 1 ? 's' : ''}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
