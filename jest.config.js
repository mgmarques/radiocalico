module.exports = {
  testEnvironment: 'jsdom',
  testMatch: ['**/static/js/**/*.test.js'],
  collectCoverageFrom: ['static/js/player.js'],
  coverageThreshold: {
    global: {
      statements: 90,
      branches: 76,
      functions: 85,
      lines: 90,
    },
  },
};