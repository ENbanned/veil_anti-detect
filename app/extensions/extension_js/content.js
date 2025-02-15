
(() => {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    document.documentElement.appendChild(script);
})();
