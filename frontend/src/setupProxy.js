const { createProxyMiddleware } = require('http-proxy-middleware');

// Forward all /api requests to the local FastAPI backend during development.
module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8001',
      changeOrigin: true,
    })
  );
};
