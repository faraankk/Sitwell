/**
 * Global Toast Notification System
 * Include this file in your base template to use showToast() anywhere
 */

(function () {
    // Create toast container if it doesn't exist
    function getOrCreateContainer() {
        let container = document.getElementById('global-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'global-toast-container';
            container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
            document.body.appendChild(container);
        }
        return container;
    }

    // Toast styles for different types
    const toastStyles = {
        success: { bg: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', icon: '✓', color: '#fff' },
        error: { bg: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', icon: '✕', color: '#fff' },
        warning: { bg: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', icon: '⚠', color: '#fff' },
        info: { bg: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', icon: 'ℹ', color: '#fff' }
    };

    // Main toast function
    window.showToast = function (message, type = 'info', duration = 4000) {
        const container = getOrCreateContainer();
        const style = toastStyles[type] || toastStyles.info;

        const toast = document.createElement('div');
        toast.style.cssText = `
      background: ${style.bg};
      color: ${style.color};
      padding: 14px 20px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 280px;
      max-width: 400px;
      pointer-events: auto;
      animation: toastSlideIn 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
      transform-origin: top right;
    `;

        toast.innerHTML = `
      <span style="width:24px;height:24px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:14px;">${style.icon}</span>
      <span style="flex:1;line-height:1.4;">${message}</span>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:inherit;cursor:pointer;opacity:0.7;font-size:18px;padding:0;margin-left:8px;">&times;</button>
    `;

        container.appendChild(toast);

        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.style.animation = 'toastSlideOut 0.3s ease-in forwards';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    };

    // Add animation styles
    if (!document.getElementById('toast-animation-styles')) {
        const styleSheet = document.createElement('style');
        styleSheet.id = 'toast-animation-styles';
        styleSheet.textContent = `
      @keyframes toastSlideIn {
        from { opacity: 0; transform: translateX(100%) scale(0.8); }
        to { opacity: 1; transform: translateX(0) scale(1); }
      }
      @keyframes toastSlideOut {
        from { opacity: 1; transform: translateX(0) scale(1); }
        to { opacity: 0; transform: translateX(100%) scale(0.8); }
      }
    `;
        document.head.appendChild(styleSheet);
    }
})();
