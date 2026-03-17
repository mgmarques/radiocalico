const js = require('@eslint/js');

module.exports = [
    js.configs.recommended,
    {
        files: ['static/js/player.js'],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: 'script',
            globals: {
                // Browser APIs
                document: 'readonly',
                window: 'readonly',
                localStorage: 'readonly',
                fetch: 'readonly',
                setTimeout: 'readonly',
                clearTimeout: 'readonly',
                setInterval: 'readonly',
                console: 'readonly',
                encodeURIComponent: 'readonly',
                Date: 'readonly',
                Math: 'readonly',
                Promise: 'readonly',
                Set: 'readonly',
                TextDecoder: 'readonly',
                Uint8Array: 'readonly',
                String: 'readonly',
                HTMLMediaElement: 'readonly',
                Event: 'readonly',
                // HLS.js (loaded from CDN)
                Hls: 'readonly',
                // Node.js module exports (conditional)
                module: 'readonly',
            },
        },
        rules: {
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
            'no-console': 'off',
            'eqeqeq': ['warn', 'smart'],
            'no-var': 'warn',
        },
    },
    {
        files: ['static/js/player.test.js'],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: 'script',
            globals: {
                // Jest globals
                describe: 'readonly',
                test: 'readonly',
                expect: 'readonly',
                beforeAll: 'readonly',
                beforeEach: 'readonly',
                afterEach: 'readonly',
                jest: 'readonly',
                // Node.js
                require: 'readonly',
                module: 'readonly',
                global: 'readonly',
                process: 'readonly',
                // Browser (jsdom)
                document: 'readonly',
                window: 'readonly',
                HTMLMediaElement: 'readonly',
                Event: 'readonly',
            },
        },
        rules: {
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
            'no-console': 'off',
        },
    },
];
