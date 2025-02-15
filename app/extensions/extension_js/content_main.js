(() => {
    const stableNoise = <CLIENTRECT_NOISE>;
    
    let config = {
        "noise": {
            "DOMRect": stableNoise,
            "DOMRectReadOnly": stableNoise
        },
        "metrics": {
            "DOMRect": ['x', 'y', "width", "height"],
            "DOMRectReadOnly": ["top", "right", "bottom", "left"]
        },
        "method": {
            "DOMRect": function (e) {
                try {
                    Object.defineProperty(DOMRect.prototype, e, {
                        "get": new Proxy(Object.getOwnPropertyDescriptor(DOMRect.prototype, e).get, {
                            apply(target, self, args) {
                                const result = Reflect.apply(target, self, args);
                                const _result = result * (1 + (stableNoise < 0.5 ? -1 : +1) * config.noise.DOMRect);
                                return _result;
                            }
                        })
                    });
                } catch (e) {}
            },
            "DOMRectReadOnly": function (e) {
                try {
                    Object.defineProperty(DOMRectReadOnly.prototype, e, {
                        "get": new Proxy(Object.getOwnPropertyDescriptor(DOMRectReadOnly.prototype, e).get, {
                            apply(target, self, args) {
                                const result = Reflect.apply(target, self, args);
                                const _result = result * (1 + (stableNoise < 0.5 ? -1 : +1) * config.noise.DOMRectReadOnly);
                                return _result;
                            }
                        })
                    });
                } catch (e) {}
            }
        }
    };

    config.method.DOMRect(config.metrics.DOMRect.sort(() => 0.5 - stableNoise)[0]);
    config.method.DOMRectReadOnly(config.metrics.DOMRectReadOnly.sort(() => 0.5 - stableNoise)[0]);

    const mkey = "clientrects-defender-sandboxed-frame";
    document.documentElement.setAttribute(mkey, '');
    
    window.addEventListener("message", function (e) {
        if (e.data && e.data === mkey) {
            e.preventDefault();
            e.stopPropagation();
            
            try {
                if (e.source.DOMRect) {
                    const metrics = ['x', 'y', "width", "height"];
                    for (let i = 0; i < metrics.length; i++) {
                        Object.defineProperty(e.source.DOMRect.prototype, metrics[i], {
                            "get": Object.getOwnPropertyDescriptor(DOMRect.prototype, metrics[i]).get
                        });
                    }
                }
            } catch (e) {}
            
            try {
                if (e.source.DOMRectReadOnly) {
                    const metrics = ["top", "right", "bottom", "left"];
                    for (let i = 0; i < metrics.length; i++) {
                        Object.defineProperty(e.source.DOMRectReadOnly.prototype, metrics[i], {
                            "get": Object.getOwnPropertyDescriptor(DOMRectReadOnly.prototype, metrics[i]).get
                        });
                    }
                }
            } catch (e) {}
        }
    }, false);
})();