


(() => {
    console.log("Injected script started");
    // ========== 0) hardwareProfile  ==========
    console.log("Setting up hardwareProfile and geoLocation");
    const hardwareProfile = <HARDWARE_PROFILE>;
    const browserLang = "<browser_language>";

    // ========== 1) Настройки ==========
    const MAX_FINGERPRINT_CANVAS_WIDTH = 300;
    const MAX_FINGERPRINT_CANVAS_HEIGHT = 100;

    const FIXED_CANVAS_DATAURL = "<CANVAS_DATA_URL>";

    function isFingerprintCanvas(canvas) {
        return (canvas.width <= MAX_FINGERPRINT_CANVAS_WIDTH
            && canvas.height <= MAX_FINGERPRINT_CANVAS_HEIGHT);
    }

    function getSpoofedDataURL(canvas) {
        return FIXED_CANVAS_DATAURL;
    }

    function dataURLToBlob(dataurl) {
        const arr = dataurl.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while(n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new Blob([u8arr], { type: mime });
    }

    // ========== 2) ОРИГИНАЛЬНЫЕ дескрипторы ==========
    const HTMLCanvasProto = HTMLCanvasElement.prototype;

    const descToDataURL = Object.getOwnPropertyDescriptor(HTMLCanvasProto, 'toDataURL');
    const descToBlob = Object.getOwnPropertyDescriptor(HTMLCanvasProto, 'toBlob');
    const descGetContext = Object.getOwnPropertyDescriptor(HTMLCanvasProto, 'getContext');

    let OffscreenCanvasProto = null;
    let descOffscreenGetContext = null;
    if (typeof OffscreenCanvas !== 'undefined') {
        OffscreenCanvasProto = OffscreenCanvas.prototype;
        descOffscreenGetContext = Object.getOwnPropertyDescriptor(OffscreenCanvasProto, 'getContext');
    }

    // ========== 3) Новые функции ==========

    function newToDataURL(...args) {
        if (isFingerprintCanvas(this)) {
            return getSpoofedDataURL(this);
        }
        return descToDataURL.value.apply(this, args);
    }
    try {
        Object.defineProperty(newToDataURL, 'toString', {
            value: function() { return 'function toDataURL() { [native code] }'; },
            writable: false,
            configurable: false
        });
    } catch(e) {}

    // --- 3.2) toBlob ---
    let newToBlob = null;
    if (descToBlob && typeof descToBlob.value === 'function') {
        newToBlob = function(callback, ...args) {
            if (isFingerprintCanvas(this)) {
                const dataURL = getSpoofedDataURL(this);
                const blob = dataURLToBlob(dataURL);
                setTimeout(() => callback(blob), 0);
                return;
            }
            return descToBlob.value.apply(this, [callback, ...args]);
        };
        try {
            Object.defineProperty(newToBlob, 'toString', {
                value: function() { return 'function toBlob() { [native code] }'; },
                writable: false,
                configurable: false
            });
        } catch(e) {}
    }

    // --- 3.3) getContext ---
    function newGetContext(type, options) {
        const ctx = descGetContext.value.apply(this, [type, options]);

        if (ctx && type === '2d' && isFingerprintCanvas(this) && !ctx.__patched) {
            const origGetImageData = ctx.getImageData;
            ctx.getImageData = function(sx, sy, sw, sh) {
                if (this.canvas && this.canvas.__bypassSpoof) {
                    return origGetImageData.call(this, sx, sy, sw, sh);
                }
                if (sx === 0 && sy === 0 &&
                    sw === this.canvas.width && sh === this.canvas.height) {
                    const offscreen = document.createElement("canvas");
                    offscreen.width = this.canvas.width;
                    offscreen.height = this.canvas.height;
                    offscreen.__bypassSpoof = true;

                    const offCtx = offscreen.getContext("2d");
                    const img = new Image();
                    img.src = getSpoofedDataURL(this.canvas);

                    if (img.complete) {
                        offCtx.drawImage(img, 0, 0);
                        return offCtx.getImageData(0, 0, offscreen.width, offscreen.height);
                    }
                }
                return origGetImageData.call(this, sx, sy, sw, sh);
            };
            try {
                Object.defineProperty(ctx.getImageData, 'toString', {
                    value: function() { return 'function getImageData() { [native code] }'; },
                    writable: false,
                    configurable: false
                });
            } catch(e) {}

            ctx.__patched = true;
        }
        return ctx;
    }
    try {
        Object.defineProperty(newGetContext, 'toString', {
            value: function() { return 'function getContext() { [native code] }'; },
            writable: false,
            configurable: false
        });
    } catch(e) {}

    // ========== 4) HTMLCanvasElement ==========

    Object.defineProperty(HTMLCanvasProto, 'toDataURL', {
        ...descToDataURL,
        value: newToDataURL
    });

    // --- toBlob ---
    if (newToBlob) {
        Object.defineProperty(HTMLCanvasProto, 'toBlob', {
            ...descToBlob,
            value: newToBlob
        });
    }

    // --- getContext ---
    Object.defineProperty(HTMLCanvasProto, 'getContext', {
        ...descGetContext,
        value: newGetContext
    });

    // ========== 5) OffscreenCanvas ==========

    if (OffscreenCanvasProto && descOffscreenGetContext) {

        function newOffscreenGetContext(type, options) {
            const ctx = descOffscreenGetContext.value.apply(this, [type, options]);
            if (ctx && type === '2d' && isFingerprintCanvas(this) && !ctx.__patched) {
                const origGetImageData = ctx.getImageData;
                ctx.getImageData = function(sx, sy, sw, sh) {
                    if (sx === 0 && sy === 0 &&
                        sw === this.canvas.width && sh === this.canvas.height) {

                        const offscreen = new OffscreenCanvas(this.canvas.width, this.canvas.height);
                        offscreen.__bypassSpoof = true;
                        const offCtx = offscreen.getContext("2d");

                        return new Promise((resolve) => {
                            fetch(getSpoofedDataURL(this.canvas))
                                .then(res => res.blob())
                                .then(blob => createImageBitmap(blob))
                                .then(imgBitmap => {
                                    offCtx.drawImage(imgBitmap, 0, 0);
                                    resolve(origGetImageData.call(offCtx, 0, 0, offscreen.width, offscreen.height));
                                })
                                .catch(() => {
                                    resolve(origGetImageData.call(this, sx, sy, sw, sh));
                                });
                        });
                    }
                    return origGetImageData.call(this, sx, sy, sw, sh);
                };
                ctx.__patched = true;
            }
            return ctx;
        }

        try {
            Object.defineProperty(newOffscreenGetContext, 'toString', {
                value: function() { return 'function getContext() { [native code] }'; },
                writable: false,
                configurable: false
            });
        } catch(e) {}

        Object.defineProperty(OffscreenCanvasProto, 'getContext', {
            ...descOffscreenGetContext,
            value: newOffscreenGetContext
        });
    }

    // ========== 4) WebGL ==========
    console.log("Modifying WebGL context parameters");
    const oldGetContextWebGL = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = new Proxy(oldGetContextWebGL, {
        apply: function(target, thisArg, args) {
            const type = args[0];
            const context = target.apply(thisArg, args);
            if (context && (type === 'webgl' || type === 'experimental-webgl' || type === 'webgl2') && !context.__modified) {

                const originalGetParameter = context.getParameter;
                context.getParameter = function(pName) {
                    if (pName === 37445) {
                        return hardwareProfile.gpu.vendor || "Intel Inc.";
                    }
                    if (pName === 37446) {
                        return hardwareProfile.gpu.renderer || "Intel Iris (Custom)";
                    }
                    return originalGetParameter.call(this, pName);
                };

                const originalGetExtension = context.getExtension;
                context.getExtension = function(name) {
                    if (name === 'WEBGL_debug_renderer_info') {
                        return {
                            UNMASKED_VENDOR_WEBGL: 37445,
                            UNMASKED_RENDERER_WEBGL: 37446
                        };
                    }
                    return originalGetExtension.call(this, name);
                };

                const originalGetSupportedExt = context.getSupportedExtensions;
                context.getSupportedExtensions = function() {
                    const realExt = originalGetSupportedExt.call(this) || [];
                    const spoofedExtra = [
                        "EXT_texture_filter_anisotropic",
                        "OES_texture_float",
                        "WEBGL_debug_renderer_info"
                    ];
                    return Array.from(new Set([...realExt, ...spoofedExtra]));
                };

                context.__modified = true;
            }
            return context;
        }
    });

    // ========== 5) AudioContext ==========
    console.log("Overriding AudioContext methods");
    const AudioContextPrototype = window.AudioContext || window.webkitAudioContext;
    if (AudioContextPrototype) {
        window.AudioContext = window.webkitAudioContext = class extends AudioContextPrototype {
            constructor(options) {
                super(options);
                const profileHash = hardwareProfile.device.mac.split('').reduce(
                    (hash, char) => ((hash << 5) - hash) + char.charCodeAt(0),
                    5381
                );
                const originalCreateOscillator = this.createOscillator;
                this.createOscillator = function() {
                    const osc = originalCreateOscillator.call(this);
                    osc.frequency.value = osc.frequency.value + (Math.sin(profileHash * 0.001) * 2);
                    return osc;
                };
                const originalCreateAnalyser = this.createAnalyser;
                this.createAnalyser = function() {
                    const analyser = originalCreateAnalyser.call(this);
                    const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                    analyser.getFloatFrequencyData = function(array) {
                        originalGetFloatFrequencyData.call(this, array);
                        for (let i = 0; i < array.length; i++) {
                            if (array[i] === -Infinity) array[i] = -50;
                            array[i] += Math.sin((i + profileHash) * 0.0001) * 0.5;
                        }
                    };
                    return analyser;
                };
            }
        };
    }

    // ========== 6) Media Devices ==========
    console.log("Overriding navigator.mediaDevices methods");
    if (navigator.mediaDevices) {
        Object.defineProperties(navigator.mediaDevices, {
            'enumerateDevices': {
                value: async function() {
                    return [
                        {
                            deviceId: `${hardwareProfile.audio.deviceId}_input`,
                            kind: 'audioinput',
                            label: hardwareProfile.audio.label,
                            groupId: hardwareProfile.audio.groupId
                        },
                        {
                            deviceId: `${hardwareProfile.audio.deviceId}_output`,
                            kind: 'audiooutput',
                            label: hardwareProfile.audio.label,
                            groupId: hardwareProfile.audio.groupId
                        },
                        {
                            deviceId: hardwareProfile.video.deviceId,
                            kind: 'videoinput',
                            label: hardwareProfile.video.label,
                            groupId: hardwareProfile.video.groupId
                        }
                    ];
                },
                enumerable: true,
                configurable: true,
                writable: false
            }
        });

        try {
            const descriptor = Object.getOwnPropertyDescriptor(navigator.mediaDevices, 'getUserMedia');
            if (descriptor && descriptor.configurable) {
                Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
                    value: function() {
                        return Promise.reject(new Error('NotAllowedError'));
                    },
                    enumerable: true,
                    configurable: true,
                    writable: false
                });
            } else {
                console.warn("Нельзя переопределить getUserMedia – свойство не конфигурируемое.");
            }
        } catch (error) {
            console.error("Ошибка при переопределении getUserMedia:", error);
        }
    }


    // ========== 8) RAM и CPU ==========
    console.log("Overriding navigator hardware properties (RAM/CPU)");
    
    (function() {
        const NavProto = Object.getPrototypeOf(navigator);
        function overrideGetter(obj, prop, newGetterValue) {
            const originalDescriptor = Object.getOwnPropertyDescriptor(obj, prop);
            if (!originalDescriptor || !originalDescriptor.get) {
                return;
            }
            const newGetter = function() {
                return newGetterValue;
            };
            Object.defineProperty(newGetter, 'toString', {
                value: function toString() {
                    return originalDescriptor.get.toString();
                },
                writable: false,
                configurable: false
            });
            Object.defineProperty(obj, prop, {
                get: newGetter,
                set: undefined,
                enumerable: originalDescriptor.enumerable,
                configurable: originalDescriptor.configurable
            });
        }
        overrideGetter(NavProto, 'deviceMemory', hardwareProfile.ram);
        overrideGetter(NavProto, 'hardwareConcurrency', hardwareProfile.cpu.cores);
    })();

    // ========== 9) WebGPU ==========
    console.log("Mocking navigator.gpu with advanced override on Navigator.prototype");
    (function() {
        const NavProto = Object.getPrototypeOf(navigator);
        const originalDescriptor = Object.getOwnPropertyDescriptor(NavProto, 'gpu');
        if (!originalDescriptor || typeof originalDescriptor.get !== 'function') {
            console.log("No native WebGPU found on Navigator.prototype. Skipping full override to avoid suspicion.");
            return;
        }
        const originalGetter = originalDescriptor.get;
        const macSuffix = hardwareProfile.device.mac.slice(-4);
        const macSeed = parseInt(macSuffix, 16) || 1;
        function seededRandom(salt) {
            return Math.abs(Math.sin(macSeed + salt));
        }
        function randomizeValue(base, salt) {
            const multiplier = 0.95 + ((seededRandom(salt) % 1) * 0.1);
            return Math.floor(base * multiplier);
        }
        function createMockGPU(originalGPU) {
            if (!originalGPU) {
                return null;
            }
            const mockedAdapter = {
                name: hardwareProfile.gpu.vendor,
                features: new Set(['texture-compression-bc', 'timestamp-query']),
                limits: {
                    maxTextureDimension2D: randomizeValue(hardwareProfile.gpu.memory, 1),
                    maxBindGroups: randomizeValue(4, 2),
                    maxBindingsPerBindGroup: randomizeValue(1000, 3),
                    maxDynamicUniformBuffersPerPipelineLayout: randomizeValue(8, 4),
                    maxDynamicStorageBuffersPerPipelineLayout: randomizeValue(4, 5),
                    maxSampledTexturesPerShaderStage: randomizeValue(16, 6),
                    maxSamplersPerShaderStage: randomizeValue(16, 7),
                    maxStorageBuffersPerShaderStage: randomizeValue(8, 8),
                    maxStorageTexturesPerShaderStage: randomizeValue(4, 9),
                    maxUniformBuffersPerShaderStage: randomizeValue(12, 10),
                    maxUniformBufferBindingSize: 65536,
                    maxStorageBufferBindingSize: 134217728,
                    minUniformBufferOffsetAlignment: randomizeValue(256, 11),
                    minStorageBufferOffsetAlignment: randomizeValue(256, 12),
                    maxVertexBuffers: randomizeValue(8, 13),
                    maxVertexAttributes: randomizeValue(16, 14),
                    maxVertexBufferArrayStride: randomizeValue(2048, 15)
                },
                isFallbackAdapter: false,
                requestDevice: async () => ({
                    features: new Set(['texture-compression-bc', 'timestamp-query']),
                    limits: {
                        maxTextureDimension2D: randomizeValue(hardwareProfile.gpu.memory, 21),
                        maxBindGroups: randomizeValue(4, 22),
                        maxBindingsPerBindGroup: randomizeValue(1000, 23),
                        maxDynamicUniformBuffersPerPipelineLayout: randomizeValue(8, 24),
                        maxDynamicStorageBuffersPerPipelineLayout: randomizeValue(4, 25),
                        maxSampledTexturesPerShaderStage: randomizeValue(16, 26),
                        maxSamplersPerShaderStage: randomizeValue(16, 27),
                        maxStorageBuffersPerShaderStage: randomizeValue(8, 28),
                        maxStorageTexturesPerShaderStage: randomizeValue(4, 29),
                        maxUniformBuffersPerShaderStage: randomizeValue(12, 30)
                    }
                })
            };
            return {
                async requestAdapter() {
                    return mockedAdapter;
                },
                getPreferredCanvasFormat: originalGPU.getPreferredCanvasFormat
                    ? originalGPU.getPreferredCanvasFormat.bind(originalGPU)
                    : () => 'bgra8unorm',
                wgslLanguageFeatures: originalGPU.wgslLanguageFeatures
            };
        }
        function newGpuGetter() {
            const realGpu = originalGetter.call(navigator);
            if (!realGpu) {
                return null;
            }
            return createMockGPU(realGpu);
        }
        Object.defineProperty(newGpuGetter, 'toString', {
            value: function() {
                return originalGetter.toString();
            },
            writable: false,
            configurable: false
        });
        Object.defineProperty(NavProto, 'gpu', {
            get: newGpuGetter,
            set: undefined,
            enumerable: originalDescriptor.enumerable,
            configurable: originalDescriptor.configurable
        });
    })();

    // ========== 10) Speech API ==========
    console.log("Mocking Speech API voices");

    const voices = (hardwareProfile.speech_voices && hardwareProfile.speech_voices.length)
    ? hardwareProfile.speech_voices
    : [
        {
            default: true,
            lang: browserLang,          
            localService: true,
            name: "FallbackVoice",
            voiceURI: "FallbackVoice"
        },
        {
            default: false,
            lang: "en-US",
            localService: true,
            name: "FallbackEnglish",
            voiceURI: "FallbackEnglish"
        }
        ];

    if ("speechSynthesis" in window) {
    Object.defineProperty(window.speechSynthesis, "getVoices", {
        value: () => voices,
        enumerable: true,
        configurable: true,
        writable: false
    });
    
    Object.defineProperty(window.speechSynthesis, "onvoiceschanged", {
        get: () => null,
        set: () => {},
        enumerable: true,
        configurable: true
    });
    }

    // ========== 11) iframe ==========
    console.log("Setting up iframe protection");
    function protectIframe(iframe) {
        try {
            const win = iframe.contentWindow;
            if (!win) return;
            if (win.HTMLCanvasElement) {
                Object.defineProperties(win.HTMLCanvasElement.prototype, {
                    'getContext': {
                        value: HTMLCanvasElement.prototype.getContext,
                        enumerable: true,
                        configurable: true,
                        writable: false
                    },
                    'toDataURL': {
                        value: HTMLCanvasElement.prototype.toDataURL,
                        enumerable: true,
                        configurable: true,
                        writable: false
                    },
                    'toBlob': {
                        value: HTMLCanvasElement.prototype.toBlob,
                        enumerable: true,
                        configurable: true,
                        writable: false
                    }
                });
            }
            if (win.CanvasRenderingContext2D) {
                Object.defineProperty(win.CanvasRenderingContext2D.prototype, 'getImageData', {
                    value: CanvasRenderingContext2D.prototype.getImageData,
                    enumerable: true,
                    configurable: true,
                    writable: false
                });
            }
            if (win.OffscreenCanvas) {
                win.OffscreenCanvas.prototype.getContext = OffscreenCanvas.prototype.getContext;
            }
            win.document.createElement = document.createElement;
        } catch (e) {}
    }
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.tagName === 'IFRAME') {
                    protectIframe(node);
                }
            }
        }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    document.querySelectorAll('iframe').forEach(protectIframe);

    // ========== 13) Блокировки localhost, порт-скан и т.д. ==========
    console.log("Blocking local connections in WebSocket and fetch");
    const originalWebSocket = window.WebSocket;
    window.WebSocket = new Proxy(originalWebSocket, {
        construct(target, args) {
            const [url] = args;
            if (url.startsWith('ws://localhost') || url.startsWith('ws://127.0.0.1')) {
                throw new Error('Access denied');
            }
            return new target(...args);
        }
    });
    const originalFetch = window.fetch;
    window.fetch = new Proxy(originalFetch, {
        apply(target, thisArg, args) {
            const [url] = args;
            if (typeof url === 'string' && (url.includes('localhost') || url.includes('127.0.0.1'))) {
                return Promise.reject(new Error('Access denied'));
            }
            return target.apply(thisArg, args);
        }
    });
    Object.defineProperty(window, 'Navigator', {
        value: class {},
        writable: false,
        configurable: true
    });
    if (navigator.permissions) {
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = (parameters) =>
            parameters.name === 'geolocation'
                ? Promise.resolve({ state: 'granted', onchange: null })
                : originalQuery(parameters);
    }
    window.WebSocket = new Proxy(WebSocket, {
        construct(target, args) {
            const [url] = args;
            if (!/^wss?:\/\/(localhost|127\.0\.0\.1)/.test(url)) {
                return new target(...args);
            }
            throw new Error('Connection blocked');
        }
    });
    window.fetch = new Proxy(fetch, {
        apply(target, thisArg, args) {
            const [resource] = args;
            const url = resource instanceof Request ? resource.url : resource;
            if (url.includes('umami.dev') || url.includes('localhost') || url.includes('127.0.0.1')) {
                return Promise.resolve(new Response(null, {status: 200}));
            }
            return target.apply(thisArg, args);
        }
    });
})();